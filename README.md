# Puente

**Your own AI platform. Runs on your hardware.**

Puente is a local-first AI orchestrator. It stands up a full stack of AI
services — chat, image generation, speech, search, notebooks — on modest
hardware, from one config file. Private by default. Yours to keep.

> Pay a **time tax**, not a **token tax**. Modest hardware, honest bills.

Puente is the deployment layer of [LocoPuente](https://locopuente.org), a
LocoLabo initiative: local AI for everyone who can't — or won't — send their
data to the cloud.

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
puente init      # detect your hardware, choose services that fit
puente install   # pull Docker images, install native pieces (Ollama, models)
puente up        # start the stack + a launcher portal
```

Then `puente status` to see what's live. That's it.

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

## Services

A pick-and-choose menu, all running locally:

| Service | What it is |
|---|---|
| **Ollama** | Local LLM inference |
| **Open WebUI** | Chat over your models |
| **SwarmUI / ComfyUI** | Image generation |
| **Voicebox / Speaches** | Voice-cloning TTS, speech-to-text |
| **SearXNG** | Private meta-search |
| **AnythingLLM** | Docs + RAG workspaces |
| **Open Notebook, Stirling PDF, Excalidraw, Jupyter, …** | Tools |

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
- Docker (for containerized services)
- A GPU is recommended but not required — a single consumer GPU is enough to start.

## License

MIT © Michael Borck. A LocoLabo initiative, Curtin University.
