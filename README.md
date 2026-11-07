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

Services are HTTP APIs behind a launcher portal, so you can build against them directly. `puente catalog` lists what the catalog declares; `puente enable @office` or `@research` installs a profile.

## Requirements

Python 3.10+, Docker Compose v2, and an NVIDIA GPU for image/voice/song (chat runs without one). Full details at [locopuente.org](https://locopuente.org).

## Licence

MIT © Michael Borck. An independent initiative.
