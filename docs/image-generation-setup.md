# Image Generation Setup (SwarmUI + ComfyUI)

Operational notes for the image-generation stack: how SwarmUI and ComfyUI fit
together, the non-obvious fixes needed to make them work, and how to recover or
reproduce the setup on a new machine.

> This is a runbook, not user docs. End users never see any of this — they hit
> a chat interface or the SwarmUI web page. This page is for whoever operates
> or duplicates a Puente box.

---

## Architecture

Two containers, both pinned to a single GPU:

- **`puente-comfyui`** (port 8188) — the image-generation *engine*. Holds the
  models, does the actual diffusion. Its node-graph API is powerful but awkward
  to call directly.
- **`puente-swarmui`** (port 7801) — a friendly front-end and **simple API** on
  top of ComfyUI. It runs ComfyUI as a *backend* and exposes a clean
  `POST /API/GenerateText2Image` (prompt in → image out) plus a click-to-generate
  web UI.

SwarmUI is configured to use the **external** `puente-comfyui` as its backend
(via a pre-seeded `Backends.fds`) rather than spinning up its own bundled copy —
this avoids downloading multiple GB of duplicate models. That external-backend
choice is what makes the setup non-standard and required the fixes below.

Both are defined in `puente.yml` and controlled with `puente up swarmui` /
`puente down swarmui`. See [`gpu`](#gpu-placement) notes for device pinning.

---

## The public endpoint

On the proof-of-concept box, SwarmUI is reachable at
**`https://image.locopuente.org`** (fronted by nginx-proxy-manager with
Cloudflare TLS). The box is headless/remote — use that URL (or the LAN address
`http://<box-ip>:7801`), not `localhost`.

The API is **session-based** — three steps, not a single stateless call:

```bash
B=https://image.locopuente.org

# 1. Handshake for a session id
SID=$(curl -s -X POST $B/API/GetNewSession -H "Content-Type: application/json" -d '{}' \
      | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

# 2. Generate (returns an image PATH, not the bytes)
curl -s -X POST $B/API/GenerateText2Image -H "Content-Type: application/json" -d "{
  \"session_id\":\"$SID\",
  \"prompt\":\"a red vintage bicycle against a white brick wall\",
  \"model\":\"juggernautXL_v9\",
  \"images\":1, \"width\":1024, \"height\":1024, \"steps\":25, \"cfgscale\":6 }"
# → {"images":["View/local/raw/2026-.../file.png"]}

# 3. Fetch the returned path (URL-encode spaces as %20)
#    curl -o out.png "$B/View/local/raw/....png"
```

It is **not** OpenAI-compatible (`/v1/images/generations` does not exist).
If a caller needs OpenAI's image schema, put a thin translation wrapper in front.

---

## Models

Checkpoints live on the host at
`~/.puente/comfyui-basedir/models/checkpoints/` and are shared into SwarmUI (see
fix #1). SDXL models (e.g. `juggernautXL_v9`, `sd_xl_base_1.0`) run comfortably
on an 8 GB card, and have ample headroom on GPU 0's 24 GB. To add a model, drop a
`.safetensors` into that folder — both
ComfyUI and SwarmUI pick it up (SwarmUI may need a model-list refresh in its UI).

---

## The three fixes (why external-ComfyUI needs help)

SwarmUI's happy path is to *self-start* ComfyUI, where it injects everything it
needs automatically. Pointing it at an external ComfyUI skips that injection, so
three things had to be handled. **All three are now automated in the Puente
service code** — this section is for understanding and debugging.

### 1. Share the model folder → SwarmUI sees the models

SwarmUI talks to ComfyUI over the API for *compute*, but lists models from its
*own* filesystem. Without a shared folder its model dropdown is empty.

*Fix (codified in `puente/services/swarmui.py`, `compose_fragment`):* mount
ComfyUI's model dirs into SwarmUI, mapping ComfyUI's names to SwarmUI's:

| ComfyUI dir  | SwarmUI dir              |
|--------------|--------------------------|
| `checkpoints`| `Stable-Diffusion`       |
| `loras`      | `Lora`                   |
| `vae`        | `VAE`                    |

**Must not be `:ro`.** SwarmUI writes `.tmp` hash-cache files next to models
(`GetOrGenerateTensorHashSha256`); a read-only mount makes generation fail with
an `IOException: Read-only file system`.

### 2. Install SwarmUI's backend nodes into ComfyUI

Symptom in the ComfyUI/SwarmUI logs:
`Comfy backend is missing the Swarm core nodes!` → generation fails.

SwarmUI ships custom nodes (`SwarmComfyCommon`, `SwarmComfyExtra`) it normally
injects into a self-started ComfyUI. For an external ComfyUI they must be copied
in manually.

*Fix (codified in `puente/services/swarmui.py`, `post_start`):* after the
container is up, `docker cp` the two node dirs out of the swarmui image
(`/SwarmUI/src/BuiltinExtensions/ComfyUIBackend/ExtraNodes/`) into ComfyUI's
shared `custom_nodes` volume, then restart `puente-comfyui`. Idempotent.

### 3. numpy-2 ABI crash + transformers drift

Two sub-problems surfaced when ComfyUI tried to import the Swarm nodes:

- **numpy-2 ABI:** the base image ships numpy 2.x but pins old `scikit-learn`
  (1.1.x) and `scikit-image` (0.19.x) built against numpy 1.x. Their compiled
  extensions raise `numpy.dtype size changed (Expected 96 ... got 88)` when
  transitively imported (transformers → librosa → sklearn). *Fix (codified in
  `puente/services/comfyui.py` `_POSTVENV_SCRIPT`):*
  `pip install --upgrade "scikit-learn>=1.4" "scikit-image>=0.24"`.

- **transformers drift:** the shipped `transformers` 5.x removed the top-level
  `CLIPSeg` imports that two *optional* Swarm nodes (`SwarmClipSeg`,
  `SwarmSam2`) rely on. These are segmentation helpers — **not needed for
  text-to-image**. Because `SwarmComfyCommon/__init__.py` imports every node
  eagerly, one broken node takes down the whole package. *Fix (codified in the
  `post_start` hook):* write a patched `__init__.py` that guards those two
  imports in `try/except`, so the core generation nodes still load.

---

## GPU placement

Image gen is pinned to one GPU via `gpu:` in `puente.yml` (compose
`device_ids`). On the PoC box ComfyUI + SwarmUI share **GPU 0** (RTX 3090, 24 GB);
**GPU 1** (RTX 2060 Super, 8 GB) runs Voicebox. Never run a bare `puente up` (it
starts every enabled service, including any other GPU-0 service that would
contend). Always scope: `puente up swarmui`.

Note GPU 0 also hosts the **host** Ollama process (pinned via
`CUDA_VISIBLE_DEVICES=0`), so image gen and LLM inference share the 24 GB card.
`device_ids` grants *visibility*, not exclusivity — co-resident models both
allocate until the card fills. See `gpu-swap-3090.md`.

---

## Recovery / reproducing on a new machine

Because the fixes are codified, a clean install just works:

```bash
puente up comfyui     # starts the engine
puente up swarmui     # starts the UI + auto-installs backend nodes (fix #2/#3),
                      # then restarts comfyui to load them
```

The `swarmui` `post_start` hook detects missing/unpatched nodes and reinstalls
them, so this is safe to re-run.

**What survives what:**

| Event                                   | Survives? |
|-----------------------------------------|-----------|
| Machine reboot                          | ✅ (containers are `restart: unless-stopped`, all state on host disk under `~/.puente/`) |
| `puente down` / `up`, container restart | ✅ |
| Deleting `~/.puente/comfyui-basedir`    | ✅ — `puente up swarmui` reinstalls the nodes; drop checkpoints back into `models/checkpoints/` |
| Fresh machine / `docker compose build`  | ✅ — pip fixes run in the build/postvenv hook; node install runs in `post_start` |

**If generation fails right after a `puente up swarmui`:** the hook restarts
ComfyUI, so the backend may be mid-reconnect for a few seconds. Check
`ListBackends` shows `"status":"running"`, then retry — the first call after a
restart can transiently return "Something went wrong while generating images."

**Manual node reinstall** (if ever needed outside the hook):

```bash
CN=~/.puente/comfyui-basedir/custom_nodes
for d in SwarmComfyCommon SwarmComfyExtra; do
  docker cp "puente-swarmui:/SwarmUI/src/BuiltinExtensions/ComfyUIBackend/ExtraNodes/$d" "$CN/$d"
done
# then re-run `puente up swarmui` to re-apply the __init__ patch, or restart comfyui
docker restart puente-comfyui
```
