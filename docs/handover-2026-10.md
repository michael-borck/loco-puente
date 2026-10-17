# State on 2026-10-10, and what to pick up in two weeks

**Written at the end of the 2026-10-10 session; updated 2026-10-17. Read this first when you come back.**

This is a handover, not a runbook. It answers three questions: what is running
right now, what is staged but unverified, and what should be decided before
anything else is built.

The plan: ship the chatbot over the next week or two, do not restructure the
stack, then revisit the engine migration with the chatbot working.

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
| Vane | docker, enabled 2026-10-17 | `search.locopuente.org` — cited AI search, gated by `swarm`/ui basic auth. Was published-but-dead for weeks; now running with prior config intact |

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

## Publishing policy, recorded 2026-10-17

**Personal install = private by default. Institution = hybrid. The `proxy:`
block is the policy switch.**

The trigger was counting the stack's browser doors: eleven hostnames share one
basic-auth credential (`swarm`/ui group), all on the public internet. That is
the weakest part of the stack's posture, and for a single-user box it buys
nothing — the week's evidence is that public exposure is what *broke* things
(the SearXNG VPS lost its engines to bot traffic; scanners hammer every open
door).

| | Personal | Small institution |
| --- | --- | --- |
| Who reaches it | The operator's own devices | Students, staff, anonymous visitors |
| Model | **Tailnet-only** — nothing public | **Hybrid** — public only where required |
| Auth | WireGuard device keys; no passwords, no prompts | App accounts + Caddy gates on public doors |
| Admin surfaces (glances, jupyter, uptime) | Tailnet | Tailnet — not student-reachable |
| Chatbot on a webpage | n/a | **Must stay public** — that is its job |

- **Tailscale is the personal answer, and it is a single static binary** — by
  the design principle above, native wins. No port forwarding, no DNS, no cert
  renewals, no scanner noise. Inside the tailnet, MagicDNS names replace the
  hostname circus and the basic-auth gates become redundant.
- **Not Tailscale vs Caddy — a shrink of the public surface.** The institution
  case keeps Caddy for the few genuinely-public things (chatbot embed, student
  chat with real accounts) and moves operator surfaces behind the tailnet.
- **Additive, not a rewrite.** Chatbot fortnight changes nothing:
  `chat.eduserver.au` stays public regardless. Install Tailscale, migrate the
  admin doors over time, shrink the public set deliberately.
- Tailscale Funnel exists for exposing one service without router changes —
  fine for a personal NAT-bound box; institutions are better on plain Caddy.
- Longer-term seam worth knowing: the shared `swarm` credential across 11 doors
  is the boxes-group pattern again. More groups + per-door `basic_group:` is
  the fix when someone needs one door without the rest. On a tailnet the
  question mostly dissolves.

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

### G. n8n — evaluated 2026-10-17: fits, wire at the revisit

The ask: "do we or should we add n8n?" Verdict: **yes, as an opt-in catalog
entry (Tier 3), off by default — and it needs no deep integration.**

n8n is node-based workflow automation: cron, webhooks, hundreds of API
connectors, and AI-agent nodes that speak **Ollama and any OpenAI-compatible
endpoint natively** — the same engine story as Presenton. It is the natural
automation layer for a stack that just committed to API-first: n8n drives the
stack's existing APIs rather than the stack growing workflow internals.

| Aspect | Verdict |
| --- | --- |
| Mechanically | Docker image, CPU-only (`needs_vram_mb: 0`), port 5678, volume for `~/.n8n` — a textbook catalog entry, ~15 min by the Presenton pattern |
| Licence | **Sustainable Use License — NOT OSI open source.** Free to self-host and use internally (personal or small institution: fine); embedding it into a paid offering is not. Surface it exactly like YuE2's NC — licence metadata belongs at install time |
| Overlap | None real. Adjacent to the OpenClaw open question in vision.md ("do we integrate agents, or keep the APIs good enough to be driven?") — n8n answers that question by being a *client*. LocalAI's built-in agents do not overlap it: n8n is glue and schedule, not inference |
| Caution | n8n webhooks are an ingress. Whatever the publishing policy says (see above) applies to it doubly — tailnet-only for personal; gated behind Caddy for an institution |

Why not wired today: chatbot fortnight, nothing needs it, and every new surface
is attack surface until the publishing policy lands. At the revisit: pin a
version tag (n8n publishes real versions — no `latest` problem), write the
entry, add the config field, done.

### H. Harness strategy — the 80/20 chat (2026-10-17)

The operator's stated grand vision: **one chat harness that does the 80%** —
chat, images, songs, code, presentations in one conversation — with dedicated
UIs (ComfyUI, SwarmUI, the editor) reserved for the power 20%. This is not a
new direction; it is vision.md commitment 3 ("capabilities are APIs, the UI is
a client") finally named as the product surface. The harness is a *client*,
swappable by design — which is exactly why this decision can be made without
touching the stack.

Current incumbent: **Open WebUI.** Working today against Ollama, SearXNG
(engine seeded 2026-10-17), and the SwarmUI/ComfyUI image engine. The one
missing piece: **Open WebUI + Presenton via MCP** — Presenton ships `/mcp`,
Open WebUI is a documented MCP client; wire an API key and chat gains
"make me a deck". ~30 min at the revisit; fallback is a small Open WebUI Tool
over the REST API. Caveats: deck outlines want `gemma4:12b` over the 3.4 GB
model, and generation is a "working on it…" turn, not instant.

Candidate: **Odysseus AI** (PewDiePie's workspace; the independent guide is
odysseusai.dev, repo odysseus-dev/odysseus, ~86k stars, AGPL-3.0). It is the
80/20 vision as one product: chat, agents (shell/files/web/memory behind
approval gates), deep research on bundled SearXNG, document editor, memory,
email/calendar, PWA. Honest cons: **early maturity, no tagged releases** (it
cannot be pinned — fights ADR0009 and the catalog's reproducibility rule),
celebrity-maintenance risk, and its "Cookbook" (hardware scan, model fit
scoring, llama.cpp/vLLM/SGLang serving) is **building into Puente's
capabilities-and-engine layer** — the QVAC warning shot again.

Verdict, not yet acted on: **run Odysseus as a side-by-side experiment at the
revisit** — one compose file, CPU-only container, still served by Ollama, so
the cost is disk and an hour. Keep Open WebUI as production harness for the
chatbot. Decide on experience, not vibes.

### I. The institutional path — closing the gap for students (2026-10-17)

The mission, made concrete: students who cannot afford a $20/month
subscription get parity — "good enough, not frontier" — via a box someone
donates, then an institution hosts. Asked whether PoC-then-cloud is dreaming:
**no, it is the standard adoption curve, but the economics must be pitched
honestly.**

The scale ladder, with the trap named:

| Stage | What serves it | Cost shape |
| --- | --- | --- |
| Demo / PoC | The existing box | $0, donated hardware |
| One class (~40) | One box + **lab windows** (already built, ADR0005) | $0 + operator time |
| One school (500–2,000 active) | 2–4 GPUs on-prem or cloud (A10/L4 class, ~$700–1,400/mo each on Azure) | Real money, plausibly under subscriptions |
| 60,000 students | A fleet or the institution's HPC/cloud tenant | Queueing + tiered access, never one box |

**Do not pitch "60k students on Azure".** The institution's baseline is not
$20/head — Copilot/Gemini are already campus-wide, and the real comparison
includes students who simply go without. The three cards that actually work:

1. **Equity** — widening participation: the student who cannot pay gets
   parity. Institutions already speak this language.
2. **Data sovereignty** — student work never leaves campus; no training on
   submissions, no retention surprises. This IS the zero-trust answer, and it
   is the strongest card held.
3. **Pedagogical control** — models frozen per semester (reproducible
   assessment), no mid-term behaviour changes, and the local-vs-frontier
   side-by-side in LibreChat is a teaching feature no subscription offers.

The "full suite" claim is credible because it already runs: chat, code,
image, video (Wan2.2, 24 GB tier), music, presentations, RAG, voice, plus the
office tools. The demo is not a mock-up; it is this box.

**The #1 technical gap for adoption is OIDC/SAML single sign-on** against the
institution's identity provider (Azure AD at Curtin). Open WebUI and LibreChat
support OIDC; verify AnythingLLM. Everything else in the zero-trust ask maps
onto the publishing policy (Decision above): SSO-gated reverse proxy, admin
surfaces off the student network, public only the chatbot.

Business-case skeleton, for drafting at the revisit: equity framing
(vision.md in institutional language) → privacy/sovereignty → cost table
(above) vs $20/head AND vs go-without → the side-by-side pedagogy → scale
ladder with the lab-window mechanism → risks (support burden, GPU procurement,
model churn, assessment integrity) → ask: one class, one semester, one box.

### J. UI shape — chat by default, a power-user tab for the rest (2026-10-17)

Yes, the operator's instinct is right, and the portal already contains most of
it — it renders views from config (`VIEWS` in portal.py: student/admin), it
already shows interface and API doors separately, and it regenerates from
puente.yml. What is missing is intent. Recorded shape, nothing implemented:

- **Default view = the harness.** Landing shows one dominant "Start here"
  action pointing at whichever harness won Decision H — chat with images,
  search, documents, decks behind it. This is the 80%.
- **Second view = "Power user"** — the existing app grid (ComfyUI, SwarmUI,
  Jupyter, ACE-Step, Voicebox…), each card still showing its separate
  interface and API doors. This is the 20%, and it is where the dedicated UIs
  live unchanged.
- The portal stays a **router, never an app**: it points at surfaces, it does
  not embed them. If Odysseus wins Decision H, the default link changes in
  config and nothing else moves.
- Implementation when it happens: a rename/restructure of `VIEWS` (the
  "student/admin" split becomes "chat/power"), a `default_view` config knob,
  and first-card prominence for the harness link. Small, template-level work.

### K. Stack gaps — what is missing, what to refuse (2026-10-17)

Honest gap analysis against the mission, ordered by how much they block the
next rung. With the vision.md rule applied up front: this is a list to work
from, not a feature pile — several plausible additions are refused below.

1. **Whole-stack backup/restore.** Only AnythingLLM has a snapshot script.
   LibreChat's Mongo, the vector stores, and every stateful volume have
   nothing. For a classroom, losing a semester of AnythingLLM workspaces is
   the worst case; for an institution it is disqualifying. A `puente backup`
   walking the stateful services (the pattern in
   `deploy/snapshot-anythingllm.sh` generalised) is the single most valuable
   missing tool.
2. **OIDC/SSO** — already the #1 adoption gate (Decision I); restated here so
   the gap list is complete.
3. **Data analysis / chat-with-a-spreadsheet.** The commonest student academic
   need after writing help, and the stack's weakest story — but it is an
   enablement task, not a missing project. Open WebUI ships a built-in code
   interpreter (Pyodide in-browser by default, or a Jupyter endpoint for
   larger data — and the stack already runs Jupyter); LibreChat has a Code
   Interpreter API option. Standalone OSS if the built-in proves insufficient:
   **PandasAI** (23.9k stars, MIT except `ee/`, CSV/SQL/parquet, Docker
   sandbox, LiteLLM → Ollama-compatible; natural shape is a harness Tool
   wrapper) and Open Interpreter (~50k stars, AGPL-3.0 — fine unless offered
   as a hosted service). The constraint is the model, not the tool: test with
   `gemma4:12b`. Do not build a fourth interface for this.
3b. **Opinionated means one (maybe two) per capability** — confirmed as the
   rule, per vision.md commitment 2. The picks: LocalAI-then-Ollama for the
   engine (llama.cpp justified by ADR0010), Open WebUI harness pending
   Decision H, Voicebox/Speaches for TTS/STT, ACE-Step for music, Presenton
   for decks, SearXNG (+Vane as the AI layer). The four superseded services —
   Chatterbox, Fooocus, SwarmUI, MusicGen — are the concrete pruning task:
   deprecate or move to the catalog as legacy. Blocked only by Decisions A
   and B.
4. **An update procedure.** Images are pinned deliberately, but there is no
   `puente upgrade` and no documented path from "new pinned tags exist" to
   "stack updated safely" (pull → regenerate → recreate → verify → rollback).
   Fine for one box; institutional rung requires it.
5. **Fair-share metering.** One GPU, 40 students: queueing exists (Ollama),
   per-user fairness does not. Real only at the institutional rung — a
   LiteLLM-style proxy or the harness's admin stats. Defer explicitly;
   building it now is feature accumulation.

Refused, with the reason recorded so they stay refused: a custom agent
framework (upstream harnesses + n8n cover it — Decision H/G), a mobile app
(the harnesses ship PWAs), video conferencing, social features, and any
fourth "chat but slightly different" interface. The stack's job is surfaces
and glue, and every one of these is a surface someone else already ships.

### The uniqueness question, answered honestly (2026-10-17)

The operator asked: "Is Puente even relevant? I have trouble seeing the
uniqueness." Recorded here because the doubt keeps recurring and deserves a
fixed answer.

**The doubt is correct for an expert operator.** Michael can hand-wire
Ollama + Open WebUI + Tailscale in an afternoon; for HIM the glue feels like
overhead. But the mission (vision.md) is the person who cannot. For that
person, the glue is the product — and this session alone harvested the failure
surface it prevents: a searxng container zombie-mounting a test directory, a
compose key that would have killed the boot unit, a GPU pin reported valid
while being inert, a search engine silently 403-ing, a settings file the
container owned. None of those are harness problems. All of them are the
reason a non-expert's afternoon of hand-wiring becomes a dead end.

What is genuinely Puente's, in priority order:

1. **Hardware-fit assessment** — what THIS box can do, before install.
   (Shrinking: Odysseus's Cookbook and QVAC's weightless registry both
   encroach. Watch both.)
2. **Hardware-aware orchestration of the whole stack** — GPU pins, VRAM
   budgets across ComfyUI + Voicebox + ACE-Step + LLM on one small card,
   auth boundaries, secrets policy, pinning, boot order. No harness does
   this; compose files do not decide it.
3. **Maintenance tooling** — doctor, catalog, status, snapshots, rotation.

What is NOT Puente's, by design: the harness, the engine, the apps. All
swappable clients. If Odysseus wins the harness slot, Puente wires Odysseus
the way it wired Open WebUI — and that is the architecture succeeding, not
failing. The thing that would make Puente genuinely irrelevant is upstream
harnesses doing hardware-aware orchestration of full stacks. Odysseus's
Cookbook is the first serious warning shot; check it at the revisit.

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
| Vane (`search.locopuente.org`) — resolved 2026-10-17: now enabled and running behind the `swarm`/ui gate. Remaining question is the credential pattern itself: 11 doors share one basic-auth password, and the operator had forgotten it (reset available via `deploy/rotate-caddy-password.sh swarm`). The publishing-policy note above is the real answer | `puente.yml`, Caddyfile |
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