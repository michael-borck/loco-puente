# Service Topology — In vs Outside Puente

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
| **Ollama** | 11434 | native (`ollama serve`) | LLM inference. In `puente.yml` but `managed: false` — see below. |
| **workready-api** | 8001 | `~/workready-api` | Separate app. |
| LibreChat, ensayo, vc2 | – | own dirs | Other unrelated projects. |

Chatterbox used to live here on `:8004`; it is **retired** (voicebox bundles
`chatterbox-tts`). AnythingLLM and the reverse proxy have both moved *into*
Puente — AnythingLLM as `puente-anythingllm` (:3001), and Caddy now owns 80/443
in place of nginx-proxy-manager. See `caddy-migration.md`.

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
| **Voicebox** (17493) | in Puente (**enabled**, GPU 1) | Voice-cloning/TTS **studio** web app + API ([jamiepine/voicebox](https://github.com/jamiepine/voicebox)) | **The active TTS.** Self-contained; bundles a `chatterbox-tts` engine. |
| **Chatterbox** (was 8004) | **retired** | Voice-cloning TTS server + API | Redundant once voicebox landed. `enabled: false`; proxy block removed. |
| **Speaches** (8000) | in Puente (disabled) | Whisper STT + Kokoro TTS, OpenAI-compatible | Different scope (STT + a lighter TTS). |

**Key point:** Voicebox is **not** a front-end over Chatterbox — it's a separate,
self-contained stack that happens to ship `chatterbox-tts` as one of its engines.
That redundancy is exactly why Chatterbox was retired rather than kept alongside.

An external tool needing TTS should target **Voicebox at :17493**. Nothing listens
on `:8004`. See `voicebox-api.md` for the endpoints.

> Note the retirement gotcha recorded in `puente.yml`: a declared `proxy:` block is
> served even when the service is `enabled: false`, so the block had to be set to
> `null` to stop the dead route being routed. See `caddy.iter_proxied_services`.

---

## SwarmUI "No backends available!" — cold-boot self-heal

SwarmUI drives an **external ComfyUI by URL** (`puente-comfyui`). It probes that
backend once at startup; if it wins the race against ComfyUI finishing its node
imports, it marks the backend `errored` and **never auto-retries** — every
generate then returns `No backends available!`.

`swarmui`'s compose fragment has `depends_on: {comfyui: service_healthy}`, which
closes the race on a single `docker compose up`. But a **bare host reboot**
restarts each container independently via its `restart: unless-stopped` policy,
bypassing that ordering — and nothing runs `puente up` on a cold boot — so the
race recurs. This box is cold-booted often.

**The self-heal (two parts):**

1. **`swarmui.post_start()` → `reconcile_backends()`** — after installing nodes,
   it calls SwarmUI's `ListBackends`; if any backend is `errored`, it calls
   `RestartBackends` and polls until `running`. Idempotent (a no-op when already
   running). Runs on every `puente up`.
2. **`deploy/puente-boot.service`** — a systemd oneshot that runs
   `puente up swarmui` **once per boot, after `docker.service`**. The container is
   already up (its own restart policy), so this just fires swarmui's `post_start`
   hook — the reconcile above. Scoped to `swarmui` on purpose: bare `puente up`
   would recreate `puente-caddy` (a brief drop of every route) and collide with
   the manually-started `puente-portal-gpu-stats` sidecar, and violates the
   "never bare `puente up`" GPU-ordering rule. This makes the cold-boot case
   self-heal without you touching anything.

Install the boot unit once (travels with the repo, but the install is host-side):

```
sudo cp deploy/puente-boot.service /etc/systemd/system/puente-boot.service
sudo systemctl daemon-reload
sudo systemctl enable puente-boot.service
```

**Manual recovery** (if the backend is ever errored right now):
`puente up swarmui` re-runs the reconcile. Or call the API directly — see
[[swarmui-no-backends-race]] in memory for the raw `curl` recovery.
