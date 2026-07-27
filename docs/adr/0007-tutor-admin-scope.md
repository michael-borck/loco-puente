# 0007 — Tutor admin withholds delete, ban and role changes

**Status:** Accepted (2026-07-27)

## Context

Once tutors had a web UI over the LibreChat user database, the obvious move was
to expose everything `deploy/librechat-users.sh` can do. The operator CLI covers
list, search, resend, force-verify, create, invite, password reset, delete, ban,
role changes and the registration gate.

The question is not what tutors are trusted with — they are colleagues — but what
a mistake, or a compromised session, can cost.

## Decision

Tutors get: **list, search, find duplicates, resend verification, force-verify,
create, invite.**

Withheld, operator-only: **delete, ban, role changes, opening/closing
registration.**

## Consequences

- Everything a tutor can reach is **additive or reversible**. A wrongly created
  account can be deleted; a wrongly verified one can be re-flagged. Nothing they
  can do destroys data.
- `delete` removes the account *and its chat history*, with no undo — the single
  most damaging action available, and the one most easily triggered by a
  misclick on the wrong row.
- `role` is privilege escalation: a tutor who can grant `ADMIN` can grant it to
  anyone, including a student, and that student can then grant it onward. The
  boundary would stop meaning anything.
- Registration open/close is a policy decision about the course, not an
  account-level fix, and it requires a container recreate anyway.
- **Cost:** a genuine delete request has to come through the operator. In
  practice this is rare — the common cases are all unblocking, which tutors now
  handle themselves. Duplicate detection is exposed *without* delete precisely so
  a tutor can identify the problem and hand over a specific, checked list.

## Alternatives rejected

**Expose everything, rely on the audit log.** An audit log is detective, not
preventive — it tells you who destroyed the history, after it is gone. Fine for
reversible actions, insufficient for irreversible ones.

**Add a confirmation dialog to delete.** Confirmation prompts are trained away by
repetition; the second time someone sees one they click through it. It does not
change what a compromised session can do.

**Soft-delete instead (disable, keep data).** Genuinely better than hard delete
and worth revisiting if delete requests become frequent. Rejected for now only
because LibreChat has no soft-delete concept, so it would mean inventing an
account state the app itself does not understand.
