---
title: "Chatterbox TTS — In Puente"
---

Chatterbox voice-cloning TTS, now a Puente-managed service. Operational notes:
the CUDA gotcha, GPU pinning, the TTS API, and how to reproduce on a new box.

> **Verified** 2026-07-07: migrated from the standalone install to
> `puente-chatterbox` (GPU 1, port 8004); existing voice library preserved;
> TTS generates real audio via `/v1/audio/speech`, with GPU 1 active.

---

## The CUDA gotcha (read before building on a new box)

Chatterbox's Dockerfile bases on **`nvidia/cuda:12.8.1-runtime-ubuntu22.04`**.
The **host NVIDIA driver/kernel must be new enough for CUDA 12.8** or the
container won't see the GPU. On the PoC box this required updating the host
driver + kernel first. The build itself is straightforward but **LONG** (large
ML deps) — cached layers make rebuilds fast, but a cold build takes a while.

---

## GPU pinning — portable by design

The service requests a GPU based on `config.gpu` in `puente.yml`:

- **`gpu: 1`** (this box) → pins to physical device 1, keeping Chatterbox off
  the image-gen GPU 0. Inside the container that device shows as "GPU 0" — that
  is normal Docker renumbering, not a misassignment (verify via UUID if unsure).
- **`gpu: null`** → requests `count: 1` (any one GPU), so a **single-GPU box
  still starts** instead of hard-erroring on a missing device id.

⚠️ Pinning `device_ids: ['1']` on a 1-GPU box is a HARD ERROR — no fallback to
GPU 0 or CPU. That is why `gpu: null` maps to `count: 1` here.

---

## Config (`puente.yml`)

```yaml
  chatterbox:
    enabled: true
    install_method: docker      # or "external" to point at an existing one
    port: 8004
    gpu: 1                       # or null for any-GPU
    review: true
    build_context: /home/michael/Chatterbox-TTS-Server
```

`build_context` is the local checkout (its Dockerfile pins the tuned CUDA/torch
stack). Others clone the repo and set their own path. The service bind-mounts
`config.yaml`, `voices/`, `reference_audio/`, `outputs/`, `logs/` from that dir,
so an existing voice library is preserved and shared.

---

## TTS API

OpenAI-compatible + native endpoints (FastAPI docs at `/docs`):

- `POST /v1/audio/speech` — OpenAI-style. **`voice` must be the full filename**
  (e.g. `Alice.wav`, not `Alice`).
- `GET /v1/audio/voices` — list available voices.
- `POST /tts` — native endpoint.
- `GET /get_predefined_voices`, `POST /upload_predefined_voice`.

```bash
curl -s -X POST http://<box>:8004/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"chatterbox","input":"Hello world","voice":"Alice.wav","response_format":"wav"}' \
  -o out.wav
```
Output: 16-bit mono 24 kHz WAV.

---

## Reproduce / migrate on a new box

1. Ensure the host driver supports CUDA 12.8.
2. Clone Chatterbox-TTS-Server; set `build_context` to it in `puente.yml`.
3. `puente up chatterbox` (long first build; cached after).

The old standalone container, if any, should be stopped with restart policy set
to `no` so it can't reclaim port 8004.
