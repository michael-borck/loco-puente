"""Decision layer — classify a request without generating a token of answer.

The control plane the residency story needs: before loading an 18 GB model,
decide which capability the request actually wants. That is a *classification*
problem over a fixed option set, not a generation problem, and the field has
established that it should not be solved by generating.

A decision model reads **label-token logits in a single forward pass** and
returns calibrated probabilities over exactly the options supplied. Zero output
tokens, no JSON to parse, no retry loop. `lev` (Qwen3.5-4B + LoRA), `SemIf`,
`Laya` and `Kev` are all this shape, and there is a published benchmark
comparing them against trained classifiers.

**Two backends, and the honest caveat about the first.**

`LlamaCppBackend` is the real thing: it reads next-token logprobs over the
option labels, which is the label-token readout mechanism. It needs a model
loaded and a GPU to run it on.

`LexicalBackend` is **not** a decision model. It is a deterministic fallback —
token overlap between the request and each option's name and description. It
needs no model, no VRAM and no network, so routing works on a fresh install
before anyone has configured an inference backend. It is weaker on paraphrase
and it is honest about that: `backend` is carried through to every answer so a
caller can tell which one answered.

The confidence threshold is what makes this safe. A decision model is *probabilistic*,
so a routing policy has to decide what to do when it is unsure. Default is to
decline and ask rather than load a large model on a coin flip — loading the wrong
capability costs a student waiting for an image that never renders.
"""

from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

# Below this the router declines rather than guessing. Loading a large model on
# a coin flip is worse than asking.
DEFAULT_THRESHOLD = 0.60

_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Option:
    """One allowed answer, with the text used to describe it."""

    name: str
    description: str = ""


@dataclass(frozen=True)
class Question:
    """A typed question over a restricted option set."""

    name: str
    instructions: str
    options: tuple[Option, ...]
    threshold: float = DEFAULT_THRESHOLD

    def names(self) -> list[str]:
        return [o.name for o in self.options]


@dataclass
class Answer:
    """One question's answer: the choice, the distribution, and the confidence."""

    choice: str
    probabilities: dict[str, float]
    confidence: float
    backend: str

    def above(self, q: Question) -> bool:
        return self.confidence >= q.threshold


class DecisionBackend(Protocol):
    name: str

    def answer(self, state: str, question: Question) -> Answer:
        ...


# --------------------------------------------------------------------------
# lexical fallback — no model, no GPU, no network
# --------------------------------------------------------------------------

#: Words that appear in almost any prompt and would make everything look like a
#: match. Dropped from scoring so "help me with this image" is not routed to
#: image purely because "image" is in the request.
_STOPWORDS = frozenset(
    """a an the and or but if then than that this these those is are was were be
    been being am do does did doing have has had having i me my mine we our ours
    you your yours he she it they them his her its for with about into over
    under to of on in at by from as so such please help can could would should
    shall will may might must make makes made get gets give gives want wants
    need needs use uses using how what why when where which who whom whose
    some any all more most very just also there here get go going come""".split()
)


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOPWORDS}


class LexicalBackend:
    """Deterministic overlap scoring. Not a decision model — see module docstring.

    Deliberately simple and dependency-free so that routing works before an
    inference backend is configured, which is what makes the stack usable out of
    the box (docs/vision.md, commitment 2).

    Two things it gets right that a naive overlap count does not:

    * **Distinctive matching.** A token that appears in only one option's
      vocabulary counts; one shared across several ("text", in both "voice" and
      "research") does not. Otherwise "text to speech" style noise routes on
      whatever common word happened to appear.
    * **Absolute confidence, not a normalised share.** Dividing by the total
      makes any single weak match read as certainty — a bug caught here when
      "write me a python function" routed to `voice` at confidence 1.00, purely
      on the token "to". Confidence now saturates with the count of distinctive
      matches, and zero matches means zero confidence and a decline.
    """

    name = "lexical"

    #: Confidence for one distinctive match, then two, capped. Chosen so a single
    #: clear signal decides while a marginal one is still reportable.
    _CONF_1 = 0.70
    _CONF_2 = 0.95
    _CONF_CAP = 0.97

    def answer(self, state: str, question: Question) -> Answer:
        words = _tokens(state)
        lowered = state.lower()

        vocab = {opt.name: _tokens(f"{opt.name} {opt.description}") for opt in question.options}

        # A token is distinctive if exactly one option's vocabulary contains it.
        owner: dict[str, set[str]] = {}
        for name, vwords in vocab.items():
            for w in vwords:
                owner.setdefault(w, set()).add(name)
        distinctive = {w for w in words if len(owner.get(w, ())) == 1}

        probs: dict[str, float] = {}
        for opt in question.options:
            hits = len(distinctive & vocab[opt.name])
            # An explicit mention of the option's own name is the strongest
            # signal available, and is treated as a second hit.
            if opt.name.lower() in lowered:
                hits += 1
            probs[opt.name] = float(hits)

        best_hits = max(probs.values()) if probs else 0.0
        if best_hits <= 0:
            return Answer(
                choice="",
                probabilities={k: 0.0 for k in probs},
                confidence=0.0,
                backend=self.name,
            )

        conf = self._CONF_1 if best_hits == 1 else min(self._CONF_2 + 0.01 * (best_hits - 2), self._CONF_CAP)
        total = sum(probs.values())
        probs = {k: v / total for k, v in probs.items()}

        return Answer(
            choice=max(probs, key=probs.get),
            probabilities=probs,
            confidence=conf,
            backend=self.name,
        )


# --------------------------------------------------------------------------
# llama.cpp backend — label-token readout
# --------------------------------------------------------------------------


def _extract_top_logprobs(data: dict) -> list[dict]:
    """Pull the top-logprob list out of either llama-server response shape.

    Native `/completion` gives `completion_probabilities` (one entry per
    generated token); OpenAI-shaped `/v1/completions` gives
    `completion[0].top_logprobs`. Reading the wrong one yields an empty list,
    which looks exactly like "the model had no opinion" — worth handling both.
    """
    probs = data.get("completion_probabilities")
    if isinstance(probs, list) and probs and isinstance(probs[0], dict):
        top = probs[0].get("top_logprobs")
        if isinstance(top, list):
            return top
    comp = data.get("completion")
    if isinstance(comp, list) and comp and isinstance(comp[0], dict):
        top = comp[0].get("top_logprobs")
        if isinstance(top, list):
            return top
    return []


class LlamaCppBackend:
    """Read the answer from next-token logprobs over the option labels.

    This is the label-token readout mechanism the decision-model literature
    describes, achieved through llama-server's logprobs rather than a dedicated
    adapter: the prompt names the options, the reply is a single label token, and
    the distribution over those labels is the answer.

    A purpose-trained adapter (`interfaze-ai/lev` is the public example) is
    expected to be better calibrated than a general instruct model, which is not
    trained for this. Where one is configured, set `lora`.
    """

    name = "llamacpp"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8081",
        model: str | None = None,
        timeout: float = 30.0,
        lora: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.lora = lora

    def _prompt(self, state: str, question: Question) -> str:
        lines = [
            "Answer with exactly one word from the list. No explanation.",
            question.instructions,
            "Options: " + ", ".join(question.names()),
        ]
        for opt in question.options:
            if opt.description:
                lines.append(f"  {opt.name}: {opt.description}")
        lines.append(f"Request: {state}")
        lines.append("Answer:")
        return "\n".join(lines)

    def answer(self, state: str, question: Question) -> Answer:
        payload: dict = {
            "prompt": self._prompt(state, question),
            "max_tokens": 1,
            "temperature": 0.0,
            "logprobs": True,
            "top_logprobs": 20,
            "cache_prompt": True,
        }
        if self.model:
            payload["model"] = self.model
        if self.lora:
            payload["lora"] = self.lora

        req = urllib.request.Request(
            f"{self.base_url}/completion",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.load(r)
        except (urllib.error.URLError, OSError, ValueError):
            # A routing decision must never be the thing that breaks the request.
            # Report zero confidence so the threshold declines and the caller
            # falls back to its own default.
            n = max(len(question.options), 1)
            return Answer(
                choice="",
                probabilities={k: 1.0 / n for k in question.names()},
                confidence=0.0,
                backend=f"{self.name}:error",
            )

        # Map the model's top logprobs onto our option labels. Labels are
        # compared case-insensitively and with surrounding punctuation stripped,
        # because the server returns the raw token text.
        wanted = {o.name.lower(): o.name for o in question.options}
        probs = {o.name: 0.0 for o in question.options}

        # llama-server's native /completion returns `completion_probabilities`,
        # a list parallel to the generated tokens. The OpenAI-shaped
        # /v1/completions returns `completion[].top_logprobs` instead. Accept
        # both so the backend works against either endpoint.
        top = _extract_top_logprobs(data)

        for entry in top:
            token = str(entry.get("token", "")).strip().strip('"\'.,:;').lower()
            if token in wanted:
                name = wanted[token]
                try:
                    probs[name] = math.exp(float(entry["logprob"]))
                except (KeyError, TypeError, ValueError):
                    probs[name] = 0.0

        total = sum(probs.values())
        if total <= 0:
            # The model's top tokens did not include any of our labels. Report
            # no confidence rather than inventing one — the threshold declines.
            return Answer(
                choice="",
                probabilities=probs,
                confidence=0.0,
                backend=self.name,
            )

        probs = {k: v / total for k, v in probs.items()}
        best = max(probs, key=probs.get)
        return Answer(
            choice=best, probabilities=probs, confidence=probs[best], backend=self.name
        )


# --------------------------------------------------------------------------
# the capability routing question
# --------------------------------------------------------------------------

CAPABILITY_QUESTION = Question(
    name="capability",
    instructions="Which capability does this request need?",
    options=(
        Option("chat", "general conversation, question, explanation, essay, summary, help"),
        Option("coding", "code, coding, programming, function, bug, debug, python, script, compile"),
        Option("image", "image, picture, photo, drawing, paint, illustration, render, visual"),
        Option("song", "song, music, lyrics, soundtrack, melody, compose, sing, track"),
        Option("voice", "voice, speech, speak aloud, transcript, narration, text to speech, podcast"),
        Option("research", "research, search, source, paper, citation, literature, find information"),
        Option("other", "anything that does not fit above"),
    ),
)

#: Capability -> the service that provides it, for the routing hint.
CAPABILITY_SERVICE = {
    "chat": "ollama",
    "coding": "ollama",
    "image": "comfyui",
    "song": "ace_step",
    "voice": "voicebox",
    "research": "anythingllm",
}


@dataclass
class Route:
    """What the decision layer concluded about one request.

    `decided` is False when the router was not confident, and `capability` then
    holds the *fallback* rather than a choice. `service` returns None in that
    case, so a caller that needs a real answer must check `decided` rather than
    trusting the capability field — which is the safer default for the one case
    where being wrong is expensive (loading an 18 GB model).
    """

    capability: str
    confidence: float
    decided: bool            # False when below threshold
    probabilities: dict[str, float]
    backend: str
    reason: str = ""

    @property
    def service(self) -> str | None:
        """The service that would satisfy this, if we actually decided."""
        return CAPABILITY_SERVICE.get(self.capability) if self.decided else None

    def to_dict(self) -> dict:
        return {
            "capability": self.capability,
            "service": self.service,
            "confidence": round(self.confidence, 4),
            "decided": self.decided,
            "backend": self.backend,
            "reason": self.reason,
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()},
        }


def route(
    request: str,
    backend: DecisionBackend | None = None,
    question: Question = CAPABILITY_QUESTION,
    default: str | None = "chat",
) -> Route:
    """Decide which capability a request needs.

    Declines (`decided=False`) when the top option is below its threshold, when
    `other` wins outright, or when nothing matched. "other" is not a licence to
    load something; it is a statement that nothing here fits.

    `default` is what to do when undecided. It defaults to `chat` because that
    is the capability that is always resident — declining into the fallback costs
    nothing, whereas declining into nothing costs the user their request. Set it
    to `None` to get the strict behaviour.
    """
    backend = backend or LexicalBackend()
    answer = backend.answer(request, question)

    def _decline(reason: str) -> Route:
        return Route(
            capability=default or "",
            confidence=answer.confidence,
            decided=False,
            probabilities=answer.probabilities,
            backend=answer.backend,
            reason=reason,
        )

    if answer.choice == "":
        return _decline("no signal")

    other = next((o.name for o in question.options if o.name == "other"), None)
    if other and answer.choice == other:
        return _decline("no capability matched")

    if not answer.above(question):
        return _decline(f"below threshold {question.threshold}")

    return Route(
        capability=answer.choice,
        confidence=answer.confidence,
        decided=True,
        probabilities=answer.probabilities,
        backend=answer.backend,
        reason=f"confidence {answer.confidence:.2f} >= {question.threshold}",
    )