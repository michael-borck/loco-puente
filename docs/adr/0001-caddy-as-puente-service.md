# 0001 — Caddy as a puente service, replacing nginx-proxy-manager

**Status:** Accepted (2026-07-08, recorded retrospectively)

## Context

Every public hostname was routed through nginx-proxy-manager, configured through
its web UI. That configuration lived in NPM's own database — **not in git** — so
the deployed routing could not be reviewed, diffed or rebuilt from the repo.

Worse, hand-edited `.conf` files silently reverted: the database is the source of
truth, and the UI regenerates configs from it whenever it feels like it. A 23-host
audit found drift that nobody had introduced deliberately.

## Decision

Run Caddy as an optional puente service. When enabled it owns `:80`/`:443` and
fronts every service declaring a `proxy:` block, terminating TLS via automatic
Let's Encrypt and enforcing a per-service auth policy.

**The Caddyfile is generated from `puente.yml`.** There is no second file to keep
in sync.

Auth policy, by service type:

- `none` — the app has its own accounts, or is public by design
- `basic` — a UI tool with no built-in login
- `bearer` — an API-only endpoint gated by a token

## Consequences

- Routing is reviewable in git and rebuildable on a new host from `puente.yml`
  alone.
- Secrets stay out of the repo: `token_env` and the basic-auth `users` map name
  *environment variables*, and the generated Caddyfile emits `{$VAR}`
  placeholders (see ADR 0002).
- Certificates are automatic, but require DNS to resolve **before** first start,
  and Cloudflare records must be DNS-only — a proxied record breaks the ACME
  challenge.
- Multiple bearer tokens per host are supported specifically to allow rotation
  without a flag-day cutover: add the new token, migrate clients, drop the old.
- Puente stays optional-by-default here: `caddy.enabled: false` means bring your
  own proxy and puente stays out of the way.
- **Do not hand-edit `~/.puente/caddy/Caddyfile`** — it is regenerated at every
  `puente up`. Same class of trap as NPM's reverting `.conf` files, which is what
  this decision was meant to eliminate.

## Alternatives rejected

**Keep nginx-proxy-manager.** Familiar and already working, but its configuration
is unreviewable and drifts. Rebuilding the routing on a new machine would mean
clicking through a UI 23 times.

**Traefik.** Capable and container-native, but its label-driven configuration
would spread routing across every service definition, and puente already has a
central config file that is a better home for it. Caddy's automatic TLS also
removed a whole category of certificate chores.
