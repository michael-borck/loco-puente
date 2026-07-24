# Reverse proxy: Caddy as a puente service

> **Status on this box: cutover DONE (2026-07-08).** `caddy.enabled: true`,
> `puente-caddy` binds `:80`/`:443`, and `nginx-proxy-manager` is stopped.
> The cutover procedure below is retained for a fresh deployment.

Puente can run its own reverse proxy (Caddy) as an optional service, the same
way it runs every other container. When enabled, Caddy fronts every service
that declares a `proxy:` block — terminating TLS (automatic Let's Encrypt) and
enforcing a per-service auth policy. When disabled, you bring your own proxy
(nginx-proxy-manager, Traefik, …) and puente stays out of the way.

This replaces the old model where the proxy lived outside puente and every
route was hand-configured in NPM's database (not captured in git, and prone to
silent reversion when the NPM UI regenerated configs).

## The model

- **Source of truth is `puente.yml`.** Each service already declares its
  `port`; add a `proxy:` block to publish it. The Caddyfile is *generated* from
  this — there is no second file to keep in sync.
- **Secrets stay out of the repo.** `proxy.token_env` (bearer) and the
  basic-auth `users` map name *environment variables*; the generated Caddyfile
  emits `{$VAR}` placeholders and puente materializes `caddy/.env` from the
  host environment at start time.

### Per-service `proxy:` block

```yaml
swarmui:
  port: 7801
  proxy:
    host: swarmui.locopuente.org   # public hostname (needs DNS -> your IP)
    auth: bearer                   # none | basic | bearer
    token_env: SWARMUI_TOKEN       # env var holding the bearer token
```

Auth policy (matches the stack convention):

| `auth`   | Use for                                   | Requires |
|----------|-------------------------------------------|----------|
| `none`   | app has its own accounts / public by design | –        |
| `basic`  | UI tool with no built-in login            | a `users` group in the `caddy:` config |
| `bearer` | API-only endpoint                         | `token_env` |

#### Rotating a bearer token

`token_env` also takes a **list**, and any one of the named tokens is accepted:

```yaml
    token_env: [OLLAMA_TOKEN, OLLAMA_TOKEN_2]
```

That is what makes rotation possible without a flag-day cutover: add the new
env var, hand the new key out, then drop the old name once nobody is using it.
Every name in the list must have a value in the environment at `puente up` —
an unset one resolves to an empty placeholder that quietly matches nothing.

### The `caddy:` service config

```yaml
caddy:
  enabled: true                     # false until you cut over (see below)
  email: you@example.org            # ACME contact
  upstream_host: 192.168.20.120     # LAN address of the backends
  users:                            # basic-auth groups: {group: {user: ENV_VAR}}
    ui:
      swarm: SWARM_BCRYPT           # bcrypt hash read from caddy/.env
```

## Secrets: `caddy/.env`

Puente writes `~/.puente/caddy/.env` on `puente up`, pulling each referenced var
from **its own process environment**. So export them before `puente up`, or
keep a persistent env file your shell sources. Required vars are discovered
automatically; any that are unset are reported and their routes will deny until
set.

Generate a bcrypt hash for a basic-auth user:

```sh
docker run --rm caddy:2 caddy hash-password --plaintext 'yourpassword'
```

Generate a bearer token:

```sh
openssl rand -hex 32
```

## Cutover from nginx-proxy-manager

Only one process can bind `:80` / `:443`. On this box that cutover is **already
done** — Caddy owns them. The steps below are for a box where NPM still does:

1. **Prep DNS** — every `proxy.host` must resolve to this host's public IP.
   (Caddy needs `:80` reachable for the HTTP-01 challenge.)
2. **Set secrets** — export the token / bcrypt env vars (see above).
3. **Stop NPM** — `cd ~/docker && docker compose stop` (or remove its
   `:80/:443` bindings). Keep its data around until Caddy is proven.
4. **Enable + start Caddy** — set `caddy.enabled: true` in `puente.yml`, then
   `puente up caddy`. Caddy will request certs on first request per host.
5. **Verify** each host:
   ```sh
   curl -sI https://swarmui.locopuente.org            # 401 (no bearer)
   curl -sI -H 'Authorization: Bearer <tok>' https://swarmui.locopuente.org
   curl -sI https://image.locopuente.org              # 401 + WWW-Authenticate: Basic
   ```
6. **Decommission NPM** once all hosts are green.

### Rollback

`puente down caddy`, then start NPM again. Caddy's certs/state live in the
`~/.puente/caddy/data` volume, so re-enabling later is instant.

## Hosts NOT managed by puente

Puente is an AI-platform orchestrator — it only fronts the AI services it runs.
Personal / unrelated infrastructure (e.g. Plex, `books.serveur.au`,
`boxes.borck.dev`) is deliberately out of scope: those hosts aren't in
`puente.yml`, so they never appear in the generated Caddyfile. Keep them on
whatever proxy you like (NPM, a separate Caddy).

The `proxy/` directory used to hold a hand-maintained standalone Caddyfile of
all 23 original hosts, used to bootstrap this migration. It was removed once
puente-caddy was serving live traffic: its only content not in the generated
config was two hosts dropped on purpose (`plex.serveur.au`, `books.serveur.au`)
and one retired service (`chatterbox.locoensayo.org`), and it had drifted far
enough to be actively misleading — its `ollama` block still named a
`127.0.0.1:11434` placeholder long after the real backend moved. Recover it
from git if ever needed: `git show ec0681b:proxy/Caddyfile`.

## Regenerating

Any `puente up` regenerates `caddy/Caddyfile` from the current `puente.yml`.
To apply changes without downtime after editing config:

```sh
docker exec puente-caddy caddy reload --config /etc/caddy/Caddyfile
```
