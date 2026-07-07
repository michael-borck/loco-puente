---
title: "Service Topology — In vs Outside Puente"
---

What runs where on the box, what Puente manages vs. doesn't, and where
functionality overlaps. Useful when wiring an external tool to the stack, or
deciding whether to reuse an existing service instead of standing up a new one.

> Snapshot from the proof-of-concept box (2026-07-07). "In Puente" = defined in
> `puente.yml`; "managed" = Puente controls its lifecycle via `puente up/down`.

---

## In Puente — active

| Service | Port | GPU | Notes |
|---------|------|-----|-------|
| **comfyui** | 8188 | 0 | Image gen engine + avatar nodes (SadTalker, Wav2Lip). Public via `comfyui.locopuente.org`. |
| **swarmui** | 7801 | 0 | Friendly image-gen UI/API over ComfyUI. Public via `image.locopuente.org`. |
| **portal** | 8090 | – | Launcher page for the stack. |

## In Puente — available but currently disabled

Defined in `puente.yml` with `enabled: false`; flip to `true` + `puente up <name>`
to run. Includes: **speaches** (Whisper STT + Kokoro TTS), **voicebox** (voice
studio), **open_webui** (chat UI), **anythingllm**, **open_notebook**, **searxng**,
**musicgen**, **jupyter**, **stirling_pdf**, **excalidraw**, **nodepad**, and others.
Kept disabled to keep the PoC minimal and avoid GPU-0 contention with image gen.

---

## Outside Puente (separate stacks on the same box)

These run as their own docker-compose projects or native processes. Puente does
**not** control them — start/stop them where they live.

| Service | Port | Location | What it is |
|---------|------|----------|------------|
| **Chatterbox** | 8004 | `~/Chatterbox-TTS-Server` | Voice-cloning TTS **server** (model + API). The active TTS. GPU 1. |
| **Ollama** | 11434 | native (`ollama serve`) | LLM inference. In `puente.yml` but `managed: false` — see below. |
| **AnythingLLM** | 3001 | standalone container | RAG/chat app. `enabled: false` in Puente but running independently. |
| **workready-api** | 8001 | `~/workready-api` | Separate app. |
| LibreChat, ensayo, vc2 | – | own dirs | Other unrelated projects. |
| **nginx-proxy-manager** | 80/443 | `~/docker` | Reverse proxy + TLS for all the `*.locopuente.org` hostnames. |

---

## Ollama — provided-but-optional

Ollama is in `puente.yml` but `managed: false`, running as a **native process**.
`OllamaConfig.install_method` accepts `native` | `docker` | `external`:

- **native** (current) — Puente knows about it (status/portal) but doesn't manage
  its lifecycle. Good when Ollama is already installed and shared with other apps.
- **docker** — Puente runs it as a managed container.
- **external** — point at a **remote** Ollama (another box). Nothing runs locally.

So the LLM backend can be local or remote without changing the rest of the stack.

---

## Voice: three things, some overlap

There is more than one "voice" capability — worth knowing before adding another,
to avoid duplicating functionality:

| Thing | In/out | What it does | Relationship |
|-------|--------|--------------|--------------|
| **Chatterbox** (8004) | outside | Voice-cloning TTS server + API | The active TTS. Bespoke, integrated. |
| **Voicebox** (17493) | in Puente (disabled) | Voice-cloning/TTS **studio** web app ([jamiepine/voicebox](https://github.com/jamiepine/voicebox)) | **Independent** — its own models/backend, NOT a UI over Chatterbox. |
| **Speaches** (8000) | in Puente (disabled) | Whisper STT + Kokoro TTS, OpenAI-compatible | Different scope (STT + a lighter TTS). |

**Key point:** Voicebox is **not** a front-end over Chatterbox — it's a separate,
self-contained stack. They overlap functionally (both do voice-clone TTS) but
can't be pointed at each other. So consolidation means *choosing one*, not
wiring a shared UI:

- **Keep Chatterbox** (current, proven, already integrated) — recommended for now.
- **Switch to Voicebox** only if you want its studio UI + API and are willing to
  migrate; it's still marked "under evaluation" in Puente.

An external tool needing TTS should target **Chatterbox at :8004** today.
