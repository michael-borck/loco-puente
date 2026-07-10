# Chatterbox TTS — RETIRED (historical reference)

> **⚠ RETIRED as of 2026-07-09. Do not follow this document to stand up a service.**
>
> Chatterbox is `enabled: false` in `puente.yml`. **Nothing listens on `:8004`.**
> Voicebox is the active TTS — it bundles a `chatterbox-tts` engine, which made
> a separate Chatterbox container redundant. See **`voicebox-api.md`** (port
> **17493**) and `service-topology.md`.
>
> Kept because the CUDA/driver gotcha and the GPU-pinning notes below are still
> instructive, and `puente/services/chatterbox.py` still references this file.

Historical operational notes from when Chatterbox ran as `puente-chatterbox`
(GPU 1, port 8004), verified 2026-07-07 — superseded two days later.

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
