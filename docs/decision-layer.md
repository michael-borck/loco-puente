# Decision layer — routing without generation

Before loading an 18 GB model, decide which capability a request actually wants.
That is a **classification problem over a fixed option set**, not a generation
problem, and it should not be solved by generating.

## What a decision model is

Not a fast chatty model. A model trained to answer from a restricted option set
by reading **label-token logits in a single forward pass**, returning calibrated
probabilities over exactly the options you supplied. Zero output tokens, no JSON
to parse, no retry loop.

The field has names — `lev` (Qwen3.5-4B + LoRA, public), `SemIf`, `Laya`,
`Kev`, `decider` — and a published benchmark comparing them against trained
classifiers.

## Why it matters for Puente

It is the one model that can be **permanently resident**. Everything else on
the card is swapped in and out; this stays. That makes it the control plane the
rest of the residency story assumes and does not yet have — the thing that
decides *which model should be loaded right now*.

## Measured on this box

`LlamaCppBackend` against `ghcr.io/ggml-org/llama.cpp:server-cuda` running
Qwen3-4B-Q8_0:

```
please draw a picture of a red fox in the snow   → image      1.00
write a python function to reverse a list        → coding     1.00
compose a song about the ocean                   → song       1.00
convert this document to speech for a podcast    → voice      1.00
find some research papers on coral bleaching     → research   1.00
```

6/6 routed correctly, **11 ms median** (min 10, max 15) — one forward pass,
`max_tokens=1`, no generation loop.

**Caveat on that 1.00.** The probabilities are a softmax over next-token
logprobs, normalised across the option labels. That is the label-token readout
*mechanism*, but it is not the same as a purpose-trained decision head, and a
general instruct model's distribution should not be read as calibrated. A
LoRA like `interfaze-ai/lev` trained for this is expected to be better; that is
untested here. Treat high confidence as "the model was unambiguous", not as a
probability.

## Two backends

| | `LexicalBackend` | `LlamaCppBackend` |
|---|---|---|
| Model | none | small instruct model + optional LoRA |
| VRAM | 0 | the model's |
| Latency | instant | ~11 ms measured |
| Paraphrase | weak | good |
| Works on a fresh install | **yes** | needs an inference backend |

`LexicalBackend` is **not a decision model** — it is a deterministic token
overlap fallback, and `backend` is carried through to every answer so a caller
can always tell which one responded. It exists so routing works before anyone
has configured inference (vision.md, commitment 2: works out of the box).

It scores two things a naive overlap count does not:

- **Distinctive matching.** A token appearing in only one option's vocabulary
  counts; one shared across several does not.
- **Absolute confidence, not a normalised share.** Dividing by the total makes
  any single weak match read as certainty.

Both were bugs found by testing, and the second is worth remembering: an earlier
version routed *"write me a python function to reverse a list"* to **voice at
confidence 1.00**, on the single token `"to"` — from "text **to** speech".

## Declining is a first-class outcome

The router declines rather than guesses when the top option is below threshold,
when nothing matches, or when `other` wins — because starting the wrong
capability costs a student waiting for an image that never renders.

`decided=False` also means `service` is `None`. A caller needing a real answer
must check `decided`, not read `capability`, which then holds the fallback.

The fallback is `chat`, because that is the capability that is **always
resident** — declining into it is free, declining into nothing loses the request.

## Not yet built

This is the decision layer only. What it is *for* — automatically loading and
releasing models based on these decisions and observed demand — is not built.
That is the payoff, and it is the larger piece.

A caveat worth flagging for that work: **load/unload may be better driven by
observed demand than by judging text.** Open WebUI and LibreChat already know
what is being asked and how busy they are. The decision model's job is
classifying a request to a capability *before anything is loaded*; the load
policy can then follow from what has actually been used.

## Use

```python
from puente.decide import route, LlamaCppBackend

r = route("draw a picture of a fox", backend=LlamaCppBackend())
if r.decided:
    print(r.capability, r.service, r.confidence)   # image comfyui 1.0
else:
    print("declined:", r.reason, "-> falling back to", r.capability)
```