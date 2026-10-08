# Host setup — everything outside puente

> **Audited 2026-07-27 against the live box.** `puente.yml` describes the
> containers; this file describes everything the host must provide *before*
> `puente up` does anything useful. Without it, a clean install or a move to new
> hardware silently loses scheduled jobs, GPU pinning and every secret.

## 0. Check the host first: `puente doctor`

Run this before working through anything below. It inspects the host and reports
what is missing, printing the command that fixes each item. It is strictly
**read-only** — it never installs anything, never writes config, and never
restarts a service, so it is safe to run against a live box mid-incident.

```sh
puente doctor              # human-readable
puente doctor --json       # for CI or monitoring
puente doctor --services   # also probe each running service
```

Exit code is non-zero if any required check fails, so it works as a deployment
gate. It covers: Docker Engine and the Compose **v2** plugin, the NVIDIA
container runtime, `gpu:` pin validity, the pinned bridge subnet, ports 80/443,
unset proxy secrets, and the optional host tools.

It deliberately **does not** install the NVIDIA driver or the container toolkit.
Both are reported with the command to run, but the operator runs them — a driver
upgrade restarts Docker and risks every running service (see §1).

## 0b. Overriding the pinned network

The stack's Docker bridge is pinned to `172.28.0.0/24` on interface `puente0`.
The fixed name is what makes `sudo ufw allow in on puente0` stable across
reboots, and the fixed subnet is what lets `host.docker.internal` resolve to a
reachable gateway on Linux, where Docker's `host-gateway` alias points at the
unreachable `docker0`.

If that range is already taken — common on a VPN or k8s host — set your own in
`puente.yml` and re-run `puente up`:

```yaml
network:
  subnet: 10.44.0.0/24      # gateway is derived as .1
  name: puente0             # optional; keep it so the UFW rule still matches
```

`puente doctor` checks whichever range is actually configured, not the default.

## 1. Host prerequisites

Versions below are what this box runs, not minimums.

| | Version here | Notes |
| --- | --- | --- |
| Docker Engine | 28.1.1 | |
| Docker Compose | 2.35.1 | v2 plugin syntax (`docker compose`) |
| NVIDIA driver | 595.84 | see the caveat below |
| nvidia-container-toolkit | 1.17.7 | required for any GPU container |
| Python | 3.10.12 | for the puente CLI |
| `jq` | 1.6 | **required by `tutor-admin-runner.sh`** |

**Do not chase the newest driver.** 595 was installed for a CUDA 13 requirement
that turned out not to exist. Torch bundles its own CUDA runtime and only needs
a driver *new enough*, not a matching one. A driver upgrade is a real risk to
every GPU service; treat it as a last resort, not routine maintenance.

GPUs on this box, with the UUIDs `puente.yml` pins by:

```
0  NVIDIA GeForce RTX 3090     24 GB   GPU-15c8ed7d-e0dd-a4d8-530d-a46c78f3720f
1  NVIDIA GeForce RTX 4060 Ti  16 GB   GPU-ce79654c-917a-e928-ad48-aca7c8014f47
```

**Pin services by UUID, not by index.** `nvidia-smi` ordering is not stable
across cards or reboots, so an integer pin silently starts pointing at a
different card after a hardware change — which is how this box ended up loading
a model onto the wrong GPU once already (see
`deploy/ollama-classroom/10-classroom.conf` for that post-mortem). `puente gpu`
prints the UUIDs, `puente init` writes them, and `puente doctor` warns about any
remaining integer pins.

An integer pin still works if it matches current hardware, so existing configs
keep running unchanged — they just gain a warning until converted. The nvidia
container runtime accepts either form in `device_ids`.

The Ollama **drop-in** (§4) is the exception: it sets `CUDA_VISIBLE_DEVICES`,
which Ollama's Vulkan backend ignores, so it uses the UUID for a different
reason — see the comment in that file.

## 2. The puente CLI

Not pip-installed system-wide here — it runs from the repo. On a fresh host:

```sh
git clone <repo> ~/loco-puente
cd ~/loco-puente
python3 -m build && pip install --user dist/locopuente-*.whl
```

The system `setuptools` (59) is too old for PEP 621, hence `python -m build`
rather than `pip install .`. The PyPI package is **`locopuente`** (`puente` was
taken); the CLI it installs is still `puente`.

## 3. Secrets — none of these are in git

Recreate by hand on a new host. All are read at `puente up` and baked into
container environments.

| Path | Holds | Mode |
| --- | --- | --- |
| `~/.puente/anthropic.key` | Anthropic API key for LibreChat | 600 |
| `~/.puente/resend.key` | Resend SMTP key (LibreChat mail) | 600 |
| `~/.puente/caddy/.env` | every bearer token + bcrypt hash | 600 |
| `~/.puente/tutor-admin/credentials.txt` | tutor logins (reference copy) | 600 |

**Secrets must not live in `~/.zshrc`.** `${VAR}` in a compose file resolves from
the environment *of the process running compose* — which is nearly empty under
cron or systemd. That mismatch cost an evening on LibreChat SMTP. Puente resolves
values at `puente up` and writes them to `env_file`s instead.

In `caddy/.env`, every `$` in a bcrypt hash must be **doubled to `$$`** or
Compose interpolates it away.

Tokens currently expected by `caddy/.env`: `COMFYUI_TOKEN`, `SPEACHES_TOKEN`,
`SWARMUI_TOKEN`, `OLLAMA_TOKEN{,_2,_3}`, `VOICE_TOKEN`, `WORKREADY_TOKEN`,
`CHATTERBOX_TOKEN`, `SWARM_BCRYPT`, `TUTOR_{MICHAEL,SISI,FREDERIK}_BCRYPT`.

A new env var needs `--force-recreate`; a reload will not see it.

## 4. Native Ollama

Ollama runs on the **host**, not in a container (`install_method: native` on this
box; `external` also exists, for pointing puente at an Ollama it does not manage
at all). Install from ollama.com, then apply the drop-in:

```sh
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo cp deploy/ollama-classroom/10-classroom.conf /etc/systemd/system/ollama.service.d/
sudo cp deploy/ollama-classroom/ollama-preload.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ollama ollama-preload
```

The drop-in is what confines Ollama to the right GPU, binds `0.0.0.0` so Caddy
can reach it, and sets `KEEP_ALIVE`. Of the classroom tuning knobs tried, **only
`KEEP_ALIVE` earned its place** — `NUM_PARALLEL` crashed model loads and then
caused thrashing. Change one setting at a time.

## 5. systemd units

Install with the renderer, which fills in this host's paths and account:

```sh
./deploy/install-units.sh              # dry run — renders and prints, installs nothing
./deploy/install-units.sh --list       # which unit depends on which service
sudo DRY_RUN=0 ./deploy/install-units.sh
systemctl daemon-reload
systemctl enable --now puente-boot ollama-preload tutor-admin-runner
```

The units in `deploy/` are **templates**: `@PUENTE_HOME@`, `@PUENTE_USER@`,
`@PUENTE_BIN@`. The renderer substitutes them, and injects `PUENTE_CONFIG` into
every unit so none of them depends on `WorkingDirectory` to find `puente.yml`.
Override with environment variables when auto-detection is wrong:

```sh
PUENTE_HOME=/srv/loco-puente PUENTE_USER=operator sudo -E DRY_RUN=0 ./deploy/install-units.sh
```

Units whose backing service isn't enabled in `puente.yml` are **skipped** — a
watchdog for a container that never starts is a recurring red mark in the
journal that hides real failures.

To install a subset, name the units: `sudo DRY_RUN=0 ./deploy/install-units.sh
puente-boot.service tutor-admin-runner.service`.

| Unit | Purpose | Required? |
| --- | --- | --- |
| `puente-boot.service` | reconciles SwarmUI backends after a cold boot | yes, if SwarmUI is enabled |
| `ollama-warm.service` | preloads classroom models | optional |
| `ollama-preload.service` | keeps the pinned model resident | optional |
| `comfyui-idle-unload.{service,timer}` | frees VRAM when ComfyUI idles | optional |
| `swarmui-watchdog.{service,timer}` | self-heals image gen every 10 min (backend `errored`, stale CUDA) | recommended, if SwarmUI is enabled |
| `imagegen-weekly-restart.{service,timer}` | weekly overnight restart of comfyui+swarmui | optional |
| `tutor-admin-runner.service` | privileged half of the tutor admin UI | yes, for create/invite |

`puente-boot` matters more than it looks: without it, SwarmUI's external-ComfyUI
backend can latch `errored` after a cold boot and report "No backends available"
until reconciled. `swarmui-watchdog` is the safety net for everything that
survives a reconcile giving up — see [service-topology](service-topology.md).

Verify after install:

```sh
systemctl is-enabled puente-boot ollama-preload tutor-admin-runner
```

Note that `ollama-preload.service` lives in `deploy/ollama-classroom/`, not
`deploy/`, so the renderer does not install it. Copy it by hand along with the
drop-in (§4), since it is part of that tuning rather than general puente setup.

## 6. crontab

`crontab -l` is **not** in git. Current contents drive the LibreChat lab windows:

```cron
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

# Labs: Mon 08:00-10:00, Wed & Thu 16:00-18:00  (Australia/Perth)
# `open` fires at :58 — it recreates the container, waits for a 200 and warms
# the model (~25-30s), so opening on the hour would leave the first arrivals
# with no Claude models in the picker. `close` fires on the hour.
58 7  * * 1  /path/to/loco-puente/deploy/chat-window.sh open
0  10 * * 1  /path/to/loco-puente/deploy/chat-window.sh close
58 15 * * 3  /path/to/loco-puente/deploy/chat-window.sh open
0  18 * * 3  /path/to/loco-puente/deploy/chat-window.sh close
58 15 * * 4  /path/to/loco-puente/deploy/chat-window.sh open
0  18 * * 4  /path/to/loco-puente/deploy/chat-window.sh close

# Safety net: force-close nightly
0 23 * * *   /path/to/loco-puente/deploy/chat-window.sh close
```

The windows are the lab times themselves. They used to carry a ±30min buffer
(Mon 07:30-10:30, Wed & Thu 15:30-18:30); that was dropped on 2026-07-30 to cut
exposure of the paid Anthropic key from 9h/week to ~6h/week. Labs finish ~10min
before the hour in practice, so the close needs no tail padding.

`PATH` is set explicitly because cron's default is minimal and `docker` would
otherwise not be found — the same near-empty-environment trap as the secrets
above.

Cron's **working directory** was a second, separate trap. `puente` resolves
`puente.yml` from the *current* directory, and cron runs jobs from `$HOME`, so an
absolute path to the venv binary was not sufficient: it was found, but exited 1
with `No puente.yml found`. This silently broke every lab window from the
2026-07-25 reboot to 2026-07-30: the error goes to *stdout*, which the script's
`up` calls were discarding, and `set -e` then aborted before the first log line —
so `chat-window.log` simply stopped while the cron journal showed each job firing
normally. When debugging this class of failure, note that running the script by
hand cannot reproduce it, because the interactive cwd is the repo; schedule a
real cron entry wrapping it in `bash -x … >>trace.log 2>&1` and read the last
traced line.

Two things now prevent a recurrence: `puente` searches **upward** from the cwd
for `puente.yml`, and `chat-window.sh` exports `PUENTE_CONFIG` explicitly rather
than relying on the cwd. The `cd` it still does is belt-and-braces.

## 7. DNS and TLS

`locopuente.org` has **no wildcard record**. Every subdomain needs its own A
record pointing at the host's public IP, and it must be **DNS-only (grey cloud)**
in Cloudflare — a proxied record breaks Caddy's ACME challenge. The apex points
at GitHub Pages for the Astro site and is unrelated to the box.

Ports 80 and 443 must reach the host. Caddy owns both.

## 8. Data that is not code

Not in git and not recreatable — back these up separately:

- `~/.puente/librechat/` + the `librechat-mongo` volume — **all student accounts
  and chat history**.
- `~/.puente/anythingllm/` — workspaces (~70 preserved through the migration).
- `~/.puente/comfyui-basedir/`, `~/.puente/swarmui/` — models and outputs.
- `~/.puente/tutor-admin/audit.log` — who did what to which account.

`~/.puente/docker-compose.yml`, `~/.puente/caddy/Caddyfile` and
`~/.puente/tutor-admin/app.py` are **generated** — do not hand-edit them; they
are overwritten at every `puente up`. Edit `puente.yml` and the repo sources.

## 8b. Custom images — what pulls and what compiles

Five services use a puente-built image rather than an upstream one, all published
to GHCR by `.github/workflows/build-images.yml`:

| Service | Image | Built from |
| --- | --- | --- |
| swarmui, fooocus, comfyui, nodepad | `ghcr.io/michael-borck/puente-<svc>` | `puente/dockerfiles/<svc>/` |
| voicebox | `ghcr.io/michael-borck/puente-voicebox` | the voicebox git repo, at the SHA pinned in `puente.yml` |
| tutor-admin | `ghcr.io/michael-borck/puente-tutor-admin` | `puente/dockerfiles/tutor-admin/` |

Each service emits **both** `image:` and `build:` in its compose fragment, so
Docker pulls the published image and only falls back to compiling from source if
that pull fails. A source build of voicebox takes 10–20 minutes with long silent
stretches, and `puente up` warns when it is about to happen.

**All are `linux/amd64` except tutor-admin**, which is also published for
`linux/arm64` because it is plain Python and needs no CUDA. An arm64 host can run
tutor-admin but not the GPU services; `puente doctor`'s `image-arch` check reports
the mismatch and points at the `build:` fallback. Do not "fix" that by adding
`platforms:` to the workflow for the others — those are CUDA services and CUDA
does not exist on Apple silicon, so a naive multi-arch build would publish an
arm64 image that cannot do GPU work at all.

`tutor-admin`'s image carries no application code — just the interpreter and a
pinned `pymongo`. The app is one stdlib file that `pre_start` copies into the bind
mount on every `up`, so code changes still ship without a rebuild.

Voicebox's `build_ref` is pinned to a **commit SHA**, not a branch, and the
workflow reads that same SHA out of `puente.yml` (rejecting a branch name). That
is what keeps a pull and a local source build producing the same image. After
voicebox PR #889 merges upstream, drop `build_ref` from `puente.yml` to track
upstream again, and re-run the workflow.

To force a source build rather than a pull — to test an unreleased voicebox
commit, or on a host the amd64 image cannot run:

```yaml
  voicebox:
    image: null
```

## 9. Known cruft on this box

Not needed on a new host — listed so a future audit does not mistake them for
dependencies:

- `ollama-secondary.service` — disabled, inactive. Leftover from the two-GPU
  Ollama split. **Not in the repo.**
- Containers `anythingllm` and `nginx-proxy-manager` — both `Exited` for weeks,
  publishing nothing. Pre-migration remnants (AnythingLLM moved into puente;
  NPM was replaced by `puente-caddy`).

## 10. Order of operations for a clean install

1. Docker + Compose + NVIDIA driver + container toolkit + `jq`
2. Clone the repo; build and install the CLI
3. `puente doctor` — confirm steps 1 landed. It names anything still missing
   and prints the fix; it will not apply it.
4. Recreate the secrets in `~/.puente/` (§3)
5. Install native Ollama + drop-in (§4)
6. DNS records, DNS-only (§7)
7. Restore data volumes if migrating (§8)
8. `puente up`
9. systemd units + `crontab` (§5, §6)
10. Verify: `puente doctor --services`, `systemctl is-enabled …`, then load each
    public hostname and check for a valid certificate

Note on `puente.yml` discovery: since 0.1.3 the CLI looks for `puente.yml` in the
current directory and then **upward**, so `puente up` works from a subdirectory of
the stack. Where that is not enough — cron and systemd have an unrelated working
directory — set `PUENTE_CONFIG=/path/to/puente.yml`. A missing config is now a
hard error rather than a silent fall back to defaults, because `puente up`
regenerates the compose file from whatever it loaded.

## See also

- `docs/tutor-admin.md` — the tutor UI and its host-side runner
- `docs/caddy-migration.md` — proxy model and auth policy
- `docs/service-topology.md` — what runs in vs outside puente
- `docs/adr/` — why these choices were made
