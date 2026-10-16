# State on 2026-10-10, and what to pick up in two weeks

**Written at the end of the 2026-10-10 session. Read this first when you come back.**

This is a handover, not a runbook. It answers three questions: what is running
right now, what is staged but unverified, and what should be decided before
anything else is built.

The two-week plan: ship the chatbot, do not restructure the stack, then revisit
the engine migration with the chatbot working.

---

## What is running and must not be disturbed

Ollama and AnythingLLM are serving traffic for a chatbot being put on a webpage.
Nothing about the engine migration should touch them.

| Service | How it runs | Notes |
| --- | --- | --- |
| Ollama | systemd, native | Pinned to the **4060 Ti** by `/etc/systemd/system/ollama.service.d/10-classroom.conf`, deliberately not the 3090. `OLLAMA_KEEP_ALIVE=3h`, `OLLAMA_MAX_LOADED_MODELS=2` — classroom tuning, deliberately prevents thrashing |
| AnythingLLM | docker, managed by puente | `storage_path` points at `~/.puente/anythingllm` |
| Caddy | docker | TLS + per-service auth for every hostname below |
| SearXNG | docker, enabled 2026-10-17 | JSON API + web UI on :8888. The old container was a zombie mounting a fake-home test dir — replaced. Engines google/bing/wikipedia force-enabled; Open WebUI's web search works again |

Anything else enabled in `puente.yml` is idle capacity, not load-bearing.

### API endpoints that already exist

The "expose this to my Python program" problem is solved. Each service has two
hostnames: a browser door and an API door with a bearer token.

| Need | Hostname | Upstream | Auth |
| --- | --- | --- | --- |
| Image | `image.locopuente.org` | :7801 (SwarmUI) | basic |
| Image (programmatic) | `swarmui.locopuente.org` | :7801 | bearer |
| Voice / TTS | `voicebox.locopuente.org` | :17493 | bearer |
| Voice (browser) | `voice.locopuente.org` | :17493 | basic |
| STT/TTS | `speaches.locopuente.org` | :8000 | bearer |
| STT/TTS (browser) | `speech.locopuente.org` | :8000 | basic |
| Chat | `chat.eduserver.au` | :3001 (AnythingLLM) | none — AnythingLLM has its own accounts |
| Ollama | `ollama.locollm.org` | :11434 | bearer |

**Bearer tokens come from the environment, never a shell profile** (ADR0002).
They are resolved into `~/.puente/caddy/.env` at `puente up` time. Whatever runs
your chatbot needs them in *its* environment.

Note: **port 8077 is an upstream, not a public port.** `boxes.borck.dev` is
served on 443; `viscatalog` listens on `192.168.20.120:8077` and is reached by
Caddy, not by browsers.

---

## Staged but NOT verified

This is the important section. Five commits landed (`91e5df3..d205081`) and the
test suite passes at 213, but nothing in the LocalAI half has run against a real
server.

### 1. LocalAI has never been started

`puente/services/localai.py` generates a compose fragment. That is all that has
been verified. The image is pinned to `v3.5.0` from the README — **check that
tag exists** before pulling, it was not confirmed against the registry.

### 2. `/v1/systemone` response handling is written against a fake

`LocalAIBackend` in `puente/decide.py` is defensive because the exact upstream
response shape was never observed: it accepts `choice` or `label`, and
`probabilities` or `scores`, falls back to argmax when no label comes back, and
declines rather than guesses on anything unrecognised.

**First thing to do:** start LocalAI, then

```bash
curl -s http://127.0.0.1:8080/v1/systemone -H 'Content-Type: application/json' -d '{
  "prompt": "draw a picture of a red fox",
  "question": "Which capability does this request need?",
  "options": [{"name": "chat"}, {"name": "image"}, {"name": "other"}]
}' | python3 -m json.tool
```

Compare the real shape to what the parser expects. Do not trust routing built on
it until this returns something sensible.

### 3. Image tag validity

Same caveat for the catalog entries: `stirlingtools/stirling-pdf:2`,
`excalidraw/excalidraw:v0.17.6`, `jupyter/minimal-notebook:stable` (that one is
deliberately floating), `searxng/searxng:2026.10.25-0e0e4b7`,
`lfnovo/open_notebook:v1-latest-single`. Verify before relying on them.

### 4. LocalAI on 8080 collides with the portal

Both default to 8080 and both are off by default, so it is harmless as it
stands. Move one before enabling both.

---

## Design principle, recorded 2026-10-10

**Docker is a means, not the goal. The aim is the easiest possible setup,
install and maintenance on a server or computer.**

Containers were chosen because they looked like plug-and-play modularity, not
because Docker is a requirement. This matters because it was nearly treated as
one: the QVAC evaluation below weighted "no container story" against it, and
ADR0012 leans on LocalAI shipping an image. If Docker is instrumental, decisions
must be made on total setup-plus-maintenance cost, per service.

`install_method: docker | native | external` already exists per service, so the
abstraction is in place. What was missing is the rule for choosing:

| Service type | Winner | Why |
| --- | --- | --- |
| Hostile dependency stacks — ComfyUI's pinned torch+cu124, Voicebox, ACE-Step | Docker | Dependency-hell avoidance IS the maintenance win; upgrade = pull a tag |
| Good native installer, direct GPU — Ollama's `curl \| sh` | Native | No `nvidia-container-toolkit` prerequisite, GPU just works |
| Single static binaries — Caddy | Native | A binary and a Caddyfile; nothing to containerise |
| Needs a database sibling — LibreChat + mongo | Docker | Orchestration is the job |

The Docker-specific tax for the target audience is specific and worth naming:
`nvidia-container-toolkit` is the hardest prerequisite `puente doctor` checks.

**Open implication, deliberately not decided:** the default trio could run
entirely without Docker — Ollama native, Open WebUI via pip, Caddy as a single
binary. That may be the true "easiest possible setup" story for someone who has
never used Docker, and is a candidate for the quick-start path at the revisit.
A pure-Docker default would foreclose it by inertia; this note is here so the
choice is made deliberately.

---

## Decisions waiting on you

Ordered by how much they block other work.

### A. Is the engine migration worth doing at all?

ADR0012 argues LocalAI should replace Ollama as the engine. That argument is
**untested in practice** — nobody has run it. Before spending time on it,
answer: what would Puente actually gain?

Honest answer from the ADR: an OpenAI+Anthropic+ElevenLabs-compatible surface
across 60+ backends, a built-in WebUI, VRAM-aware routing, and a decisions API.
It would *not* gain image or audio, because routing those there switches off
Tier 2 work no engine ships (Wan2.2-S2V, LivePortrait, SadTalker, Wav2Lip,
Voicebox's idle-unload fork, ACE-Step's separate torch build). See
`ENGINE_CAPABILITIES` in `decide.py` — deliberately `chat` and `coding` only.

If the gain is only "a nicer API surface", that may not be worth a migration of a
working stack. Say so and ADR0012 gets marked superseded rather than quietly
ignored.

### B. AnythingLLM vs Open WebUI

Both are workspace/RAG UIs over an external engine, both in the stack. ADR0012
records the redundancy rather than resolving it, because AnythingLLM is in
production use. LocalAI has its own RAG, which sharpens the question. One of
these should probably go.

### C. The opinionated default is still not opinionated

`docs/services-inventory.md` says it plainly: a fresh install gives **chat and
search only**. Image, voice and song are opt-in. `docs/vision.md` promises five
capabilities by default. This is the most substantive open product question and
it has not moved.

### D. ComfyUI node ecosystems: curate here, or make them catalog entries?

Wan2.2-S2V, LivePortrait, SadTalker, Wav2Lip are Tier 2 precisely because no
engine ships them. That is defensible, and it is also a maintenance surface on
a fast-moving upstream. Worth deciding whether they stay hand-curated.

### E. QVAC — evaluated 2026-10-10, verdict: not adopted

Checked so it does not get re-litigated. Sources: `github.com/tetherto/qvac`
(685 stars, Apache-2.0, 3,131 commits, Tether-funded) and
`docs.qvac.tether.io/ecosystem/`.

QVAC is **not** a LocalAI alternative — different shape entirely:

| | LocalAI | QVAC |
|---|---|---|
| Shape | Server-first, single Go binary | SDK-first (JS/TS + Python), npm/Bare runtime |
| Ships as | Docker image | npm package — no container story |
| API | OpenAI + Anthropic + ElevenLabs | OpenAI-compatible only |
| UI | Built-in WebUI | None (QV.AC is a separate app) |
| Multi-model | 60+ backends, OCI gallery | One model per server config |

Puente's real aim is ease of setup and maintenance, and Docker is instrumental —
see the design-principle note above. QVAC still loses the engine slot, but on
the surviving grounds: one model per server config (vs LocalAI's 60-backend
gallery), OpenAI-compatible only, no WebUI, a native Node runtime to install on
a GPU box, and a server defaulting to `127.0.0.1:11434` — Ollama's own port,
which this box is keeping. "Not containerised" is NOT one of the reasons; do
not resurrect it as one.

Two things recorded so they are findable later:

- **Revisit trigger:** a mobile/edge companion app. QVAC is the only one of the
  three engines that runs on Android/iOS, with P2P model fetching. That is the
  one scenario where it wins.
- **Thing worth stealing:** its model registry serves *weightless* model
  descriptions — tensor lists and settings — so "does this model fit in memory"
  can be answered **before downloading**. That is `puente capabilities` done
  from the model side. If LocalAI's catalog ever exposes similar metadata,
  wiring it into the capability report would turn the heuristic table in
  `capabilities.py` into an answer from data. Also validation that the
  hardware-assessment idea is aimed at the right thing.

### F. Song generation: offer three models, decided at install (2026-10-10)

Found while checking whether YuE2's ~11-12 GB claim
(`localmodelwatch.tsuchitsuchi.com/en/model-m-a-p-yue2-en/`) reopened the
question the stack closed when it chose ACE-Step over YuE 1
(`docs/ace-step-api.md:6-24`). It does.

YuE 1 was rejected correctly: 24 GB BF16, 0.083x realtime, 36% phoneme error
rate. **YuE2 fixes most of that** — 3.6B params, ~11 GiB peak measured on a
4090 (14 GiB max length), ~71 s for a 3.6-min song (~3x realtime), and the best
open weights available: SongBench 6.73 vs ACE-Step 1.5's 6.01, above Suno v6.
Its score-first architecture (ABC notation written first, then rendered —
editable, agent-modifiable, covers via SheetSage2) is a real differentiator.

Caveats, from the same source:

- A 12 GB card "leaves almost no headroom"; official rec is 24 GB. Fits the
  3090 beside ComfyUI (~20 GB, tight); fits the 4060 Ti only with Ollama's
  8.4 GB resident model gone; does not fit the 8-12 GB tier at all.
- **Licence CC BY-NC 4.0 — non-commercial.** Probably fine for the education
  stack, but must be surfaced at install, not discovered later.
- ACE-Step still wins lyric clarity (7.46% vs 8.44% PER) and is ~5x faster.

The decision this points to: **offer all three, chosen at install time.** The
choice layer is legitimately Tier 1 — "24 GB free → XL or YuE2; 8 GB → 2B" is
`capabilities` + `init`, which no upstream does. Not reinventing.

The serving layer, where reinvention would happen — each model already has a
path that adds no service class:

| Model | Path | New code |
| --- | --- | --- |
| ACE-Step 2B/XL | LocalAI backend (upstream Feb 2026); standalone container today | None — `variant:` knob exists |
| YuE2 | **ComfyUI node** — Comfy-Org ships official ComfyUI workflows (`YuE2: Text to Music`, `YuE2: Music Cover`) | A flag, following the `install_wan_s2v` pattern exactly |

What WOULD be reinventing: a third standalone song container. Do not.

Two unverified assumptions, check before building: YuE2 on ComfyUI's
torch 2.6.0+cu124 (the Comfy-Org repackaging implies compatibility; that is
inference, not evidence), and whether LocalAI has a YuE2 backend (probably not
yet — it is new and ComfyUI-first).

Evolution this suggests for the catalog: **licence as a first-class field**
next to `needs_vram_mb`. The install-time question becomes
"ace-step-2b (5 GB, Apache) / ace-step-xl (9 GB, Apache) / yue2 (12 GB, **NC**)"
— VRAM and licence tolerance decide, metadata not an engine.

---

## Known rough edges

| Issue | Where |
| --- | --- |
| `write_compose` regenerates the whole compose file from config on many commands. This overwrote the live `~/.puente/docker-compose.yml` during testing on 2026-10-10. The config system is the fragile part of the stack, not Docker | `puente/compose.py` |
| AnythingLLM overlaps Open WebUI | see B |
| 4 services are opt-in and superseded (Chatterbox, Fooocus, SwarmUI, MusicGen) — cost nothing when off, confusing when on | `services-inventory.md` |
| `residency_plan` is pure policy; no backend adapter turns `keep`/`load`/`release` into HTTP calls | `puente/demand.py` |
| The bcrypt hashes from `ec0681b` remain in git history. Rotated 2026-10-10, so this is historical rather than a live exposure | git history |
| `michael` is in both the `boxes` and `tutors` caddy groups. Rotating one does not rotate the other | `deploy/rotate-caddy-password.sh` |
| `search.borck.dev` is a separate VPS (31.97.67.189), up but serving **0 results** — engines block datacenter IPs. The local SearXNG is the working instance. Retire the hostname or fix the VPS; do not point anything at it meanwhile | VPS, not this repo |
| Vane (`search.locopuente.org`) is published but not running: `enabled: false`, no container. The hostname answers 401 (basic auth, `swarm`/ui group) and would 502 with correct creds. Decide: enable it or drop the hostname | `puente.yml`, Caddyfile |
| SearXNG's settings.yml gets rewritten by the container user (uid 977), which is why puente's seed silently lost to it before. If reseeding, chown to the host user first (done 2026-10-17) | `~/.puente/searxng/settings.yml` |
| `voicebox.py` emitted a top-level `restart_delay` — not in the compose spec. Docker compose rejected the ENTIRE generated file, so every compose command including the boot unit would have failed at the next reboot. Fixed 2026-10-17; `test_generated_compose_is_valid_for_real_docker` now runs real `docker compose config` against the generated file so this class of bug cannot ship silently again | `puente/services/voicebox.py`, `tests/test_generators.py` |

---

## Cleanliness pass, for when there is time

Nothing here is urgent; it is a list for a session with no deadline.

- [ ] Decide the engine question (A). If not migrating, mark ADR0012 superseded.
- [ ] `uv.lock` is untracked. Decide whether the project uses `uv` at all;
      `pyproject.toml` has no lock file and setuptools is the build backend.
- [ ] `docs/README.md` says "All 28 services" — now 30, and the split has changed.
      Update the index.
- [ ] `docs/README.md` lists the CLI commands and is now missing `catalog` and
      the `@profile` form of `enable`.
- [ ] Catalog entries could carry a `notes:` field for the awkward ones
      (Jupyter's empty `JUPYTER_TOKEN` is a real decision that deserves a
      paragraph somewhere more findable than a YAML comment).
- [ ] `puente capabilities` still suggests LocalAI in its `enable with:` hint
      but `suggest_backend()` never chooses it. Decide whether that is
      confusing or correct.
- [ ] Consider whether `puente doctor` should surface systemd drop-in pins at
      all, rather than only warning that it cannot see them.
- [ ] AnythingLLM snapshot on a timer — the script exists, nothing calls it.

---

## Commands worth remembering

```bash
# what can this box do
puente capabilities

# what is wrong with the host
puente doctor

# what does the catalog offer, and install a group
puente catalog
puente enable @office      # stirling-pdf, excalidraw, jupyter
puente enable @research    # searxng, anythingllm, open_notebook

# anythingllm backup — online sqlite backup, integrity-checked
deploy/snapshot-anythingllm.sh

# rotate a caddy basic-auth password
deploy/rotate-caddy-password.sh michael --password '...'

# where is a native service really pinned
systemctl cat ollama
```

---

## The honest note

The 2026-10-10 session found that two things this project had built — ACE-Step
support and a decisions API — already shipped upstream, and responded by
restructuring the project substantially. Asking that question was right.
Restructuring a working system in the same sitting as discovering it was not,
and part of a day was spent recovering a config file that testing had clobbered.

The chatbot is what matters for the next two weeks. The stack is in a good
enough state to leave alone. `puente doctor` should be clean, `puente up` should
be boring, and the engine question can wait for a machine that is not in use.