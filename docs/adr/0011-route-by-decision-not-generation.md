# 0011 — Route by decision, not by generation

**Status:** Accepted (2026-10-10) — decision layer shipped; load orchestration not built

## Context

The residency story says a small box swaps models in and out (ADR0010, and
`docs/vision.md`). But it has been missing the piece that decides *when*: what
should be loaded right now?

The naive implementation is to ask a language model. Prompt it "what does this
request need?" and parse the reply. That is wrong in three ways at once:

- It **generates**. Getting the word "image" out costs a decode loop, not a
  forward pass.
- It **parses**. Free text means retries, malformed output, and a second model
  to fix the first model's formatting.
- It **cannot decline**. Asked about an ambiguous request, it produces an answer
  anyway. And starting the wrong capability is expensive — an 18 GB model
  loading for a chat request, or a student waiting for an image that never
  renders.

None of that is necessary, because deciding which capability a request wants is
not a generation task. It is classification over a fixed, known option set: chat,
coding, image, song, voice, research, other.

## Decision

**Answer from label-token logits in a single forward pass, and let "no answer" be
a first-class result.**

1. **Options are supplied, never invented.** The router's answer is always one
   of the options it was given, with a probability for each. The model has no
   opportunity to name a capability that does not exist.

2. **Declining is an outcome, not a failure.** Below threshold, no signal, or
   `other` winning outright all produce `decided=False`. `Route.service` then
   returns `None` so a caller cannot accidentally act on a fallback.

3. **The fallback is chat**, because that is the capability that is *always
   resident*. Declining into it costs nothing; declining into nothing loses the
   user's request. `decided=False` still means "no real answer" — the capability
   field holds a default, not a conclusion.

4. **Two backends behind one interface, and the caller is told which answered.**
   `backend` rides through to every answer. This matters because the two are not
   equally trustworthy: `LlamaCppBackend` is a real decision layer;
   `LexicalBackend` is a deterministic fallback, and saying "yes" about which
   one spoke would be a lie the caller cannot check.

5. **The deterministic fallback exists so routing works with nothing installed.**
   Token overlap, no model, no VRAM, no network. That is what makes the stack
   usable on a fresh install (vision.md, commitment 2). It is weaker on
   paraphrase, and it is labelled as such rather than presented as a decision
   model.

6. **Threshold is policy, calibration is the model's business.** The router
   decides what an acceptable confidence is; backends only report one. This keeps
   the trade-off ours rather than something that changes when the model does.

## Measured

`LlamaCppBackend` against `ghcr.io/ggml-org/llama.cpp:server-cuda` with
Qwen3-4B-Q8_0, `max_tokens=1`:

```
draw a picture of a red fox in the snow   → image      1.00
write a python function to reverse a list  → coding     1.00
compose a song about the ocean             → song       1.00
convert this document to speech            → voice      1.00
find some research papers on coral         → research   1.00
6/6 correct, 11 ms median (min 10, max 15)
```

**The 1.00 is not a calibrated probability.** It is a softmax over next-token
logprobs normalised across the labels — the label-token readout *mechanism*, not
a purpose-trained decision head. A general instruct model's distribution should
be read as "the model was unambiguous", not as a probability. `interfaze-ai/lev`
(Qwen3.5-4B + LoRA) is the public adapter to try and is untested here.

## Two bugs, both worth remembering

- **Response shape.** llama-server's native `/completion` returns
  `completion_probabilities` (a list parallel to the generated tokens), not
  `completion[0].top_logprobs` as the OpenAI shape does. Reading the wrong path
  returns an empty list, which is indistinguishable from "the model had no
  opinion" — and silently made every route decline. Found only because the
  backend was tested against a live server.

- **Normalised confidence is always confident.** The lexical backend divided
  scores by their total, so a single weak match read as certainty. It routed
  *"write me a python function to reverse a list"* to **voice at confidence
  1.00**, on the token `"to"` from "text **to** speech". Confidence is now
  *absolute* evidence, and only tokens unique to one option count. This is the
  more dangerous of the two patterns: normalised distributions look certain no
  matter how little evidence there was.

## Not decided here

**What to do with the decision.** Automatic load and release of models is *not*
built, and this ADR does not commit to how it works.

One thing worth flagging for whoever does it: **load policy may be better driven
by observed demand than by judging text.** Open WebUI and LibreChat already know
what is being asked and how busy they are; a request classifier adds latency
and a dependency to answer a question the logs already answer. The decision
model's clearer job is classifying a request to a capability *before anything is
loaded* — which is a different question, and the one implemented here.

## Rejected

- **Prompt an LLM and parse the reply.** Costs a decode loop, needs parsing and
  retries, and cannot decline.
- **A purpose-trained decision model as the only backend.** `lev` and its peers
  are the right answer for accuracy, but requiring one means routing does not
  work until someone has downloaded and configured a model — which breaks
  "works out of the box". Hence a fallback that admits what it is.
- **Routing to a service directly.** The router answers "which capability",
  not "which container". Keeping those separate means a new backend needs no
  routing change, and the answer stays meaningful when a service is disabled.
- **A Web UI with routing built in.** The UI is a client of the APIs
  (vision.md, commitment 3); putting the policy in the UI would make it
  unavailable to anyone writing their own code against the same services.