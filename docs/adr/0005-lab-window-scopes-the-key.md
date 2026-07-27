# 0005 — The lab window scopes the Anthropic key, not the app

**Status:** Accepted (2026-07-23). Supersedes the original stop-the-container
approach.

## Context

Claude models in LibreChat cost real money per token, and the service is exposed
to a class of ~40 students. The exposure needed bounding to scheduled lab hours.

The first implementation had `deploy/chat-window.sh` **stop the container**
outside those hours. That protected the key, but also took registration and the
free local Ollama models offline — so the entire class could only sign up during
the first minutes of a lab, from one NATed campus IP.

That directly caused the registration failure: LibreChat rate-limits signup per
client IP, and a lab behind NAT shares a single bucket. At the stock limit of 5
per 60 minutes, **8 of 40 students registered**; the rest saw "Too many accounts
created". The scheduling mechanism created the incident it appeared to be
unrelated to.

## Decision

LibreChat runs **24/7**. Only the Anthropic endpoint is scheduled: `open`
recreates the container with `ANTHROPIC_API_KEY` set, `close` recreates it empty.
LibreChat drops the endpoint when the value is empty.

Students can register and use local Ollama models at any hour; the Claude models
appear in the picker at lab open and vanish at close.

## Consequences

- Registration is available all week, so signups spread out and never hit a
  shared per-IP bucket in one burst.
- Swapping the key is a **container recreate, not a restart** — environment is
  baked in at creation (see ADR 0002). Cost: ~10s downtime at each boundary, and
  in-flight chats drop. History lives in Mongo, in a separate always-up
  container, so nothing is lost.
- The nightly 23:00 `close` became a safety net guaranteeing the key is out if an
  `open` fired without its `close`.
- Verification requires a logged-in call to `/api/endpoints`; `/api/models`
  returns the static catalogue and proves nothing.
- **Anything that recreates LibreChat re-bakes the key from the ambient
  environment.** A `docker compose up` that pulls LibreChat in via `depends_on`
  will blank it if the shell has no key exported. Use `--no-deps` when touching a
  single service.
- The schedule bounds the *exposure window*; it does not bound *damage* within
  one. A spend cap on the key in the Anthropic Console is the durable protection
  and is still outstanding.

## Alternatives rejected

**Keep stopping the container.** Protects the key equally well, but takes
registration and the free local models down with it — the cause of the incident
above.

**Leave the key in place and rely on LibreChat's own permissions.** No per-user
spend control exists at the granularity needed, and the blast radius of a leaked
or shared account is unbounded.
