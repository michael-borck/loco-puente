# 0003 — Puente's scope excludes personal infrastructure

**Status:** Accepted (recorded retrospectively)

## Context

Puente is a **portable AI orchestrator for low-end hardware** — the pitch is that
it charges a time tax rather than a token tax, and that someone else can run it
on their own box.

The machine it happens to run on here also hosts personal services: Plex, an
ebook library, and other unrelated boxes. Puente already manages containers,
ports, a reverse proxy, TLS and secrets — everything those services need. Folding
them in is a small, tempting step each time.

## Decision

Puente manages **AI services only**. Personal infrastructure stays outside it,
even when it runs on the same host and would benefit from the same machinery.

The test is not "could puente run this?" but **"would this belong in someone
else's puente install?"**

## Consequences

- The service registry stays legible: every entry is something an AI stack user
  would plausibly want.
- Puente's command surface does not change shape based on what is enabled — no
  `puente plex` in a config that has no Plex.
- Service-specific operational tooling that fails the test lives in `deploy/`
  instead. `chat-window.sh` (LibreChat lab windows) and `librechat-users.sh`
  (account admin) are both there: they shell into one named container and would
  be dead weight in any deployment without LibreChat.
- **Puente can still *use* a service it does not manage** — `install_method:
  external` points it at something already installed. Native Ollama is the
  reference case: puente wires it into LibreChat and Caddy without owning its
  lifecycle.
- Cost: some genuinely useful glue gets written twice, or lives as a shell script
  rather than a subcommand. Accepted — the alternative is a tool nobody else can
  adopt.

## Alternatives rejected

**Manage everything on the box.** Immediately convenient and the reason the rule
exists: without it, puente becomes this machine's config rather than a portable
tool, and the AI-stack story is buried under unrelated services.

**A plugin system for local additions.** Solves it in principle, but the
`deploy/` directory already handles these cases at a fraction of the complexity.
Revisit only if third-party services start needing lifecycle management.
