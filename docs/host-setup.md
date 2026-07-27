# Host setup — everything outside puente

> **Audited 2026-07-27 against the live box.** `puente.yml` describes the
> containers; this file describes everything the host must provide *before*
> `puente up` does anything useful. Without it, a clean install or a move to new
> hardware silently loses scheduled jobs, GPU pinning and every secret.

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

GPUs on this box — **verify indices after any hardware change**, because mixed
cards reorder:

```
0  NVIDIA GeForce RTX 3090    24 GB
1  NVIDIA GeForce RTX 4060 Ti 16 GB
```

`nvidia-smi` ordering is not stable across cards; `gpu:` pins in `puente.yml`
refer to these indices, so confirm them before starting GPU services.

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

Copy from `deploy/`, then `daemon-reload` and `enable --now`. All units hardcode
`User=michael` and `/home/michael/loco-puente` — **edit both on a new host.**

| Unit | Purpose | Required? |
| --- | --- | --- |
| `puente-boot.service` | reconciles SwarmUI backends after a cold boot | yes, if SwarmUI is enabled |
| `ollama-warm.service` | preloads classroom models | optional |
| `ollama-preload.service` | keeps the pinned model resident | optional |
| `comfyui-idle-unload.{service,timer}` | frees VRAM when ComfyUI idles | optional |
| `tutor-admin-runner.service` | privileged half of the tutor admin UI | yes, for create/invite |

`puente-boot` matters more than it looks: without it, SwarmUI's external-ComfyUI
backend can latch `errored` after a cold boot and report "No backends available"
until reconciled.

Verify after install:

```sh
systemctl is-enabled puente-boot ollama-preload tutor-admin-runner
```

## 6. crontab

`crontab -l` is **not** in git. Current contents drive the LibreChat lab windows:

```cron
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

# Mon 07:30-10:30, Wed & Thu 15:30-18:30  (Australia/Perth)
30 7  * * 1  /home/michael/loco-puente/deploy/chat-window.sh open
30 10 * * 1  /home/michael/loco-puente/deploy/chat-window.sh close
30 15 * * 3  /home/michael/loco-puente/deploy/chat-window.sh open
30 18 * * 3  /home/michael/loco-puente/deploy/chat-window.sh close
30 15 * * 4  /home/michael/loco-puente/deploy/chat-window.sh open
30 18 * * 4  /home/michael/loco-puente/deploy/chat-window.sh close

# Safety net: force-close nightly
0 23 * * *   /home/michael/loco-puente/deploy/chat-window.sh close
```

`PATH` is set explicitly because cron's default is minimal and `docker` would
otherwise not be found — the same near-empty-environment trap as the secrets
above.

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
3. Recreate the secrets in `~/.puente/` (§3)
4. Install native Ollama + drop-in (§4)
5. DNS records, DNS-only (§7)
6. Restore data volumes if migrating (§8)
7. `puente up`
8. systemd units + `crontab` (§5, §6)
9. Verify: `puente status`, `systemctl is-enabled …`, then load each public
   hostname and check for a valid certificate

## See also

- `docs/tutor-admin.md` — the tutor UI and its host-side runner
- `docs/caddy-migration.md` — proxy model and auth policy
- `docs/service-topology.md` — what runs in vs outside puente
- `docs/adr/` — why these choices were made
