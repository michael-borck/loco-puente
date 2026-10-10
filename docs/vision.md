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

### 4. One engine, chosen by the operator

**Puente is not an AI engine.** It is a hardware-assessment and multi-service
orchestration layer *over* existing engines (ADR0012).

That is a change of direction, and it was forced by two facts found too late:
LocalAI shipped ACE-Step support in February 2026, and a Decisions API
(`/v1/systemone`) in October 2026 — the same two things this project had built
or was about to build. LocalAI is MIT, ~49.5k stars, and offers
OpenAI/Anthropic/ElevenLabs-compatible APIs across 60+ backends with VRAM-aware
routing and a built-in WebUI. Rebuilding an engine against that is not a
contribution, and the honest response is to use it.

So the engine slot is LocalAI's. What stays ours is the part no upstream is
doing:

- **hardware assessment** — what this specific box can afford, per capability;
- **heterogeneous orchestration** — ComfyUI and its node ecosystems, SearXNG,
  AnythingLLM, Caddy's multi-tenant auth, lab-window scheduling, GPU UUID pinning;
- **residency policy** — what stays in VRAM on a card that cannot hold it all;
- **the catalog** — pinned third-party images with honest hardware-fit metadata.

Ollama and llama.cpp both remain supported and neither is being retired. llama.cpp
still matters because on a small card it is the difference between a 7B model and
a 30B one (ADR0010), and LocalAI wraps llama.cpp rather than replacing that
capability.

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

- **A resident decision model.** Partly answered upstream: LocalAI's
  `/v1/systemone` is a Decisions API doing this job, and `decide.py` now
  delegates to it. What is still open is whether a *bespoke* adapter beats it on
  our hardware — `lev` (Qwen3.5-4B + LoRA) is the public one and is untested
  here.

  The reason the question survives delegation: `/v1/systemone` needs an engine
  running. The lexical fallback in `decide.py` is the only routing that works
  with nothing installed, no VRAM and no network, and on a fresh install that is
  the path that runs. Whether a resident 0.4–4B model is worth the VRAM is still
  undecided — it would be the one model that could stay permanently resident
  while everything else is swapped in and out.

- **ComfyUI's node ecosystems, long term.** Wan2.2-S2V, LivePortrait, SadTalker
  and Wav2Lip are Tier 2 precisely because no engine ships them. That is a
  defensible position, but it is also a maintenance surface on a fast-moving
  upstream. Worth deciding whether those stay curated here or move to
  user-supplied catalog entries with documented prerequisites.

- **Agents.** OpenClaw (MIT, ~250k stars) connects local models to files, shell
  and browsers. Do we integrate, or only ensure our APIs are good enough that an
  agent can drive them? Open question also: which "Hermes" is meant — Nous
  Research's Hermes fine-tunes, or Hermes Agent.

- **The launcher.** Is the portal a real UI, or a signpost? Committing to a web
  app is a maintenance cost; a good API plus a clear list of endpoints is honest
  and cheap.

- **AnythingLLM vs Open WebUI.** Both are workspace/RAG UIs over an external
  engine, and both are in the stack. ADR0012 records the redundancy rather than
  resolving it, because AnythingLLM is in production use today. LocalAI's own
  RAG makes the question sharper, not moot.

## Acknowledgements

Puente stands on other people's work and says so:

- **[LocalAI](https://github.com/mudler/localai)** (MIT) — the default engine:
  OpenAI/Anthropic/ElevenLabs-compatible APIs across 60+ backends, the Backend
  Gallery, VRAM-aware routing, the built-in WebUI, and `/v1/systemone`.
- **[QVAC](https://github.com/tetherto/qvac)** (Apache-2.0, Tether) — an on-device
  SDK and server spanning the same generation surface. Not adopted; the comparison
  is why the engine decision was made deliberately rather than by default.
- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** (MIT) — `--cpu-moe` expert
  offload is the capability the small-card story rests on.
- **[Ollama](https://github.com/ollama/ollama)** (MIT) — still a first-class backend.
- **[LibreChat](https://github.com/danny-avila/LibreChat)** (MIT) and
  **[Open WebUI](https://github.com/open-webui/open-webui)** (MIT) — the chat
  surfaces, both clients of the APIs rather than owners of them.
- **[ComfyUI](https://github.com/comfyanonymous/ComfyUI)** (GPL-3.0) and
  **[SwarmUI](https://github.com/mcmonkeyprojects/SwarmUI)** (AGPL-3.0) — Tier 2
  image pipelines, including the node ecosystems no engine ships.
- **[SearXNG](https://github.com/searxng/searxng)** (AGPL-3.0),
  **[AnythingLLM](https://github.com/Mintplex-Labs/anything-llm)** (MIT),
  **[Stirling-PDF](https://github.com/Stirling-Tools/Stirling-PDF)** (GPL-3.0),
  **[Excalidraw](https://github.com/excalidraw/excalidraw)** (MIT),
  **[Jupyter](https://github.com/jupyter/notebook)** (BSD-3),
  **[Open Notebook](https://github.com/lfnovo/open-notebook)** (MIT) — catalog
  entries, declared rather than reimplemented.
- **[Caddy](https://github.com/caddyserver/caddy)** (Apache-2.0) — TLS termination
  and the per-service auth policy.
- **[Pipecat](https://github.com/pipecat-ai/pipecat)** (BSD-2) — the reference for
  voice orchestration. Not currently a dependency; recorded because it is what we
  would build against rather than build.