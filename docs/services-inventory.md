# Every service Puente can run

30 registered, 3 on by default. This is the full list and, more usefully, how it
divides — because "30 services" is a misleading number, and since
[ADR0012](adr/0012-localai-as-engine-and-the-catalog.md) most of them are
*declarations* rather than code.

## The three tiers

Puente no longer builds an AI engine, and it no longer hand-writes a service class
for every image it can run. What it owns is split by who writes the code:

| Tier | What it is | Where it lives |
| --- | --- | --- |
| **1 — Ours** | Hardware assessment, residency policy, decision routing, GPU pinning, Caddy auth, lab-window scheduling | `puente/*.py` |
| **2 — Capability pipelines** | ComfyUI + node ecosystems, SwarmUI — things no engine ships | `puente/services/` |
| **3 — Catalog** | Pinned third-party images, declared | `puente/catalog/*.yml` |

Tier 3 is the part that changed most. Jupyter, Excalidraw, Stirling PDF, Open
Notebook and Nodepad were five service classes; they are now five YAML entries.
`puente catalog` lists them, `puente enable @office` installs the office set, and
adding a service Puente has never heard of no longer needs a fork.

## The opinionated set

The five capabilities a fresh install should provide. Note how many *services*
that takes, and how few are currently default-on.

| Capability | Service | Default | GPU | Notes |
| --- | --- | --- | --- | --- |
| **chat** | LocalAI | off | yes | The successor engine: OpenAI/Anthropic/ElevenLabs-compatible, 60+ backends ([ADR0012](adr/0012-localai-as-engine-and-the-catalog.md)) |
| | Ollama | **on** | yes | Still the default backend while LocalAI proves itself |
| | Open WebUI | **on** | no | The chat UI — a *client* of the engine, not the owner |
| | llama.cpp | off | yes | Alternative backend for small cards ([ADR0010](adr/0010-llamacpp-for-small-card-hardware.md)) |
| | LibreChat | off | no | Alternative chat UI, with login and rooms |
| **image** | ComfyUI | off | yes | Tier 2: SDXL, FLUX, and the node host for the video/avatar work |
| | SwarmUI | off | yes | A better ComfyUI UI — drives the *same* ComfyUI |
| | Fooocus | off | yes | Simpler image UI, fewer knobs |
| **voice** | Voicebox | off | yes | The active TTS (~5.6 GB) |
| | Speaches | off | yes | Whisper STT + Kokoro TTS, OpenAI-compatible |
| | Chatterbox | off | yes | **Retired** — Voicebox subsumes it |
| **song** | ACE-Step | off | yes | Lyrics → song, ~4.7 GB ([docs](ace-step-api.md)) |
| | MusicGen | off | yes | Instrumental/audio, no vocals, GPL-3.0 image |
| **search** | SearXNG | **on** | no | Private meta-search. The one catalog entry that is default-on |

**The gap:** three of the five capabilities are not on by default. A fresh
install gives chat and search; image, voice and song require opting in. That is
not yet the opinionated set `docs/vision.md` promises, and it is the most
substantive open decision in the project.

Note that ACE-Step is no longer a Puente service in the sense it was: LocalAI
has served it since February 2026, and it is kept here because its own container
pins a different torch build from ComfyUI's ([AceStepConfig](ace-step-api.md)).

## Infrastructure — not a capability, but what makes the others reachable

| Service | What it is | Default |
| --- | --- | --- |
| **Caddy** | Reverse proxy, automatic TLS, per-service auth | off |
| **portal** | The launcher page — a *client* of the service APIs | off |
| **Uptime Kuma** | Service monitoring and alerting | off |
| **Glances** | CPU, RAM, disk, GPU, container metrics | off |
| **tutor-admin** | Tutor-facing LibreChat account admin (ADR0006) | off |

## Research and knowledge

| Service | What it is | GPU | Source |
| --- | --- | --- | --- |
| AnythingLLM | RAG workspaces over documents | no | catalog (builtin) |
| Open Notebook | NotebookLM-style: podcasts, quizzes, notes | no | catalog |
| Vane | AI metasearch over SearXNG | no | service |
| CiteSight | Citation extraction | no | service |
| DeepTutor | Research assistant and tutoring | no | service |

## Tools — all catalog, all CPU-only, all opt-in

`puente enable @office` installs Stirling PDF, Excalidraw and Jupyter.
`puente enable @research` installs SearXNG, AnythingLLM and Open Notebook.
Open Terminal (code sandbox) and Nodepad are standalone entries.

## Video and avatar — ComfyUI add-ons, not services

These are *nodes inside ComfyUI*, gated by their own flags, not separate
containers. This is the clearest example of why Tier 2 exists:

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
  maps eight capabilities onto six services; the rest are reachable only by
  naming them. That is deliberate for infrastructure (you would not route a user
  request to Caddy) but incomplete for the research and tools groups.
- **Routing follows the enabled engine, but only for text.** `ENGINE_CAPABILITIES`
  is `chat` and `coding` alone. LocalAI can also generate images and audio, and
  routing those to it would look like a simplification while quietly switching off
  Tier 2 work — the S2V and avatar nodes, Voicebox's idle-unload fork, ACE-Step's
  separate torch build.
- **Two catalog entries stay hand-written.** SearXNG's settings file must be
  seeded before the container's first read, and AnythingLLM's `storage_path`
  adopts an existing install in place. They are declared in the catalog for their
  metadata and marked `implementation: builtin`.

## Where this is going

The inventory is larger than the product. A fresh install wanting "an AI stack
that works" needs about **eight services** — LocalAI or Ollama, Open WebUI,
SearXNG, ComfyUI, Voicebox, ACE-Step, Caddy, portal — and the rest should be
discoverable through `puente catalog` rather than listed here.