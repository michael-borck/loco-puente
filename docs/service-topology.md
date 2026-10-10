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

### GPU 1 is the contended card — this is why boot races happen

Worth stating plainly, because it caused a real outage and the symptom points
somewhere unhelpful.

| Card | Services | Concurrent weight |
| --- | --- | --- |
| GPU 0 — RTX 3090, 24 GB | speaches, comfyui, swarmui, ollama-classroom | comfortable |
| GPU 1 — RTX 4060 Ti, 16 GB | **voicebox**, and ollama's classroom preload | **~13 GB of 16 GB** |

`gemma4:12b` (7.6 GB) and Voicebox's TTS weights (~5.6 GB) do not leave much
headroom. At boot both try to load within seconds of each other and the transient
peak tips the card over. Observed **2026-10-10**:

- Voicebox: `cudaErrorDevicesUnavailable`, then it exited — while
  `restart: unless-stopped` brought it straight back, so the log showed a
  shutdown and a healthy `/health` in the same minute and it read as a non-event.
- Ollama: `timed out waiting for llama-server to start` after 5m9s → HTTP 500,
  so `ollama-preload.service` failed and the classroom model sat cold. That unit
  had no retry policy, so one collision left it broken until the next reboot.

Both recovered on their own this time, but only because Docker's restart policy
happened to cover voicebox and nothing covered ollama. The fixes are in
`deploy/ollama-classroom/ollama-preload.service` (retry, backoff, a settle delay,
and `curl -sSf` so a failure says why) and in `puente/services/voicebox.py`
(`restart_delay` plus a healthcheck with a real `start_period`).

**If you add a third GPU-1 consumer, expect this to get worse.** The durable fix
is serialising GPU-1 startup with explicit systemd ordering rather than relying
on retries to paper over the collision.

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

---

## Image-gen watchdog + weekly restart — the layers above the boot unit

The boot self-heal above failed once in practice (2026-08-31): its reconcile
fired `RestartBackends` **once** and polled 60 s, but ComfyUI was still importing
nodes, so the backend re-latched `errored` — and sat that way for six days.
Two further layers now cover what a single reconcile can't:

**1. `reconcile_backends()` is now a rounds loop** (`puente/services/swarmui.py`).
Each round re-fires `RestartBackends` if the backend is still errored, polling
in between — up to ~3 min of patience instead of one shot. A single attempt
loses whenever ComfyUI is slower to become ready than SwarmUI's probe.

**2. `deploy/swarmui-watchdog.{sh,service,timer}`** — ticks every 10 min, quiet
no-op when healthy. Heals two failure modes:

- *Backend latched `errored`* (the race, or anything else that broke it) →
  `RestartBackends` with retries, deferred to the next tick if not healed.
- *Stale CUDA inside a long-lived container* — observed 2026-09-07 after ~7
  days uptime: host GPUs fine, driver libs matched, yet in-container NVML
  failed and torch saw **0 GPUs**, so every model load failed with a
  misleading OOM error. Nothing but a container restart fixes this; the
  watchdog detects it (`torch.cuda.device_count()` via `docker exec`) and
  restarts `puente-comfyui` + `puente-swarmui` — never while ComfyUI has a
  job queued, and it re-heals the backend afterwards (the restart re-arms
  the race).

**3. `deploy/imagegen-weekly-restart.{service,timer}`** — Sunday ~04:30,
`docker restart puente-comfyui puente-swarmui` followed by a watchdog run.
The stale-CUDA state develops over long uptimes; this resets the clock
weekly instead of waiting for it to bite. `Persistent=true` catches a
missed slot.

Note: a ComfyUI-only restart does *not* re-arm the race (SwarmUI's
`comfyui_api` backend auto-reconnects) — the latch needs both containers
starting around the same time, which is exactly the cold-boot and
weekly-restart shape.

Install (host-side, like the other units):

```
sudo cp deploy/swarmui-watchdog.{service,timer} deploy/imagegen-weekly-restart.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now swarmui-watchdog.timer imagegen-weekly-restart.timer
```
