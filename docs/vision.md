# What Puente is for

*Written 2026-10-10, after a session that spent a long time arguing with
ourselves about which direction to take. This records the answer.*

## The one sentence

**A customisable local AI stack that detects your hardware, offers an opinionated
configuration that fits it, works out of the box — and exposes every capability
as an API so you can write your own thing on top.**

## Why this was hard to see

The project started as a proof of concept on one specific box: a 3090 and a 4060
Ti, a hand-tuned `puente.yml`, and a set of operational knowledge that lived in
shell scripts and one person's head. Every question about "should we add service
X" got answered by "would it fit on this box", which made the project look like a
pile of workarounds rather than a tool.

The turn was realising that **the box is the rarest case, not the typical one**.
The audience is a DIYer on consumer NVIDIA: Linux, frequently a *single* card,
often 8 or 12 GB of VRAM. That reframes everything:

- An 8 GB card cannot hold a 30B model — so MoE expert offload goes from a
  curiosity to the thing that makes the stack useful (ADR0010).
- A single card cannot hold chat, image, voice and song at once — so load and
  release is the **design**, not a compromise. The PoC box has 40 GB and holds
  two models; a real user has 12 GB and holds one.

Everything that looked like a limitation is actually the shape of the product.

## The four commitments

### 1. Detect, then offer — not detect and impose

`puente doctor` inspects the host. `puente init` proposes a configuration that
fits. But the proposal is a *proposal*: the output is a committable `puente.yml`
that the operator then owns and edits. Nothing is hidden, nothing is magic.

The test: could someone read `puente.yml` and understand exactly what will run,
and change any part of it? If not, the feature is wrong.

### 2. Opinionated defaults, genuinely opinionated

Not "here are 27 services, choose some." A default that runs on this hardware:
chat that answers, images that generate, voice that speaks, code that compiles.
A student or a hobbyist should get something working without reading docs, and
without a frontier-model subscription.

The defaults are opinionated *because* they were chosen against real hardware.
That is also what makes them defensible — not taste, but a measurement.

### 3. Capabilities are APIs. The UI is a client.

This is the architectural commitment that matters most, and it is the one the
PoC has been drifting from.

Chat, image, voice and song are **services with APIs**. The launcher portal, and
any WebUI we build, is a *client* of those APIs — not the thing that owns them.

Why: the mission is student equity, and the thing that creates equity is not
access to a chat box. It is being able to *write your own code* against a real
AI stack. A student who has used the portal and then read its API can build
something of their own. A student given only a chat UI cannot.

Consequences: every capability is reachable over HTTP with a documented contract;
auth is the proxy's job (ADR0001, ADR0002); and the admin surface is a separate
concern with its own privilege split (ADR0006).

### 4. Both backends, user's choice

Ollama is the default because it is easy to operate. llama.cpp is there because
on a small card it is the difference between a 7B model and a 30B one (ADR0010).
Neither is being retired. The choice belongs to whoever installs it.

## What this rules out

- **Feature accumulation.** A service that does not fit the default profile on
  typical hardware does not go in the opinionated set. It can exist as opt-in.
- **Cloud.** "Private by default" is the point. A capability that only works by
  calling an API is not a local AI stack.
- **Requiring the newest hardware.** The 2026-10-10 finding: dual-channel
  DDR4-3200 measures within a few percent of DDR5-6000, so anyone who has
  chased a memory upgrade on our advice has wasted their money. DDR3 *is* a real
  cliff (~1.7× slower) and worth detecting — but the answer is a smaller model,
  not a new motherboard.

## Open questions

- **Agents.** OpenClaw (MIT, ~250k stars) connects local models to files, shell
  and browsers. Do we integrate, or only ensure our APIs are good enough that an
  agent can drive them?
- **System 1 / System 2.** A small fast model for routine turns and a large one
  on demand, rather than one model doing everything slowly. This is really the
  same problem as model residency, solved at the routing layer instead of the
  memory layer. Worth deciding deliberately.
- **The launcher.** Is the portal a real UI, or a signpost? Committing to a web
  app is a maintenance cost; a good API plus a clear list of endpoints is honest
  and cheap.