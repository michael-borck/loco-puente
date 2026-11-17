# Puente

**Your own AI platform. Runs on your hardware.**

Puente is a local-first AI orchestrator. It stands up a full stack of AI services (chat, image generation, speech, song, search, notebooks) on modest hardware, from one config file. Private by default. Yours to keep.

> Pay a **time tax**, not a **token tax**. Modest hardware, honest bills.

**Live site:** [locopuente.org](https://locopuente.org) — vision, hardware selection, stack, roadmap.

## Install

```bash
pip install locopuente
```

> The PyPI distribution is `locopuente` (the `puente` name belongs to another project). The command you run is `puente`.

Or from source:

```bash
git clone https://github.com/michael-borck/loco-puente.git
cd loco-puente && pip install -e .
```

## Quick start

```bash
puente capabilities  # what this host can do — and what it can't
puente init          # detect hardware, choose services that fit
puente install       # pull images, install native pieces
puente up            # start the stack + launcher portal
puente status        # what's live
puente doctor        # check Docker, GPU runtime, ports, secrets
```

Start with `capabilities`: it reports usable / needs-offload / not-available per capability, with the reason. It also picks the LLM backend that suits the host (`llama.cpp` on a small card, `ollama` otherwise).

## What it does

- **Says what your hardware can do**, including memory bandwidth, because DDR3 is a real cliff for anything streaming experts from RAM.
- **Detects hardware and pins models to GPU UUIDs**, not indices, which get reassigned.
- **Orchestrates containers** from one committable `puente.yml`.
- **Coexists with what you already run** (`managed: false`).

Services are HTTP APIs behind a launcher portal, so you can build against them directly. `puente catalog` lists what the catalog declares; `puente enable @research` installs the search-and-RAG profile, or enable any entry by name.

## Requirements

Python 3.10+, Docker Compose v2, and an NVIDIA GPU for image/voice/song (chat runs without one). Full details at [locopuente.org](https://locopuente.org).

## Related projects

Puente is the shared/institutional end of a small family. The ladder — four
places AI can live when the subscription is the barrier, every rung speaking an
OpenAI-shaped API — is cross-referenced from each project's site:

- **[mochila](https://github.com/michael-borck/mochila)** — the laptop kit:
  Ollama + the Pi agent + skills in plain text. Rung 1, personal.
- **[frugal](https://github.com/michael-borck/frugal)** — one command to a
  working free-cloud setup: 9Router with a verified fallback chain. Rung 3.
- **[Portable AI Studio](https://github.com/techjarves/Portable-Local-Studio)**
  (not ours) — a zero-setup GUI studio for one person's machine: chat, images
  and voice offline. Evaluated 2026-11-17: linked, not adopted, not wrapped
  ([stocktake](docs/stocktake-2026-11.md)); the single-user, no-auth shape
  can never serve a classroom, which is Puente's job.
- **[loco-base](https://github.com/michael-borck/loco-base)** — the foundation
  layer: NVIDIA drivers, Docker, Ollama and hardening for the lab's Ubuntu
  boxes. Puente deploys on top of it.
- **[LocoLabo](https://locolabo.org)** — the research programme this project
  belongs to. Puente is its deployment layer.

Evaluated and deliberately *not* adopted, recorded so they stay decided:
Kindi (floor-hardware inference; benchmark pending), QVAC (edge SDK; revisit
trigger: a mobile companion), Odysseus (harness candidate; side-by-side
experiment running). See the [stocktake](docs/stocktake-2026-11.md) and
[handover](docs/handover-2026-10.md).

## Licence

MIT © Michael Borck. An independent initiative.
