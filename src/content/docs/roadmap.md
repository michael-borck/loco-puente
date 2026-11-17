---
title: "Roadmap"
---

LocoPuente's path from a minimal "closing the gap" PoC to faculty-scale deployment. Two things scale it: **hardware** (the phases below) and **deployment shape** (three tiers). The architecture carries forward unchanged at every stage.

---

## Phase 1: Current PoC: Single RTX 3090

**Hardware:** Puente, a Ryzen 5 2600 desktop with a single NVIDIA RTX 3090 24 GB
**Capacity:** Small cohort (pilot scale)
**Status:** Running today

The minimal "closing the gap" PoC. One secondhand consumer GPU running three backend services (Ollama, ComfyUI, Speaches) and four front ends: **OpenWebUI** as the general chat interface (augmented with ComfyUI, Speaches, and OpenTerminal as integrated tools so it delivers commercial-chat-equivalent functionality in one tab), plus **Vane** for deep research, **DeepTutor** for research and tutoring, and **OpenNotebook** for podcasts, quizzes, and notes. The 24 GB of VRAM absorbs concurrent LLM inference, image generation, and voice services with comfortable headroom.

| Service | VRAM |
|---|---|
| Ollama 8B Q4_K_M | ~5 GB |
| Speaches (Whisper + Kokoro) | ~0.7 GB |
| ComfyUI: SDXL base + refiner | ~8-10 GB |
| **Full stack concurrent** | **~14-16 GB: comfortable** |

---

## Phase 2: Apple M5 Ultra (256-512 GB unified memory)

**What it unlocks:**

- 50-100 concurrent users
- Multiple large models loaded simultaneously, including the larger open-weight models (70B+) that close the remaining capability gap with frontier cloud services
- No VRAM constraints for any current workload — every model resident at once, so load-and-release stops being part of the design on this box
- A machine the institution owns outright, with no ongoing costs

The M5 Ultra is the scale target. The transition from Phase 1 is a hardware upgrade, not a rebuild. The front ends carry forward unchanged, and the institutional layer — single sign-on, fair-share queueing, snapshots, per-semester pinned models — is exactly what the Campus tier adds (below). The operational model is proven on a secondhand consumer GPU; the M5 Ultra simply removes the hardware bottleneck.

**The frontier-capability argument.** On standardised benchmarks the best open-weight models sit roughly 5-10 percentage points behind the best frontier closed models. That gap is real, but it is not decisive, particularly because students use AI dialogically, not in one-shot prompts. A conversation that iterates, clarifies, and corrects closes most of that gap naturally: the student supplies context, notices errors, and asks again. Phase 2 on an M3 Ultra runs the open-weight models large enough that the residual gap is not a reason to send student data to a commercial provider.

---

## Three Deployment Tiers

The same architecture deploys at three sizes. `puente init` proposes the tier from your hardware; `puente.yml` records it; any service's install method follows its declaration.

| Tier | Shape | For whom |
|---|---|---|
| **Suitcase** | No Docker. The engine runs native, Open WebUI installs via pip, Caddy is a single binary. Chat and search: the opinionated minimum | One operator, one classroom, modest hardware |
| **Stack** | The full container stack: every capability, GPU pinning, the service catalog, the portal | The PoC, the unit pilot, an institution's first server |
| **Campus** | The Stack plus single sign-on (OIDC), fair-share queueing on shared GPUs, whole-stack snapshots, and a documented upgrade path | The institutional product; what a large deployment runs |

How this maps onto the family ladder: a student's own laptop runs **mochila** (rung 1); a classroom box can run **Suitcase** without Docker; **Stack** is the Phase 1 PoC; **Campus** is where the M5 Ultra deployment lands. The tiers are deployment shapes of one architecture, not three products. Recorded as [ADR0014](https://github.com/michael-borck/loco-puente/blob/main/docs/adr/0014-deployment-tiers-native-quick-start.md).

---

## What Does Not Change

At every phase, the fundamentals remain the same:

- **All inference is local.** No data leaves the machine.
- **All APIs are OpenAI-compatible.** Any component can be swapped independently.
- **No subscriptions.** Users access everything through a browser on the local network.
- **No external dependencies.** The stack runs without internet access.

The PoC proves the model. The roadmap scales it.
