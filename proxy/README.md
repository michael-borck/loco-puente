# `proxy/` — standalone Caddy reference

This directory holds a **complete, hand-written Caddyfile** covering all 23
hosts that were originally configured in nginx-proxy-manager — including hosts
puente does not manage (Plex, Calibre-Web, `boxes.borck.dev`).

It exists as a **bootstrap / reference**. Two ways to use it:

- **Standalone:** `cp .env.example .env`, fill in secrets, `docker compose up -d`.
  Runs Caddy independently of puente.
- **Reference:** copy the blocks for non-puente hosts into your setup when
  migrating, since the puente-generated Caddyfile only covers puente services.

## Prefer the puente-native path

For services puente runs, don't maintain routes here by hand — declare a
`proxy:` block on the service in `puente.yml` and let puente generate the
Caddyfile. That keeps the proxy config in one source of truth with no drift.
See [`../docs/caddy-migration.md`](../docs/caddy-migration.md).

Use this standalone folder only for hosts outside puente's world, or to run
Caddy without adopting the puente service model.

## Secrets

`.env` is gitignored. `.env.example` documents the required vars (bcrypt hashes
for basic-auth, bearer tokens). Generate:

```sh
docker run --rm caddy:2 caddy hash-password --plaintext 'pw'   # bcrypt
openssl rand -hex 32                                           # token
```
