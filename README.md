# Puente

**Your own AI platform. Runs on your hardware.**

Puente is a local-first AI orchestrator. It stands up a full stack of AI
services — chat, image generation, speech, song, search, notebooks — on modest
hardware, from one config file. Private by default. Yours to keep.

> Pay a **time tax**, not a **token tax**. Modest hardware, honest bills.

Puente is the deployment layer of [LocoPuente](https://locopuente.org): local AI
for anyone who can't — or won't — send their data to the cloud.

**What this is for, and the four commitments it makes:** [docs/vision.md](docs/vision.md).

## Install

```bash
pip install locopuente
```

> The PyPI distribution is `locopuente` (the `puente` name belongs to another
> project). The command you run is `puente`.

Or from source:

```bash
git clone https://github.com/michael-borck/loco-puente.git
cd loco-puente && pip install -e .
```

## Quick start

```bash
puente capabilities  # what this host can do — and what it can't
puente init          # detect your hardware, choose services that fit
puente install       # pull Docker images, install native pieces (Ollama, models)
puente up            # start the stack + a launcher portal
```

Start with `capabilities`. It reports a blunt verdict per capability — usable
with offload, or not available, with the reason — so you find out before
enabling something, rather than watching a container fail. It also picks the LLM backend
that suits the host: `llama.cpp` on a small card, where expert offload is the
difference between a 7B and a 30B model; `ollama` otherwise, because it is
easier to operate.

Then `puente status` to see what's live.

**Out of the box you get chat and search** — Ollama, Open WebUI, SearXNG. Image,
voice, song and the rest are opt-in, because what fits depends on your hardware
and enabling them by default would be a guess. `puente init` proposes a set and
writes it to `puente.yml`, which is yours to edit from there.

On a new host, run `puente doctor` before and after — it checks Docker, the
NVIDIA container runtime, your GPU pins, ports and secrets, and prints the fix
for anything missing. Read-only, and exits non-zero if something's wrong, so it
doubles as a deployment gate:

```bash
puente doctor            # what's missing, and how to fix it
puente doctor --json     # for CI or monitoring
```

## Expose services (optional)

Enable the built-in **Caddy** service and give any service a `proxy:` block to
publish it at a public hostname — automatic TLS, per-service auth. It's
config-as-code: you declare the boundary, Caddy serves it.

```yaml
services:
  caddy:
    enabled: true
    email: you@example.org         # Let's Encrypt contact
    users:
      ui: { admin: ADMIN_BCRYPT }  # basic-auth groups (bcrypt hash from env)
    proxy_hosts:                   # front hosts that aren't puente services, too
      - host: plex.example.org
        port: 32400
        upstream: 192.168.1.10
        auth: none

  swarmui:
    proxy:
      host: swarmui.example.org
      auth: bearer                 # none | basic | bearer
      token_env: SWARMUI_TOKEN     # token read from the environment
```

Secrets (`ADMIN_BCRYPT`, `SWARMUI_TOKEN`, …) come from the environment, never the
committed config. Full walkthrough — including migrating off an existing proxy —
in [docs/caddy-migration.md](docs/caddy-migration.md).

## What it does

- **Says what your hardware can do.** `puente capabilities` detects the GPU, RAM
  and memory generation, then reports usable / needs-offload / not-available per
  capability. It also detects memory bandwidth, because DDR3 is a real ~1.7×
  cliff for anything streaming experts from RAM and DDR5 is not.
- **Detects your hardware** and proposes a service set it can actually run,
  pinning models to the right GPU. Pins are GPU **UUIDs**, not indices — indices
  get reassigned when cards are reordered, which silently loads a model onto the
  wrong card.
- **Orchestrates the containers** — you toggle services in `puente.yml`, Puente
  handles Docker, GPUs, models, and (optionally) a reverse proxy.
- **Config as code.** The whole stack is one committable `puente.yml`. No web UI,
  no hidden state.
- **Coexists with what you already run.** A service you've already installed can
  stay (`managed: false`); Puente uses it instead of spinning up its own.

### Capabilities are APIs

Chat, image, voice and song are **services with HTTP APIs**. The launcher portal
is a client of them, not the thing that owns them — so you can read the API and
build your own thing against it, which is the point. The WebUI is deliberately
optional.

Because your box may not hold every model at once, Puente also has a small
**decision layer** that routes a request to a capability without generating
anything — measured at 11 ms on a small model. See
[docs/decision-layer.md](docs/decision-layer.md).

## Services

A pick-and-choose menu, all running locally. **Bold** = enabled by `puente init`
on a machine that can run it; the rest are opt-in.

| Service | What it is |
|---|---|
| **Ollama** | Local LLM inference — the default backend |
| **llama.cpp** | GGUF inference with MoE experts offloaded to system RAM. Opt-in; the one to use on a single small card ([ADR0010](docs/adr/0010-llamacpp-for-small-card-hardware.md)) |
| **Open WebUI** | Chat over your models |
| **SearXNG** | Private meta-search |
| **SwarmUI / ComfyUI** | Image generation, and video with the S2V nodes |
| **ACE-Step** | Song generation from lyrics — ~5 GB, so it fits beside other services ([docs](docs/ace-step-api.md)) |
| **Voicebox / Speaches** | Voice-cloning TTS, speech-to-text |
| **AnythingLLM** | Docs + RAG workspaces |
| **Open Notebook, Stirling PDF, Excalidraw, Jupyter, …** | Tools |

Both LLM backends are first-class and neither is being retired: Ollama is
easier to operate, llama.cpp is what makes a large model usable on a small card.
The choice belongs to whoever installs it.

Plus an optional **Caddy** reverse-proxy service (automatic TLS) that fronts
whichever services you expose — see [docs/caddy-migration.md](docs/caddy-migration.md).

Most services pull a prebuilt image and start in seconds. Five are built by
Puente itself and published to GHCR: swarmui, fooocus, comfyui, nodepad, and
voicebox (which upstream ships only as a Dockerfile, so Puente builds it from a
pinned commit).

Each of those services will fall back to compiling from source if the pull fails
— budget 10–20 minutes with long silent stretches for voicebox. Set
`image: null` in that service's config to force the source build, or run
`puente doctor` to check your host against them first. These images are
`linux/amd64`; on an arm64 host, expect to build from source.

## Commands

```
puente capabilities  What this host can do, and what it cannot
puente init      Interactive setup — detect hardware, pick services
puente install   Install native services + pull Docker images
puente up        Start the stack (or a specific service)
puente down      Stop the stack (or a specific service)
puente enable    Enable a service in puente.yml
puente disable   Disable a service in puente.yml
puente status    Status of all enabled services
puente doctor    Check the host environment (read-only; --json, --services)
puente gpu       Detect and display GPUs
puente connect   Connection details for external tools
puente portal    Generate the service launcher page
```

## Requirements

- Python 3.10+
- Docker with the Compose **v2** plugin
- An NVIDIA GPU is needed for image, voice and song; chat runs without one
- For any GPU service: the NVIDIA driver plus `nvidia-container-toolkit`

`puente doctor` checks all of the above and prints the fix for anything
missing — it installs nothing, because a driver upgrade restarts Docker and
risks every running service. See [docs/host-setup.md](docs/host-setup.md).

## License

MIT © Michael Borck. An independent initiative.
