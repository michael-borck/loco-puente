# Tutor admin — LibreChat account administration for non-shell staff

> **Status on this box: LIVE (2026-07-27).** `tutors.locopuente.org`, three
> accounts (michael, sisi, frederik), `tutor-admin-runner.service` enabled.

Tutors need to unblock students — resend a verification link, force-verify when
mail fails, create an account once self-registration is closed — without holding
a shell account on the machine that also runs Ollama, ComfyUI, SwarmUI and the
Anthropic key file.

LibreChat cannot do this on its own. Its admin API is **read-only**:
`/api/admin/users` exposes `listUsers` and `searchUsers` and nothing else, so
even a LibreChat `ADMIN` can see who registered and fix nothing. Everything that
actually unblocks a student is a CLI script inside the container.

## What tutors can and cannot do

| Available | Withheld |
| --- | --- |
| list / search accounts | delete an account |
| resend verification | ban a user |
| force-verify (SMTP escape hatch) | change roles |
| find duplicate addresses | open/close registration |
| create an account | |
| invite by email | |

The split is **blast radius, not trust**. Delete destroys chat history
irreversibly; granting `ADMIN` is privilege escalation that would let a tutor
grant it to anyone, including a student. Both stay on the operator's CLI
(`deploy/librechat-users.sh`). Everything a tutor can reach is additive or
reversible.

## Architecture, and why the runner is not a container

Two halves, deliberately separated:

```
  internet ── Caddy (basic_auth, TLS) ── puente-tutor-admin ──── Mongo
                    per-tutor login          (container)     └── LibreChat HTTP
                    X-Tutor-User                  │
                                            spool directory      NO docker socket
                                                  │
                              tutor-admin-runner.service  ── docker exec ── LibreChat
                              (HOST systemd, runs as you)     npm create-user
                                                              npm invite-user
```

`create` and `invite` are npm scripts *inside* the LibreChat container: they hash
passwords and mint invite tokens using LibreChat's own internals, and
reimplementing either would drift the moment upstream changes. Reaching them
needs `docker exec` → the Docker socket → **root on the host**.

Mounting that socket into an internet-facing web service would mean one bug there
escalates to the whole machine. So the web app has **no socket and cannot exec
anything**. It writes a JSON request into a spool directory; the host-side runner
validates it and does the work. The privileged half has no network listener, so
it cannot be attacked directly — only handed files by a process that could
already create those accounts legitimately through its own UI.

**Containerising the runner would defeat this.** A container with
`/var/run/docker.sock` mounted writable is not meaningfully more contained than a
host process, and it would sit on the same network as the exposed app.

Consequence: if the runner is stopped, list / search / duplicates / resend /
force-verify all still work (those go straight to Mongo or LibreChat's HTTP API).
Only `create` and `invite` block, and they report that the runner is inactive
rather than failing silently.

## Authentication

The app authenticates **nothing** itself. Caddy terminates HTTP Basic before any
request reaches it, and forwards the authenticated username in `X-Tutor-User`,
which the app records in its audit log. That header is attribution only, never
authorisation — it is trustworthy solely because the app is unreachable except
through Caddy.

That unreachability is enforced by the compose fragment binding the container to
`127.0.0.1`, and by Caddy reaching it over the compose network
(`proxy.upstream: tutor-admin`, the container name). **Do not publish this port
on `0.0.0.0`** — that would expose unauthenticated account administration to the
LAN.

**One Caddy account per person, never a shared login.** The username lands in the
audit log for every action; a shared account makes every entry read "tutors" and
answers "somebody" when you ask who force-verified something.

## Rebuilding on a new machine

Assumes puente, LibreChat and Caddy are already up.

### 1. DNS

`locopuente.org` has **no wildcard record** — each subdomain needs its own A
record pointing at the host's public IP, and it must be **DNS-only** (grey cloud
in Cloudflare). An orange-cloud/proxied record breaks Caddy's ACME challenge.

```
tutors.<your-domain>.   A   <host public IP>
```

Add it *before* starting the service, or Caddy's first certificate attempt fails
and retries with backoff.

### 2. Basic-auth credentials

One bcrypt hash per tutor, into `~/.puente/caddy/.env`:

```sh
docker run --rm caddy:2-alpine caddy hash-password --plaintext '<password>'
```

Every `$` in the resulting hash must be **doubled to `$$`** in the env file —
Compose interpolates `$` in `env_file` values and would otherwise mangle it:

```
TUTOR_MICHAEL_BCRYPT=$$2a$$14$$....
TUTOR_SISI_BCRYPT=$$2a$$14$$....
```

### 3. `puente.yml`

```yaml
services:
  tutor_admin:
    enabled: true
    install_method: docker
    port: 8091            # NOT 8090 on this box — portal already holds it
    managed: true
    allowed_domains:
    - curtin.edu.au
    - student.curtin.edu.au
    - postgrad.curtin.edu.au
    proxy:
    - host: tutors.locopuente.org
      auth: basic
      basic_group: tutors
      forward_user_header: X-Tutor-User
      upstream: tutor-admin      # container name — see below

  caddy:
    users:
      tutors:
        michael: TUTOR_MICHAEL_BCRYPT
        sisi: TUTOR_SISI_BCRYPT
        frederik: TUTOR_FREDERIK_BCRYPT
```

`upstream: tutor-admin` is required. Without it Caddy uses `caddy.upstream_host`
(the LAN address), where nothing is listening because the container binds to
localhost — the symptom is a 502 *after* a successful login.

`allowed_domains` matters because `create`/`invite` bypass the signup page's own
allowlist by design. Without it a tutor could add any address at all. It is
re-checked independently in the runner, which treats anything in the spool as
untrusted input regardless of what wrote it.

### 4. Start it

```sh
puente up tutor_admin caddy
```

Note `tutor_admin` declares `depends_on: librechat`, so a bare
`docker compose up tutor-admin` also **recreates LibreChat** — roughly 10s of
downtime, and it re-bakes `ANTHROPIC_API_KEY` from the ambient environment
(empty under cron or a non-interactive shell). Use `--no-deps` when touching one
service:

```sh
docker compose -f ~/.puente/docker-compose.yml up -d --no-deps --force-recreate caddy
```

Adding or rotating a tutor is a **recreate, not a reload** — env vars are baked
in at container creation. A Caddyfile-only change (e.g. a new route) can use
`docker exec puente-caddy caddy reload --config /etc/caddy/Caddyfile`.

### 5. Install the runner

```sh
sudo cp deploy/tutor-admin-runner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tutor-admin-runner
```

The unit hardcodes `User=michael` and the repo path — edit both on a different
host. It needs `jq`.

### 6. Verify

```sh
curl -s -o /dev/null -w '%{http_code}\n' https://tutors.<domain>/          # 401
curl -s -u 'sisi:<pw>' https://tutors.<domain>/ | grep -o 'class=who>[^<]*' # sisi
systemctl is-active tutor-admin-runner                                      # active
```

Then create a throwaway account through the UI and delete it with
`deploy/librechat-users.sh delete <email>` — that exercises the whole spool path,
which is the only part that can be broken while every page still loads fine.

## Operational notes

- **Credentials:** `~/.puente/tutor-admin/credentials.txt` (mode 600).
- **Audit log:** `~/.puente/tutor-admin/audit.log`, one JSON line per action:
  `{ts, actor, action, target, ok, detail}`.
- **Runner log:** `~/.puente/tutor-admin/runner.log`, plus
  `journalctl -u tutor-admin-runner`.
- **Spool:** `~/.puente/tutor-admin/spool/`. Should be empty at rest. Files
  there hold **plaintext passwords in flight** — mode 0640, owned by the runner
  user, removed immediately after execution.
- **App code** is copied into `~/.puente/tutor-admin/app.py` at every
  `puente up` from `puente/tutor_admin/app.py`. Edit the repo copy; the deployed
  one is overwritten.

## Traps found the hard way

- **`create-user` takes the password as a 4th positional argument** and asks
  about email-verification *afterwards*. Feeding answers to its prompts
  desynchronises and `docker exec -i` **hangs forever holding the queue**. Use
  `create-user -- <email> <name> <username> <password> --email-verified=true`
  with no stdin at all.
- **The container writes the spool as root; the runner reads it as you.** Files
  need an explicit `chown` (`SPOOL_UID`/`SPOOL_GID`) and the directory needs
  group-execute, or the runner cannot open its own queue.
- **npm exits 0 on some upstream failures** — "A user with that email already
  exists!" prints and then `silentExit(1)`. The runner checks the output text,
  not just the exit code.
- **`create-user` echoes the entire resolved `librechat.yaml`** before doing
  anything, in ANSI colour. The runner strips escapes and keeps only outcome
  lines, or the audit log fills with kilobytes of config.
- **The page template can use neither `%`-formatting nor `str.format`** — the CSS
  is full of literal `%` (`width:100%`, every `@media`) and braces. Both raise.
  The page is assembled by concatenation.

## See also

- `deploy/librechat-users.sh` — the operator CLI; superset of this UI, plus
  delete / ban / role / registration control.
- `docs/caddy-migration.md` — the proxy model and auth policy.
- `deploy/chat-window.sh` — the Anthropic key schedule, and why a recreate
  differs from a restart.
