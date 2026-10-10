# 0010 — llama.cpp as the LLM backend, for small-card hardware

**Status:** Accepted (2026-10-10) — both backends supported; llama.cpp is the
one that scales down

## Context

Puente's audience is a **DIYer with consumer NVIDIA hardware** — a Linux box, often
a single GPU, frequently 8 or 12 GB of VRAM. That is the target, not a lab with
spare cards. Two machines are a luxury; one modest card is the normal case.

That reframing matters because the feature this ADR is about is **much less
important on a big card and transformative on a small one.**

A MoE model is defined by two numbers: total parameters, and *active* parameters
per token. Qwen3-30B-A3B is 30B of weights but activates ~3B per token. On a 24 GB
card, 30B at Q4 is ~18 GB and simply fits — you do not need offloading. On an **8 GB
card it does not fit at all**, and without expert offloading the choice is between
a 7B model that runs fast and a 30B model that does not run.

`--cpu-moe` resolves that: routed experts live in system RAM, attention and KV
cache stay in VRAM, and only the few percent of experts a token actually touches
are read from RAM. It turns "you cannot afford a 30B model" into "you can, more
slowly". For the 8 GB user that is the difference between the stack being useful
and the stack being a toy.

**Neither Ollama, vLLM nor SGLang offers this.** vLLM and SGLang are architected
around tensor parallelism and have no expert-aware CPU offload. Ollama does not
expose the flag. So the proposal to "move to vLLM" and the desire for MoE expert
offload are mutually exclusive, and that — not throughput, not concurrency — is
what decides the backend.

## The PoC box is the wrong place to evaluate this

The development box has an RTX 3090 (24 GB) **and** an RTX 4060 Ti (16 GB) — 40 GB
of VRAM. On that hardware expert offloading is close to pointless, because a good
model fits in VRAM regardless. Its most recent load/unload collisions came from
GPU 1 holding ~13 GB between Voicebox and Ollama's classroom preload.

So:

- **This box cannot validate the feature.** It can only prove the backend runs.
- **The V100 32 GB box cannot validate it either** — also a large card, and also
  a poor demonstration target.
- What this box *can* do is measure the **curve**: tokens/sec as a function of
  offload depth (`-ncmoe N`), on a real MoE model. That curve is the deliverable,
  because it transfers: a user with 8 GB reads off their own point on it.

**llama.cpp works on this box** (verified: `Llama-3.2-1B-Instruct-Q4_K_M` via
`ghcr.io/ggml-org/llama.cpp:server-cuda`, OpenAI-compatible chat completion, 419
tok/s decode, 1659 MiB VRAM). **The offloading behaviour is still unmeasured**, and
that measurement should be the next thing done.

## Decision

**llama.cpp is supported as an LLM backend alongside Ollama, and is the one to
reach for on a single small card.** Both remain first-class.

- `cpu_moe` is a **dial, not a switch**. Offload only as many layers as needed to
  fit; a model that nearly fits costs almost nothing. The penalty scales with
  offload depth, not with "MoE vs dense".
- `n_gpu_layers` is the coarse dial for reserving VRAM for other services.
- Both are asserted in tests, because the failure is silent: `-ncmoe` on a dense
  model is accepted and does nothing, and an over-large `-ngl` is clamped rather
  than refused.
- One `llama-server` serves one model, so several models means several instances.
  The config mirrors Ollama's shape deliberately so the two stay swappable.
- Off by default. Enabling both backends at once puts two servers on one card.

Ollama is **not** retired. It is easier to operate, needs no GGUF preparation,
and remains the right default on a box with VRAM to spare. The migration is a
choice, and `docs/llama-cpp-api.md` should help someone make it rather than
push them into it.

## A finding worth recording: DDR4 is not the problem

The obvious objection to offloading experts to system RAM is that consumer boards
have slow memory. Measured and compared against the published DDR5-6000 baseline:

| Memory (dual-channel) | Theoretical | Realistic |
| --- | --- | --- |
| DDR5-6000 | 96 GB/s | ~42 GB/s *(published MoE benchmark)* |
| **DDR4-3200** | 51 GB/s | **~41 GB/s** |
| DDR4-2666 | 43 GB/s | ~34 GB/s |

**Dual-channel DDR4-3200 lands within a few percent of the DDR5-6000 figure.** An
earlier draft of this ADR claimed consumer DDR4 was "roughly half" the speed of
DDR5; that was wrong, and it would have sent people chasing a motherboard upgrade
for no benefit. DDR5's real advantages are density and capacity, not doubled
dual-channel bandwidth. Recorded here so the claim is not repeated.

## Consequences

- `puente doctor` validates llama.cpp's per-instance GPU pins — they live inside
  `instances:`, not on the service, so the generic `requires_gpu` scan misses them.
- The model directory must be configurable to an existing GGUF library. This box
  has 211 GB of GGUFs at `/mnt/data/models/loco-llm/` that Ollama cannot touch —
  for an installer who already has a model library, this is the whole value.
- Documentation should describe capability per hardware profile, not imply that a
  particular rig is short of anything.

## Rejected

- **vLLM.** The standard choice for serving many concurrent users, and probably
  right if the goal ever shifts to 50 simultaneous students. But no MoE expert
  offload, which is this decision's entire point. Revisit on that trigger.
- **Retiring Ollama outright.** Doubles the surface for a tool whose problem is
  already too many knobs. Support both; document when to prefer which.
- **Apple Silicon as the answer to VRAM pressure.** Abandoned. ComfyUI on MPS
  cannot run FP8 models, `channels_last` errors, image generation runs at 20–90
  s/image. Unified memory solves the LLM half and not the half that made this
  project distinctive.