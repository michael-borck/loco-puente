"""Tests for the decision layer.

The routing decision is load-bearing: a wrong one starts an 18 GB model for a
chat request, or answers an image request with text. Two properties matter more
than accuracy, and both are pinned here:

  * **Declining is safe.** Below threshold, or no signal, the router declines
    rather than guessing. A service that says "I don't know" costs nothing; one
    that confidently routes a python question to voice costs an evening.
  * **The backend is always reported.** A caller must be able to tell a real
    decision model from the deterministic fallback, because they are not equally
    trustworthy.
"""

from __future__ import annotations

import json

import pytest

from puente.decide import (
    CAPABILITY_QUESTION,
    LlamaCppBackend,
    LexicalBackend,
    Question,
    Option,
    _extract_top_logprobs,
    route,
)


class _StubBackend:
    """Returns a fixed answer, to test policy independent of scoring."""

    name = "stub"

    def __init__(self, choice: str, confidence: float):
        self._choice = choice
        self._confidence = confidence

    def answer(self, state: str, question: Question):
        from puente.decide import Answer

        probs = {k: 0.0 for k in question.names()}
        probs[self._choice] = 1.0
        return Answer(self._choice, probs, self._confidence, self.name)


# --------------------------------------------------------------------------
# lexical fallback
# --------------------------------------------------------------------------


def test_lexical_routes_on_distinctive_words():
    b = LexicalBackend()
    assert b.answer("compose a song about the ocean", CAPABILITY_QUESTION).choice == "song"
    assert b.answer("draw a picture of a mountain", CAPABILITY_QUESTION).choice == "image"


def test_lexical_ignores_shared_vocabulary():
    """A token in more than one option's vocabulary must not decide.

    Caught as a bug: "text to speech" put the token "to" in voice's
    vocabulary, and "write me a python function" contains "to" — which routed a
    coding question to voice at confidence 1.00.
    """
    a = LexicalBackend().answer("write me a python function to reverse a list",
                               CAPABILITY_QUESTION)
    assert a.choice != "voice"


def test_lexical_confidence_is_absolute_not_a_normalised_share():
    """Normalising by the total turns any single weak match into certainty.

    The second half of the same bug: even with 'to' removed, a share-based
    confidence would report ~1.0 for a one-word coincidence.
    """
    a = LexicalBackend().answer("draw a picture", CAPABILITY_QUESTION)
    assert 0.0 < a.confidence < 1.0


def test_lexical_declines_when_nothing_matches():
    a = LexicalBackend().answer("qqq zzz xxx", CAPABILITY_QUESTION)
    assert a.confidence == 0.0
    assert a.choice == ""


def test_lexical_needs_no_model_or_network():
    """The reason it is the default: routing works on a fresh install before
    anyone has configured an inference backend (vision.md, commitment 2)."""
    a = LexicalBackend().answer("make an image of a cat", CAPABILITY_QUESTION)
    assert a.backend == "lexical"
    assert a.choice == "image"


# --------------------------------------------------------------------------
# routing policy
# --------------------------------------------------------------------------


def test_confident_answer_routes():
    r = route("draw a picture of a fox", backend=LexicalBackend())
    assert r.decided and r.capability == "image"
    assert r.service == "comfyui"


def test_low_confidence_declines_and_falls_back():
    r = route("anything", backend=_StubBackend("image", 0.2))
    assert not r.decided
    assert r.service is None, "a declined route must not name a service"


def test_decline_falls_back_to_chat_by_default():
    """Chat is the capability that is always resident, so declining into it is
    free while declining into nothing loses the user's request."""
    r = route("anything", backend=_StubBackend("image", 0.1))
    assert r.capability == "chat"
    assert not r.decided


def test_strict_mode_has_no_fallback():
    r = route("anything", backend=_StubBackend("image", 0.1), default=None)
    assert r.capability == ""


def test_other_is_never_a_licence_to_load():
    """"other" means nothing here fits. Routing on it would start a service at
    random."""
    r = route("x", backend=_StubBackend("other", 0.99))
    assert not r.decided
    assert r.capability == "chat"


def test_route_reports_its_backend():
    """A caller must be able to distinguish a real decision model from the
    deterministic fallback; they are not equally trustworthy."""
    r = route("draw a picture", backend=LexicalBackend())
    assert r.backend == "lexical"


def test_route_serialises():
    d = route("draw a picture", backend=LexicalBackend()).to_dict()
    restored = json.loads(json.dumps(d))
    assert restored["capability"] == "image"
    assert set(restored["probabilities"]) >= {"image", "chat", "song"}


# --------------------------------------------------------------------------
# llama.cpp backend — response shapes
# --------------------------------------------------------------------------


def test_native_completion_shape_is_parsed():
    """llama-server's /completion returns `completion_probabilities`, a list
    parallel to the generated tokens — not `completion[0]`. Reading the wrong
    one returns an empty list, which is indistinguishable from "the model had no
    opinion" and silently makes every route decline."""
    data = {
        "completion_probabilities": [
            {"token": " image", "logprob": -0.01,
             "top_logprobs": [{"token": " image", "logprob": -0.01},
                              {"token": " chat", "logprob": -6.0}]}
        ]
    }
    top = _extract_top_logprobs(data)
    assert top[0]["token"] == " image"


def test_openai_shape_is_parsed():
    data = {"completion": [{"top_logprobs": [{"token": "song", "logprob": -0.2}]}]}
    assert _extract_top_logprobs(data)[0]["token"] == "song"


def test_unknown_shape_yields_empty_rather_than_raising():
    assert _extract_top_logprobs({"unexpected": 1}) == []


def test_backend_reports_error_rather_than_raising():
    """A routing decision must never be the thing that breaks a request. An
    unreachable server is an error state, not an exception."""
    b = LlamaCppBackend(base_url="http://127.0.0.1:1")  # nothing listening
    a = b.answer("draw a picture", CAPABILITY_QUESTION)
    assert a.confidence == 0.0
    assert a.backend.endswith(":error")


# --------------------------------------------------------------------------
# decision-model semantics
# --------------------------------------------------------------------------


def test_threshold_is_the_policy_not_the_model():
    """Calibration is the model's business; the trade-off is ours. Two backends
    reporting the same confidence must route the same way."""
    high = route("x", backend=_StubBackend("image", 0.95))
    low = route("x", backend=_StubBackend("image", 0.30))
    assert high.decided and not low.decided


def test_option_set_is_restricted():
    """The whole point: the answer comes from the options given, never from the
    model's own idea of what to say."""
    q = Question(
        name="x", instructions="?",
        options=(Option("a"), Option("b")),
    )
    a = _StubBackend("a", 0.9).answer("anything", q)
    assert set(a.probabilities) == {"a", "b"}


def test_probabilities_sum_to_one():
    for text in ["draw a picture", "compose a song", "debug this code"]:
        probs = LexicalBackend().answer(text, CAPABILITY_QUESTION).probabilities
        if any(v > 0 for v in probs.values()):
            assert sum(probs.values()) == pytest.approx(1.0), text


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])