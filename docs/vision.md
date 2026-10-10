# What Puente is for

*Written 2026-10-10, after a session that spent a long time arguing with
ourselves about which direction to take. This records the answer.*

## The one sentence

**A customisable local AI stack that detects your hardware, offers an opinionated
configuration that fits it, works out of the box — and exposes every capability
as an API so you can write your own thing on top.**

## Why this was hard to see

The project started as a proof of concept on one specific box: a 3090 and a 4060
Ti, a hand-tuned `puente.yml`, and a set of operational knowledge that lived in
shell scripts and one person's head. Every question about "should we add service
X" got answered by "would it fit on this box", which made the project look like a
pile of workarounds rather than a tool.

The turn was realising that **the box is the rarest case, not the typical one**.
The audience is a DIYer on consumer NVIDIA: Linux, frequently a *single* card,
often 8 or 12 GB of VRAM. That reframes everything:

- An 8 GB card cannot hold a 30B model — so MoE expert offload goes from a
  curiosity to the thing that makes the stack useful (ADR0010).
- A single card cannot hold chat, image, voice and song at once — so load and
  release is the **design**, not a compromise. The PoC box has 40 GB and holds
  two models; a real user has 12 GB and holds one.

Everything that looked like a limitation is actually the shape of the product.

## The four commitments

### 1. Detect, then offer — not detect and impose

`puente doctor` inspects the host. `puente init` proposes a configuration that
fits. But the proposal is a *proposal*: the output is a committable `puente.yml`
that the operator then owns and edits. Nothing is hidden, nothing is magic.

The test: could someone read `puente.yml` and understand exactly what will run,
and change any part of it? If not, the feature is wrong.

### 2. Opinionated defaults, genuinely opinionated

Not "here are 27 services, choose some." A default that runs on this hardware:
chat that answers, images that generate, voice that speaks, code that compiles.
Anyone should get something working without reading docs, and without a
frontier-model subscription.

The defaults are opinionated *because* they were chosen against real hardware.
That is also what makes them defensible — not taste, but a measurement.

### 3. Capabilities are APIs. The UI is a client.

This is the architectural commitment that matters most, and it is the one the
PoC has been drifting from.

Chat, image, voice and song are **services with HTTP APIs**. The launcher portal,
and any WebUI we build, is a *client* of those APIs — not the thing that owns them.

Why: the mission is access, and the thing that creates access is not
access to a chat box. It is being able to *write your own code* against a real
AI stack. Someone who has used the portal and then read its API can build
something of their own. Someone given only a chat UI cannot.

**Every service has two distinct surfaces, and they are not the same thing:**

| Surface | What it is | Examples |
| --- | --- | --- |
| **Interface** | The human-facing one — usually a service's own web GUI | Open WebUI, SwarmUI, ComfyUI, the Gradio UIs on Voicebox and ACE-Step |
| **API** | What your code talks to | OpenAI-compatible on Ollama and llama.cpp; bespoke JSON on ComfyUI and SearXNG |

A service can have both, either, or neither. Open WebUI is an interface over
Ollama's API. Ollama has an API and almost no interface of its own. Excalidraw
is an interface with nothing to automate.

The launcher therefore shows **both, labelled separately** — "Open" for the
interface, "API" for the endpoint — because collapsing them into one link is how
someone ends up pointing their script at a web GUI.

Consequences: every capability is reachable over HTTP with a documented contract;
auth is the proxy's job (ADR0001, ADR0002); and the admin surface is a separate
concern with its own privilege split (ADR0006).

### 4. Both backends, user's choice

Ollama is the default because it is easy to operate. llama.cpp is there because
on a small card it is the difference between a 7B model and a 30B one (ADR0010).
Neither is being retired. The choice belongs to whoever installs it.

## What this rules out

- **Feature accumulation.** A service that does not fit the default profile on
  typical hardware does not go in the opinionated set. It can exist as opt-in.
- **Cloud.** "Private by default" is the point. A capability that only works by
  calling an API is not a local AI stack.
- **Requiring the newest hardware.** The 2026-10-10 finding: dual-channel
  DDR4-3200 measures within a few percent of DDR5-6000, so anyone who has
  chased a memory upgrade on our advice has wasted their money. DDR3 *is* a real
  cliff (~1.7× slower) and worth detecting — but the answer is a smaller model,
  not a new motherboard.

## Open questions

- **A resident decision model.** This is the control plane the rest of this
  document assumes and does not yet have. Not a chatty small model — a
  *decision* model: a 0.4–4B model fine-tuned to pick from a restricted option
  set, reading **label-token logits in one forward pass and generating zero
  tokens**, returning calibrated probabilities over exactly the options supplied.
  The field has names (`lev`, `SemIf`, `Laya`, `Kev`, `decider`) and a published
  benchmark against trained classifiers.

  Why it matters here: it is the one model that can be **permanently resident**.
  Everything else is swapped in and out. A decision model can sit on the card
  permanently and answer the only question that governs everything else — *which
  model should be loaded right now?* That turns model residency from a schedule
  someone maintains into a policy the stack applies.

  It also reframes routing. OpenClaw already routes simple queries to a cheap
  model and complex ones to a powerful one; a decision model is the cheap half,
  done properly, at ~0.2 s and no generation loop.

- **Agents.** OpenClaw (MIT, ~250k stars) connects local models to files, shell
  and browsers. Do we integrate, or only ensure our APIs are good enough that an
  agent can drive them? Open question also: which "Hermes" is meant — Nous
  Research's Hermes fine-tunes, or Hermes Agent.

- **The launcher.** Is the portal a real UI, or a signpost? Committing to a web
  app is a maintenance cost; a good API plus a clear list of endpoints is honest
  and cheap.