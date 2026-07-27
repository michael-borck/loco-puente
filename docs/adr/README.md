# Architecture Decision Records

Short records of decisions that were **not obvious**, where the reasoning would
otherwise be lost in a commit message and re-litigated a year later.

## What belongs here

A decision earns an ADR if it meets at least one of:

- **A plausible alternative was rejected**, and someone could reasonably propose
  it again ("why isn't the runner a container?", "why not just use SSH?").
- **The reasoning is invisible from the code.** A `127.0.0.1` bind looks like an
  oversight until you know it is load-bearing for the security model.
- **It was expensive to learn.** A decision paid for with an evening of debugging
  should not have to be paid for twice.

What does *not* belong: routine implementation choices, anything the code already
states plainly, and one-off bug fixes — those live in commit messages, which git
already indexes well.

## Format

One file per decision, `NNNN-short-title.md`, numbered in the order decided.
Keep them short — context, decision, consequences, and what was rejected.

Status is one of **Accepted**, **Superseded by NNNN**, or **Reversed**.
**Never delete or rewrite a superseded ADR**: the record of a decision that was
later reversed is more useful than its absence, because it stops the same
reversal being proposed a third time.

## Index

| # | Decision | Status |
| --- | --- | --- |
| [0001](0001-caddy-as-puente-service.md) | Caddy as a puente service, replacing nginx-proxy-manager | Accepted |
| [0002](0002-secrets-resolved-at-up-time.md) | Secrets resolved at `puente up`, never `${VAR}` in compose | Accepted |
| [0003](0003-scope-excludes-personal-infra.md) | Puente's scope excludes personal infrastructure | Accepted |
| [0004](0004-librechat-open-registration.md) | Open self-registration gated by domain + email verification | Accepted |
| [0005](0005-lab-window-scopes-the-key.md) | The lab window scopes the Anthropic key, not the app | Supersedes an earlier stop-the-container approach |
| [0006](0006-tutor-admin-privilege-split.md) | Tutor admin: web app in a container, privileged runner on the host | Accepted |
| [0007](0007-tutor-admin-scope.md) | Tutor admin withholds delete, ban and role changes | Accepted |
