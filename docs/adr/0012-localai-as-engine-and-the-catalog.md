# 0012 — LocalAI as the engine; a catalog for everything else

**Status:** Accepted (2026-10-10) — engine migration in progress; Tier 3 catalog
schema landed first

## Context

Puente has been growing a service per capability. `puente/services/` now holds 28
hand-written service classes, and two of them were built without checking whether
the capability already existed upstream. That was the wrong order of operations, and
the cost showed up in the two most recent additions:

- **ACE-Step.** `AceStepService` was added as a first-class service. LocalAI shipped
  ACE-Step 1.5 support in **February 2026**.
- **`decide.py`.** A decision layer that classifies a request to a capability before
  anything is loaded. LocalAI shipped `/v1/systemone`, a "Decisions API", in
  **October 2026** — the same idea, upstream, before it was written here.

Both were proposed without a survey of what already existed. Building an AI engine
is not what this project is for, and it is being done by a project with ~49.5k
stars, a Go codebase, and releases every few weeks.

## What LocalAI is, precisely

Worth stating exactly, because the shape decides the split:

- **A single Go server**, shipped as a container (`localai/localai`). It is **not** an
  orchestrator — it does not manage sibling containers, a reverse proxy, or
  per-service lifecycles.
- **OpenAI-, Anthropic- and ElevenLabs-compatible** across 60+ backends
  (llama.cpp, vLLM, whisper.cpp, diffusers, MLX).
- A **Backend Gallery**: backends installed on the fly as OCI bundles into its own
  container. This is roughly what `puente/services/` was, with a package manager
  attached.
- Built-in WebUI, VRAM-aware routing, agents/tool-use/RAG/MCP, voice cloning,
  multi-user auth and quotas.

So LocalAI replaces **the engine slot**. It does not replace orchestration, because
it does not do orchestration.

## Decision

**Puente is a hardware-assessment and multi-service orchestration layer over existing
engines. LocalAI becomes the default engine.**

### Three tiers, split by ownership rather than by whether the service is "AI"

The tempting line is "drop the non-AI services". That line is wrong. It would remove
SearXNG — which LocalAI's agents need for web grounding — and Caddy, which is the
front door for every other service. The useful line is **who writes the code**.

| Tier | Definition | Members |
| --- | --- | --- |
| **1 — Ours** | No upstream project does this for our hardware | LocalAI backend, hardware detection, demand-driven residency, decision routing, config anchoring, GPU UUID pinning, reboot snapshot tooling, Caddy auth |
| **2 — Capability pipelines LocalAI cannot reach** | Real service classes, because no engine will ship these | ComfyUI + its node ecosystems (Wan2.2-S2V, LivePortrait, SadTalker, Wav2Lip), SwarmUI |
| **3 — Curated catalog** | Declarations of pinned third-party images, not implementations | Jupyter, Nodepad, Excalidraw, Stirling PDF, Open Notebook, SearXNG, AnythingLLM |

A Tier 3 entry declares an image, the capability it provides, the hardware it needs,
its interface and API paths, and a profile. No compose fragment, no health check, no
lifecycle logic. Users may point `image:` at their own build, or swap Caddy for
nginx, without Puente needing to know.

### Everything stays opt-in, with one exception already in force

Tier 3 entries are **off by default and enabled by profile or flag**. Fresh install
stays light; the extras are one flag away.

**SearXNG is the exception, and it is already on by default.** It predates this
ADR, it is one of the three services a bare `puente init` turns on, and Open Web
UI's web-search integration points at it — removing the default would break web
search on every existing install. It is declared in the catalog like any other
entry and stays default-on. AnythingLLM is the other one to watch, and it is
genuinely opt-in.

### The decision layer delegates but keeps its fallback

`decide.py` keeps its `LexicalBackend`. `LexicalBackend` is the only routing that
works with no engine, no model, no VRAM and no network — that is what makes a fresh
install usable at all, and it is cheap. Above it, a `LocalAIBackend` calls
`/v1/systemone` when the engine is up. `backend` still rides through to the caller,
because the two are not equally trustworthy.

## Consequences

- **AnyLLM overlaps Open WebUI.** Both are workspace/RAG UIs over an external engine.
  This redundancy is recorded, not resolved — AnythingLLM is in production use, so it
  stays until someone decides otherwise.
- **Port collision on the default profile.** LocalAI and AnythingLLM both want 3000
  in some upstream default configurations; the catalog declares explicit ports.
- **The catalog is the differentiator.** Version pinning plus honest hardware-fit
  metadata for third-party images is the part no upstream project is doing, and it is
  what justifies continuing to exist next to them.
- **Acknowledgement, not silence.** LocalAI, QVAC, LibreChat and Pipecat are credited
  in the README. Standing on other people's work without saying so is not an option.
  Note that the claim "LibreChat does not offer an API" is wrong — it exposes its own
  `/api/*` routes and is commonly used as an agent/MCP backend.

## Rejected

- **Continuing to build capability-summarising services.** Against a 49.5k-star
  engine with a decisions API, a backend gallery and a built-in UI, a
  capability-summariser is a worse version of something that already exists and is
  better funded.
- **Dropping non-AI services on principle.** Cuts SearXNG and Caddy, which are
  infrastructure the AI half depends on. Demote them instead.
- **Making Tier 3 default-on.** The whole argument for Puente over a bare
  `docker run` LocalAI is that the default install stays small. Enabling the office
  tools by default removes that advantage.
- **Deleting `decide.py` in favour of `/v1/systemone`.** It removes the no-engine
  path, which is the one that matters on a fresh install.