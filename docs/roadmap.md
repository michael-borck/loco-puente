---
title: "Roadmap"
---

LocoPuente's path from a minimal "closing the gap" PoC to faculty-scale deployment. The software stack carries forward unchanged at every stage -- only the hardware changes.

---

## Phase 1: Current PoC -- Single RTX 3090

**Hardware:** Puente -- Ryzen 5 2600 desktop with a single NVIDIA RTX 3090 24 GB
**Capacity:** Small cohort (pilot scale)
**Status:** Running today

The minimal "closing the gap" PoC. One secondhand consumer GPU running three backend services (Ollama, ComfyUI, Speaches) and four front ends: **OpenWebUI** as the general chat interface (augmented with ComfyUI, Speaches, and OpenTerminal as integrated tools so it delivers commercial-chat-equivalent functionality in one tab), plus **Vane** for deep research, **DeepTutor** for research and tutoring, and **OpenNotebook** for podcasts, quizzes, and notes. The 24 GB of VRAM absorbs concurrent LLM inference, image generation, and voice services with comfortable headroom.

| Service | VRAM |
|---|---|
| Ollama 8B Q4_K_M | ~5 GB |
| Speaches (Whisper + Kokoro) | ~0.7 GB |
| ComfyUI -- SDXL base + refiner | ~8-10 GB |
| **Full stack concurrent** | **~14-16 GB -- comfortable** |

---

## Phase 2: Apple M3 Ultra (512 GB unified memory)

**What it unlocks:**

- 50-100 concurrent users
- Multiple large models loaded simultaneously, including the larger open-weight models (70B+) that close the remaining capability gap with frontier cloud services
- No VRAM constraints for any current workload
- A machine the institution owns outright, with no ongoing costs

The M3 Ultra is the scale target. The transition from Phase 1 is not a rebuild -- it is a hardware upgrade. Ollama, ComfyUI, Speaches, and the four front-end apps all carry forward unchanged. The operational model is proven on a secondhand consumer GPU; the M3 Ultra simply removes the hardware bottleneck.

**The frontier-capability argument.** On standardised benchmarks the best open-weight models sit roughly 5-10 percentage points behind the best frontier closed models. That gap is real, but it is not decisive -- particularly for the way students actually use AI, which is *dialogic* rather than one-shot. A conversation that iterates, clarifies, and corrects closes most of that gap naturally: the student supplies context, notices errors, and asks again. Phase 2 on an M3 Ultra runs the open-weight models large enough that the residual gap is not a reason to send student data to a commercial provider.

---

## What Does Not Change

At every phase, the fundamentals remain the same:

- **All inference is local.** No data leaves the machine.
- **All APIs are OpenAI-compatible.** Any component can be swapped independently.
- **No subscriptions.** Users access everything through a browser on the local network.
- **No external dependencies.** The stack runs without internet access.

The PoC proves the model. The roadmap scales it.
