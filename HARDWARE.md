# Hardware Selection Guide

This guide covers how to choose hardware for running local AI inference. It focuses on durable frameworks — the math that governs memory requirements, the architectural tradeoffs, and the principles that hold regardless of which model generation you are deploying.

For current model-to-VRAM benchmark results on specific hardware, run [LocoBench](https://github.com/michael-borck/loco-bench).

---

## The One Rule That Governs Everything

**VRAM is the bottleneck.** CPU clock speed is largely irrelevant for inference. What matters is whether your entire model fits in fast memory (VRAM or unified RAM) — if it does not, the system either fails or becomes so slow as to be unusable.

The math is simple and stable across generations:

> **2 bytes per parameter at 16-bit (full) precision**

| Model size | 16-bit VRAM | 8-bit VRAM | 4-bit VRAM |
|-----------|-------------|------------|------------|
| 7B | 14 GB | 7 GB | ~4 GB |
| 13B | 26 GB | 13 GB | ~7 GB |
| 30B | 60 GB | 30 GB | ~16 GB |
| 70B | 140 GB | 70 GB | ~35 GB |

But the model weights are only part of the picture. You also need headroom for the **KV Cache** — the pre-calculated vectors that store conversation context. If VRAM is exhausted by the cache, the context window collapses, the system slows dramatically, or it crashes. Loading a model that nearly fills your VRAM (e.g., a 101 GB model on a 108 GB system) leaves almost nothing for context, limiting you to roughly 4,000 tokens — unusable for serious work.

**Rule of thumb:** the model should occupy no more than 70–75% of your available VRAM to leave room for a useful context window.

---

## Quantisation: Fitting More into Less

Quantisation reduces numerical precision — rounding weights from 16-bit floats down to 8-bit, 4-bit, or lower — to shrink the model's memory footprint. Most of the capability is preserved; very low quantisations (2-bit, 3-bit) show measurable quality degradation.

**Q4_K_M is the reliable default** for most use cases: good quality, roughly half the VRAM of full precision, and well-supported across all inference engines. Q5_K_M and Q8 give better output if your VRAM allows. Q2/Q3 are useful on very constrained hardware but are best avoided for reasoning-heavy tasks.

The GGUF format (from Llama.cpp) is the industry standard for quantised local inference. When pulling models from Hugging Face, filter for GGUF.

---

## Hardware Architectures: Discrete GPU vs. Unified Memory

There are two fundamentally different approaches to memory for local inference.

### Discrete GPU

A traditional setup where the GPU has its own dedicated VRAM, separate from system RAM. CPU and GPU communicate over PCIe, which creates a bandwidth bottleneck. The VRAM ceiling is determined by the GPU card itself.

Consumer cards top out at 24 GB (RTX 3090/4090). Professional cards with higher VRAM — RTX 6000 (48 GB), RTX Pro 6000 (96 GB) — cost $7,000–$10,000+. For inference-only workloads, this cost-to-VRAM ratio is poor.

**Best for:** multi-GPU setups, high-throughput server deployments, CUDA-dependent workloads, training.

### Unified Memory Architecture (UMA)

The CPU, GPU, and NPU share a single high-speed RAM pool with no PCIe bottleneck. The practical result: a system with 128 GB of unified RAM can make ~108 GB available for inference, at a fraction of the cost of equivalent discrete VRAM.

**Apple M-series**: mature ecosystem, excellent stability, strong community support, but price premium and limited system-level customisation.

- **Entry / base benchmark tier — M1 MacBook, 16 GB unified RAM.** With shared CPU/GPU memory and typical macOS overhead (~8 GB), 16 GB leaves roughly 8 GB available for the GPU. This is enough to run 8B models comfortably at Q4 quantisation. Anything less forces you down to 3B–4B models. The M1 MacBook 16 GB is the Apple baseline used across LocoLab benchmarks — the floor from which all Apple-silicon comparisons are made.

- **High-capacity tier — Mac Studio M3 Ultra (192 GB / 512 GB).** Note: Apple discontinued the 512 GB M3 Ultra configuration and, as of mid-2025, stopped taking orders. The Mac Mini was also effectively unavailable in April 2025, with reported wait times of 3–6 months or longer. Check current availability before planning a purchase around specific configurations.

**AMD Strix Halo (Ryzen AI 395)**: delivers comparable or greater memory capacity to the Mac at lower cost, runs Linux natively, and gives full driver and OS control. Available in mini-PC form factors (e.g., GMK Tech Evo X2, Minisforum, ASUS) for $2,100–$2,500.

**Nvidia DGX Spark**: 128 GB unified memory, ~$4,000. Enterprise support, clean software stack.

**Best for:** large single-node inference, privacy-focused deployments, cost-sensitive high-VRAM needs.

### Memory Configuration on Linux (UMA systems)

On AMD Strix Halo systems running Linux, the **GTT (Graphics Translation Table)** setting controls how much system RAM the kernel allocates to the GPU. Without manual configuration, Linux may reserve far less than the physical capacity.

**Standard configuration:** 108 GB GPU / 20 GB OS. This leaves enough headroom to avoid kernel panics during sustained inference load. Exceeding the GPU allocation into OS memory causes system instability.

On AMD hardware, use **ROCm drivers** (proprietary) over Vulkan for AI workloads — ROCm typically delivers 15–20% better throughput for inference. The AMD GPU toolbox (containerised, Docker or Podman) provides pre-compiled driver packages.

---

## Operating System

| OS | Recommendation |
|----|---------------|
| **Linux (Fedora)** | First choice for inference servers. Best driver support, Cockpit for headless web management, most community packages. |
| **macOS** | Best for Apple silicon. Plug-and-play, stable, excellent MPS acceleration. Less flexible for driver-level tuning. |
| **Windows** | Avoid for serious inference workloads — limited memory addressability for integrated/unified GPU. |

---

## Platform Comparison

| Platform | VRAM / RAM | Approx. cost | Notes |
|----------|-----------|-------------|-------|
| RTX 4090 | 24 GB discrete | $1,500–$2,000 | Consumer max; good CUDA ecosystem |
| RTX 3090 | 24 GB discrete | $700–$900 used | Strong value second-hand |
| MacBook / Mac Mini (M1, 16 GB) | 16 GB unified | $700–$1,000 used | LocoLab Apple baseline; runs 8B models comfortably |
| AMD Strix Halo mini-PC | 128 GB unified | $2,100–$2,500 | Best $/GB for large models |
| Mac Studio (M3 Ultra) | 192 GB unified | $4,000+ | Check availability — 512 GB config discontinued; orders paused mid-2025 |
| Nvidia DGX Spark | 128 GB unified | ~$4,000 | Enterprise warranty, clean stack |
| RTX 6000 / Pro 6000 | 48–96 GB discrete | $7,000–$10,000 | High discrete VRAM, high cost |

*Hardware prices change frequently. Treat this table as directional, not definitive.*

---

## Software Stack

| Layer | Recommended | Notes |
|-------|------------|-------|
| Inference engine | **Ollama** or **Llama.cpp** | Ollama for ease; llama.cpp for maximum control |
| Model format | **GGUF** | Universal quantised format; filter Hugging Face by GGUF |
| Model management | **Open WebUI** | Browser-based, connects to Ollama |
| IDE integration | **Continue.dev** | VS Code / JetBrains extension, points at local server |
| Remote management | **Cockpit** | Web dashboard for headless Linux servers |

---

## The Self-Upgrading Machine

The most durable argument for a hardware investment over a subscription is trajectory. Open-weight models improve continuously — the hardware you buy today will run materially better models in six months without any upgrade. A subscription is a fixed fee for a service that can change, degrade, or be discontinued. A local inference machine is a one-time cost whose effective capability increases as the model ecosystem matures.

This dynamic is accelerating: aggressive quantisation techniques and emerging architectures (including sub-2-bit ternary weight models) are pushing the capability-per-VRAM ratio rapidly upward. Hardware purchased at a given tier will continue to unlock more capable models over time.

---

## Before You Buy — Audit Checklist

- What is the largest model I need to run at full context? (determines minimum VRAM)
- Will I use multiple models simultaneously? (multiply requirements)
- Do I need CUDA specifically? (limits you to Nvidia)
- Do I need to run inference 24/7? (affects cooling, power, form factor)
- Is this a single-user workstation or a shared server? (affects RAM, network, OS choice)

Run LocoBench on candidate hardware before committing. Theoretical VRAM capacity and real-world throughput (tokens/sec) diverge significantly across architectures and model formats.

---

*See also: [CHOOSING.md](CHOOSING.md) for deployment strategy (local vs cloud VPS), model selection, and the minimal viable stack.*
