# 0006 — Tutor admin: web app in a container, privileged runner on the host

**Status:** Accepted (2026-07-27)

## Context

Tutors need to unblock students in LibreChat — resend a verification link,
force-verify when mail fails, create an account — without a shell account on the
machine that also runs Ollama, ComfyUI, SwarmUI and the Anthropic key file.

Two of those actions (`create`, `invite`) are npm scripts *inside* the LibreChat
container. They hash passwords and mint invite tokens using LibreChat's own
internals, so reimplementing them would drift the moment upstream changed either
format. Reaching them means `docker exec`, which means the Docker socket.

**A writable Docker socket is root on the host.** Anything holding it can start a
privileged container and own the machine.

## Decision

Split the tool in half:

- **Web app** — a container, puente-managed, reachable from the internet through
  Caddy. Talks to Mongo and LibreChat's HTTP API. **No Docker socket.**
- **Runner** — a host-side systemd service running as the operator, with the
  socket. **No network listener at all.**

They communicate through a spool directory: the app writes a JSON request, the
runner validates it independently and executes the npm script.

## Consequences

- A compromise of the internet-facing app cannot escalate to the host. The worst
  it can do is queue account creations it could already perform legitimately
  through its own UI.
- The runner cannot be attacked directly — it has no listener, only a directory.
- Validation is duplicated (domain allowlist in both halves) on purpose: the
  runner treats anything in the spool as untrusted input regardless of origin.
- **Cost:** `create` and `invite` need the runner installed and running. If it is
  stopped they time out with an explicit message. Everything else — list, search,
  duplicates, resend, force-verify — keeps working, because those go straight to
  Mongo or LibreChat's HTTP API.
- Spool files hold plaintext passwords in flight. Mode 0640, owned by the runner
  user, deleted immediately after execution.

## Alternatives rejected

**Mount the Docker socket into the web app.** Simplest by far, and the reason to
reject it is exactly the one above: it converts any bug in an internet-facing web
service into full host compromise. Not worth a convenience feature.

**Run the runner in a container with the socket mounted.** No real gain — a
container with a writable socket is not meaningfully contained, and it would then
sit on the same network as the exposed app. Strictly worse than a host process.

**Reimplement password hashing and invite tokens in the app.** Removes the socket
requirement entirely, but couples us to LibreChat's internal formats with no
compile-time signal when they change. The failure mode is silent and lands on
students.

**Give tutors SSH instead.** Cheapest option, but grants shell on a box holding
every service and the Anthropic key. Scoping SSH down to "only LibreChat user
admin" (forced commands, restricted shell) is more work than this design, and one
tutor is not comfortable at a terminal regardless.
