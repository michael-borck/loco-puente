# 0004 — Open self-registration, gated by domain allowlist + email verification

**Status:** Accepted (2026-07-22, recorded retrospectively)

## Context

~40 students per cohort need LibreChat accounts. Creating them by hand from
enrolment data is slow, goes stale as students add and drop, and produces
password-distribution problems in a lecture theatre.

## Decision

Leave self-registration open, and gate it with two independent controls:

1. **`allowedDomains`** in `librechat.yaml` — Curtin addresses only. Enforced in
   `registerUser`, returning 403 before any account is created.
2. **Mandatory email verification** — proves the address is real and reachable.

The **per-IP rate limiter is effectively disabled** (`REGISTER_MAX=10000`), on
purpose. It is not a useful control here and actively harmful: a lab NATs to one
campus IP, so a whole class shares one bucket.

## Consequences

- Students self-serve; the operator does nothing in the common case.
- Verification also gates self-service password reset, which tutors cannot
  perform on the operator's behalf.
- It prevents a whole class of duplicate accounts: without it, a student who
  mistypes their address gets a *working* account on the wrong email, then
  registers again next lab when the correct address reports "user not found".
- **Never set a limiter to 0** — in `express-rate-limit`, 0 blocks everything.
- Each 429 calls `logViolation`, feeding the ban layer, so a tight limit can
  escalate beyond its own window.
- The domain allowlist is exact-suffix. A wrong spelling matches nothing and is
  invisible until someone tries: `postgraduate.curtin.edu.au` was listed for
  weeks while the real domain is `postgrad.curtin.edu.au`, silently rejecting
  every postgraduate student.
- **A rejected domain surfaces to the student as "You have tried to sign up too
  many times"** — the same string as the rate limiter. Always confirm against
  `docker logs puente-librechat | grep 'Registration not allowed'` before
  concluding it is rate limiting.
- `create`/`invite` (CLI and tutor UI) **bypass both gates** by design, which is
  what makes them the tool for closing registration later. They enforce their own
  domain allowlist independently.

## Alternatives rejected

**Manual account creation from enrolment.** Accurate but slow, stale within days,
and requires distributing passwords out of band. Still the plan *after* the
add/drop period settles, at which point registration closes and `invite` takes
over.

**Rely on the per-IP rate limiter as the abuse control.** It does not distinguish
a class from an attacker — NAT makes them identical. It punished exactly the
users it was meant to serve.
