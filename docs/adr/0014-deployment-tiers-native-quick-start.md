# 0014: Three deployment tiers; the quick-start tier runs without Docker

**Status:** Accepted (2026-11-17).

## Context

The handover's design principle (2026-10-10): **Docker is a means, not the
goal. The aim is the easiest possible setup, install and maintenance.** The
open implication was recorded and deliberately left undecided: the default trio
could run entirely without Docker (engine native, Open WebUI via pip, Caddy as
a single binary). A pure-Docker default would have foreclosed that by inertia.

Three facts now decide it:

- `nvidia-container-toolkit` is the hardest prerequisite `puente doctor`
  checks. For a non-expert with one small card, it is the difference between an
  afternoon and a dead end.
- The mission audience (a DIYer on consumer NVIDIA, often a single 8 to 12 GB
  card) is better served by a native quick start; an institution wanting every
  capability is not.
- The M5 Ultra deployment is macOS: native regardless, so the container stack
  was never going to be the only shape anyway.

## Decision

Three named tiers. `puente init` proposes the tier; `puente.yml` records it;
every service already declares `install_method: docker | native | external`.

| Tier | Shape | For whom |
| --- | --- | --- |
| **1. Suitcase** | no Docker: engine native (per ADR0013), Open WebUI via pip, Caddy binary. Chat and search only; the opinionated minimum | one operator, one classroom, modest hardware |
| **2. Stack** | today's compose stack: all capabilities, GPU pinning, catalog, portal | the PoC, the unit pilot, an institution's first server |
| **3. Campus** | tier 2 plus OIDC forward-auth at Caddy, fair-share queueing, whole-stack snapshots, a documented upgrade path | the institutional product; what the M5 deployment runs |

Relationship to the family ladder: tier 1 is mochila-shaped (the laptop kit,
scaled to a classroom box); tier 3 is Puente's institutional end-state
(Decision L). The tiers are deployment shapes of one architecture, not three
products.

## Consequences

- `puente doctor` gains a tier report: what the host qualifies for, and what
  each tier would need.
- `compose.py` remains the tier 2 engine; tier 1 generates systemd units and a
  Caddyfile instead of a compose file. No service class changes: a service's
  `install_method` was always per-service, and this uses it.
- Tier 3 is configuration and wiring of an upstream harness (OIDC at Caddy,
  queueing policy, snapshot scripts), per Decision H's rule that the harness
  itself is not Puente's to build.
- The tier is visible in `puente capabilities` output, so the honest hardware
  verdict and the honest deployment verdict read as one answer.

## Rejected

- **Container-only default.** Forecloses the easiest setup for the exact
  audience the mission names; rejected on the design principle, not on
  Docker's merits.
- **Building a custom harness for tier 3.** Decision H's verdict stands; wire
  Open WebUI (or its successor) with MCP tools and OIDC. Reopen "our own
  harness" only after a real attempt proves no upstream harness can carry the
  surface.
