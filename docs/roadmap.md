---
title: "Roadmap"
---

LocoPuente's path from proof of concept to faculty-scale deployment. The software stack carries forward unchanged at every stage -- only the hardware changes.

---

## Phase 1: Current PoC (Dual GPU)

**Hardware:** RTX 3060 12 GB (Pulpo) + RTX 2060 Super 8 GB (Puente)
**Capacity:** 2-5 concurrent users
**Status:** Running today

The full stack is operational. Voice + LLM inference run concurrently on separate cards. Image generation shares GPU 0 with the primary LLM (not concurrent). All services are accessible on the local network.

---

## Phase 2: RTX 4060 Ti 16 GB

**What it unlocks:**

- FLUX.1 Dev GGUF Q8 for near-full-quality image generation
- Truly concurrent LLM + image generation on a single card (16 GB headroom)
- Larger quantised models (8B at Q8_0, 13B at Q4_K_M)

The 4060 Ti replaces the RTX 3060 on Pulpo, eliminating the current constraint where LLM and image generation cannot run simultaneously.

---

## Phase 3: RTX 3090 24 GB

**What it unlocks:**

- Full stack on a single card
- FLUX.1 Dev FP16 at full quality
- 30B+ models for higher-quality inference
- Voice + LLM + image generation all concurrent with comfortable headroom

| Service | VRAM |
|---|---|
| Ollama 8B Q4_K_M | ~5 GB |
| Speaches (Whisper + Kokoro) | ~0.7 GB |
| SDXL base + refiner | ~8-10 GB |
| **Full stack concurrent** | **~16 GB -- comfortable** |

The RTX 3090 consolidates the dual-GPU arrangement into a single card. Pulpo and Puente are freed for dedicated LocoBench benchmarking roles.

---

## Phase 4: Apple M3 Ultra (512 GB)

**What it unlocks:**

- 50-100 concurrent users
- Multiple large models loaded simultaneously
- No VRAM constraints for any current workload
- A machine the institution owns outright, with no ongoing costs

The M3 Ultra is the scale target. The transition from PoC is not a rebuild -- it is a hardware upgrade. The Docker Compose stack, the Ollama instances, the service integrations all carry forward unchanged. The operational model is proven on consumer GPUs; the M3 Ultra simply removes the hardware bottleneck.

---

## What Does Not Change

At every phase, the fundamentals remain the same:

- **All inference is local.** No data leaves the machine.
- **All APIs are OpenAI-compatible.** Any component can be swapped independently.
- **No subscriptions.** Users access everything through a browser on the local network.
- **No external dependencies.** The stack runs without internet access.

The PoC proves the model. The roadmap scales it.
