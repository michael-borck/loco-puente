# Every service Puente can run

28 registered, 3 on by default. This is the full list and, more usefully, how
it divides — because "28 services" is a misleading number. What matters is which
few the opinionated default should be.

## The opinionated set

The five capabilities a fresh install should provide. Note how many *services*
that takes, and how few are currently default-on.

| Capability | Service | Default | GPU | Notes |
| --- | --- | --- | --- | --- |
| **chat** | Ollama | **on** | yes | OpenAI-compatible API |
| | Open WebUI | **on** | no | The chat UI — a *client* of Ollama, not the owner |
| | llama.cpp | off | yes | Alternative backend for small cards ([ADR0010](adr/0010-llamacpp-for-small-card-hardware.md)) |
| | LibreChat | off | no | Alternative chat UI, with login and rooms |
| **image** | ComfyUI | off | yes | SDXL, FLUX; the node host for the video/avatar work |
| | SwarmUI | off | yes | A better ComfyUI UI — drives the *same* ComfyUI |
| | Fooocus | off | yes | Simpler image UI, fewer knobs |
| **voice** | Voicebox | off | yes | The active TTS (~5.6 GB) |
| | Speaches | off | yes | Whisper STT + Kokoro TTS, OpenAI-compatible |
| | Chatterbox | off | yes | **Retired** — Voicebox subsumes it |
| **song** | ACE-Step | off | yes | Lyrics → song, ~4.7 GB ([docs](ace-step-api.md)) |
| | MusicGen | off | yes | Instrumental/audio, no vocals, GPL-3.0 image |
| **search** | SearXNG | **on** | no | Private meta-search |

**The gap:** three of the five capabilities are not on by default. A fresh
install gives chat and search; image, voice and song require opting in. That is
not yet the opinionated set `docs/vision.md` promises, and it is the most
substantive open decision in the project.

## Infrastructure — not a capability, but what makes the others reachable

| Service | What it is | Default |
| --- | --- | --- |
| **Caddy** | Reverse proxy, automatic TLS, per-service auth | off |
| **portal** | The launcher page — a *client* of the service APIs | off |
| **Uptime Kuma** | Service monitoring and alerting | off |
| **Glances** | CPU, RAM, disk, GPU, container metrics | off |
| **tutor-admin** | Tutor-facing LibreChat account admin (ADR0006) | off |

## Research and knowledge

| Service | What it is | GPU |
| --- | --- | --- |
| AnythingLLM | RAG workspaces over documents | no |
| Vane | AI metasearch over SearXNG | no |
| CiteSight | Citation extraction | no |
| Open Notebook | NotebookLM-style: podcasts, quizzes, notes | no |
| DeepTutor | Research assistant and tutoring | no |

## Tools

Stirling PDF, Excalidraw, Jupyter, Nodepad, Open Terminal (code sandbox,
PDF/DOCX generation). All CPU-only, all opt-in.

## Video and avatar — ComfyUI add-ons, not services

These are *nodes inside ComfyUI*, gated by their own flags, not separate
containers:

`install_sadtalker` · `install_wav2lip` · `install_liveportrait` (+ animal) ·
`install_wan_s2v`

`wan_s2v` is the one worth knowing about: audio-driven video with no face
detector anywhere in its path, so it works on **non-human** characters — teddy
bears, robots. At ~22 GB it needs a 24 GB card to itself.

## Honest notes

- **ComfyUI is the host for six capabilities** — image, video, four avatar
  systems — behind one container and one GPU reservation. It is the most
  depended-on service in the stack and the most contended.
- **SwarmUI is not a separate ComfyUI.** It drives `puente-comfyui` by URL. That
  is why `puente-boot.service` waits on ComfyUI's healthcheck, and why ADR0008
  exists.
- **Four services are opt-in and superseded** — Chatterbox (retired),
  Fooocus and SwarmUI (UI alternatives to ComfyUI), MusicGen (audio, not song).
  They cost nothing when off and confuse the inventory when on.
- **Most services are unreachable by the router today.** `puente/decide.py`
  maps eight capabilities onto six services; the other 22 are reachable only by
  naming them. That is deliberate for infrastructure (you would not route a user
  request to Caddy) but incomplete for the research and tools groups.

## Where this is going

The inventory is larger than the product. A fresh install wanting "an AI stack
that works" needs about **eight services** — Ollama, Open WebUI, SearXNG,
ComfyUI, Voicebox, ACE-Step, Caddy, portal — and the rest should be discoverable
rather than listed.