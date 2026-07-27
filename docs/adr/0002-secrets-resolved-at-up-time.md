# 0002 — Secrets resolved at `puente up`, never `${VAR}` in compose

**Status:** Accepted (2026-07-24, recorded retrospectively)

## Context

Services need API keys and passwords: the Anthropic key, the Resend SMTP key,
bearer tokens and bcrypt hashes for Caddy. The natural-looking approach is to
write `${ANTHROPIC_API_KEY}` in the compose file and export the value from
`~/.zshrc`.

That works interactively and **fails silently everywhere else.** A `${VAR}` in a
compose file resolves from the environment of the process running Compose. Under
cron or systemd that environment is nearly empty, so the variable expands to an
empty string and the container starts *successfully* with no credential.

This cost an evening on LibreChat SMTP: mail failed with unauthenticated 530s
from Resend, while the config looked correct in the repo and worked by hand.

## Decision

Puente resolves secret values **at `puente up`** — from key files under
`~/.puente/` or the host environment — and writes them into `env_file`s that
Compose reads directly. The generated compose file contains no `${VAR}`
placeholders for secrets.

Keys come from **files**, not the ambient environment, so behaviour is identical
whether started by hand, cron or systemd.

## Consequences

- A missing secret fails loudly at `up` time rather than producing a running
  service with an empty credential.
- `deploy/chat-window.sh open` reads `~/.puente/anthropic.key` and **aborts** if
  it is missing or empty, rather than quietly opening a lab with no Claude models.
- Bcrypt hashes in `caddy/.env` need every `$` doubled to `$$`, because Compose
  interpolates `env_file` values too. Puente escapes on write; values carried
  over from an existing file are not re-escaped, or the `$` would double on every
  run.
- **A new env var requires `--force-recreate`.** Environment is baked in at
  container creation; a reload or restart will not see it. This surprises people
  repeatedly — it is the same mechanism behind ADR 0005.
- Secrets are not in git and must be recreated by hand on a new host. See
  `docs/host-setup.md` §3.

## Alternatives rejected

**Export from `~/.zshrc`.** The failure mode above. Worse, it made a paid
Anthropic key ambiently available to *any* interactive `puente up`, which
silently re-enabled Claude outside lab hours and leaked spend. The export is now
commented out.

**Docker secrets / an external secret manager.** Correct for a multi-host or
multi-operator deployment, and disproportionate for a single box with one
operator. Revisit if either assumption changes.
