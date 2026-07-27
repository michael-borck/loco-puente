# `docs/` — operator runbooks

**These files are not published anywhere.** They are read in the repo (and cited from
source comments in `puente/services/*.py`). Nothing builds or serves this directory.

There are three separate web surfaces in this project, and they are easy to confuse:

| Surface | Source | What it is |
|---|---|---|
| **locopuente.org** (GitHub Pages) | `src/` — Astro | `src/pages/index.astro` is the marketing landing page and owns `/`. `src/content/docs/*.md` become the public docs (`/services`, `/stack`, `/choosing`, `/hardware`, …) via Starlight. Deployed by `.github/workflows/deploy-pages.yml`. |
| **`puente portal`** | `puente/templates/portal/index.html.j2` | The on-box service dashboard. Rendered by `puente/portal.py`; built dynamically from enabled services in `puente.yml`. |
| **`docs/`** (here) | — | Operator runbooks. Read as plain markdown in the repo. |

There is **no `puente serve` or `puente docs` subcommand.** The CLI commands are
`init, install, up, down, enable, disable, status, doctor, gpu, connect, portal, version`.

## Don't duplicate the public docs here

`docs/` once carried copies of `architecture.md`, `choosing.md`, `hardware.md`,
`philosophy.md`, `poc.md`, `roadmap.md`, `services.md`, `stack.md` and an `index.md`.
They were duplicates of `src/content/docs/`, differing only in link syntax, kept in sync
by hand and already starting to drift. They were removed. **Public/narrative docs belong
in `src/content/docs/`.** Only put a file here if it is an operator runbook that would be
noise on the website.

## What lives here

| File | Subject |
|---|---|
| `host-setup.md` | **Everything outside puente**: prerequisites, secrets, systemd units, crontab, DNS. Start here for a clean install or a move to new hardware |
| `adr/` | Architecture Decision Records — why the non-obvious choices were made, and what was rejected |
| `tutor-admin.md` | The tutor-facing LibreChat account UI and its host-side runner |
| `service-topology.md` | What runs in vs outside puente; the voice-service overlap |
| `caddy-migration.md` | The nginx-proxy-manager → Caddy cutover |
| `gpu-swap-3090.md` | The 2060 Super → 3090 swap, and its verification |
| `image-generation-setup.md` | ComfyUI + SwarmUI integration |
| `sadtalker-api.md`, `wav2lip-api.md`, `liveportrait-api.md` | Talking-head / lip-sync ComfyUI nodes |
| `voicebox-api.md` | The **active** TTS service (port 17493) |
| `chatterbox-api.md` | **Retired.** Kept for the CUDA/GPU-pinning notes |
| `student-ai-options.md` | Student-facing guide to the four AI options |
