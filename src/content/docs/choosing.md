---
title: Choosing Your Stack
---

# Choosing Your Stack — A Decision Guide for Puente

This document helps you decide *how* to deploy, *what* to run, and *why* it matters — before you touch any configuration.

---

## Start Here: Strategy, Not Tools

Before picking hardware or models, it helps to understand what you are actually doing when you use an LLM.

**LLMs do not retrieve facts. They interpolate.**
Every response is a statistically predicted continuation — the next most plausible token given everything before it. This is extraordinary for certain tasks and unreliable for others. Knowing which is which determines whether the tool amplifies you or misleads you.

### Two modes of use

| Mode | Description | Risk |
|------|-------------|------|
| **Cognitive offloading** | Using the model as a thinking partner — brainstorming, ideating, iterating, drafting, critiquing | Low. You stay in the loop. Hallucinations are caught because you are still thinking. |
| **Cognitive surrender** | Treating the model as an oracle — asking it for facts, trusting its output without verification | High. Hallucinations get amplified, not filtered. |

The framing matters: *a conversation with an AI that amplifies your thinking is fundamentally different from outsourcing your thinking to one.* The first is a productivity multiplier. The second transfers your judgment — and your errors — to a system that cannot know what it does not know.

**Practical heuristic:** Use local AI for brainstorming, ideating, iterating, drafting, and cognitive offloading of simple tasks. Stay close to frontier models for tasks where factual precision matters, and verify outputs independently. The gap between a good local model and a frontier model is much smaller when you are the one doing the thinking.

### Why local at all?

- **Data sovereignty** — your documents, conversations, and ideas stay on your hardware
- **No subscription model** — pay once for hardware (or a VPS), not monthly per seat
- **No usage throttling** — run as many queries as your hardware allows
- **Reproducibility** — pin a model version; it does not change under you
- **Skill transferability** — understanding the local stack prepares you for the edge AI wave (see below)

---

## The Minimal Viable Stack

Three services give you roughly 90% of what commercial AI providers offer:

```
Open WebUI + ComfyUI + Open Terminal
```

| What you get | Commercial equivalent |
|---|---|
| Chat with any local or remote LLM | ChatGPT, Claude, Gemini web UI |
| Image generation (SD, SDXL, FLUX) | Midjourney, DALL·E |
| Terminal with LLM-aware tooling | Codex CLI, GitHub Copilot CLI |
| Built-in audio in/out (Open WebUI) | Voice mode on ChatGPT / Gemini |

**What you do not get (yet):** video generation. That requires significantly more VRAM and is still maturing. ComfyUI supports video workflows (AnimateDiff, Wan, CogVideoX) but treat them as experimental unless you have 24 GB+ VRAM.

---

## Deployment Options

### Option A — Fully Local (on-premise GPU)

You own the hardware, the data never leaves your network.

| VRAM | Realistic capability | Notes |
|------|---------------------|-------|
| 4–6 GB | 7B models at Q4, SD 1.5 image gen | Tight but functional. CPU offload helps. |
| 8 GB | 13B at Q4, SDXL image gen | Good daily driver tier |
| 12 GB | 13–30B at Q4, SDXL comfortable | Solid research workstation |
| 16–24 GB | 34–70B at Q4, FLUX image gen | Near-frontier local capability |
| 24 GB+ (RTX 3090/4090) | 70B+ at Q4, video workflows | Full stack, no meaningful compromise |
| 2× 24 GB | 70B+ at Q5/Q8, multi-GPU split | Effectively on-par with frontier API |

**Run LocoBench** on your hardware to get actual throughput numbers (tokens/sec) rather than relying on this table. Model performance varies significantly by architecture, quantisation method, and generation.

**Note on older GPUs:** NVIDIA CUDA Compute Capability 5.x (Maxwell architecture — GTX 900 series and equivalents) is officially in maintenance mode. PyTorch and related frameworks are progressively dropping support for Compute < 6.0/7.0. If you are on a Compute 5.x card, your current software stack will work until it does not — plan for a hardware refresh or cloud fallback rather than assuming indefinite support.

### Option B — Cloud VPS with GPU (RunPod, Vast.ai, AWS, etc.)

You rent the hardware; you still control the software and data.

| Provider | Notes |
|----------|-------|
| **RunPod** | Best GPU-per-dollar for AI workloads. Spot and on-demand. Community templates available. |
| **Vast.ai** | Peer-to-peer GPU rental, cheapest option. Variable reliability. |
| **Lambda Labs** | Reserved GPU instances, more stable than spot. |
| **AWS / GCP / Azure** | Enterprise SLAs, higher cost, best for institutional compliance requirements. |

**When cloud makes sense:**
- You need more VRAM than you own for a specific job (large model inference, FLUX, video)
- You want a persistent server accessible to multiple users without maintaining local hardware
- Your institution has compliance requirements around where data is processed

**Data sovereignty note:** a VPS you control (with a model you run) is categorically different from a managed AI API. Your data goes to your rented server, not through a third party's inference infrastructure. Both VPS and local give you sovereignty; managed APIs do not.

### Option C — Hybrid

Run the fast lightweight tasks locally (chat, coding assistance) and offload VRAM-heavy tasks (image gen, large models) to a cloud GPU pod on demand. Puente's configuration supports pointing services at external endpoints, so the two can coexist cleanly.

---

## Choosing a Model

The right model depends on your task, your VRAM, and your tolerance for latency. General guidance:

| Task | Model family to consider |
|------|--------------------------|
| General chat, writing, reasoning | Llama 3.x, Qwen 2.5, Mistral |
| Coding | Qwen 2.5 Coder, DeepSeek Coder, CodeLlama |
| Long context (documents, research) | Gemma 3, Qwen 2.5 (128k context variants) |
| Multimodal (image + text) | LLaVA, Qwen2-VL, Gemma 3 |
| Image generation | SD 1.5 (lowest VRAM), SDXL, FLUX.1 |

**For precise model-to-VRAM-tier recommendations, run LocoBench.** It benchmarks candidate models against your actual hardware and surfaces the optimal quality/speed tradeoff for your specific setup. This table dates; LocoBench results do not.

**Quantisation:** Q4_K_M is a reliable default — good quality, roughly half the VRAM of full precision. Q5_K_M and Q8 give higher quality if your VRAM allows. Q2/Q3 quantisations are useful on very constrained hardware but quality degrades noticeably at that level.

---

## The Edge AI Trend — Why This Skill Matters Beyond Your Current GPU

Model efficiency is improving faster than hardware is. A few developments worth watching:

- **Aggressive quantisation** (GPTQ, AWQ, GGUF and successors) has already pushed 7B models onto consumer GPUs that would have required a data centre three years ago
- **1.58-bit ternary weight models** (Microsoft BitNet and related work) use only addition — no multiplication — making inference viable on CPU at useful speeds, and drastically reducing VRAM requirements for a given parameter count
- **Google and others** are actively publishing quantisation research that promises running significantly larger models in the same VRAM envelope

The implication: **the hardware you own today may run meaningfully better models in two years without any upgrade.** More importantly, the architectural shift toward edge inference means that understanding how to deploy and operate local AI is a durable skill — the same mental model that lets you run Llama 3 on a workstation today will let you run its successors on a laptop or embedded device as the ecosystem matures.

Running locally now is not just about the current capability. It is practice for a future where capable AI runs at the edge by default.

---

## Quick Decision Flowchart

```
Do you have a GPU with 8 GB+ VRAM?
├── Yes → Start with the minimal stack (Open WebUI + ComfyUI + Open Terminal)
│         Run LocoBench to find your optimal model tier
│         Add services as you need them
└── No  → Consider a cloud VPS (RunPod spot is cheapest)
          Or run CPU-only with smaller quantised models (7B Q4 is usable)
          Watch 1.58-bit model developments — CPU viability improving fast

Is your data sensitive?
├── Yes → Local or VPS only. Do not use managed AI APIs for this data.
└── No  → Managed APIs fine for non-sensitive tasks; local for everything else

Do you want to supplement rather than replace commercial tools?
└── Yes → Minimal stack. Use local for iteration and drafting,
          frontier API for final-pass precision tasks where you verify output.
```

---

## For Institutions and Organisations

The case for local AI looks different at institutional scale. The key framing shift is **CapEx vs. OpEx**.

Cloud AI is operational expenditure: recurring per-seat costs (typically $200+/month per user for enterprise tiers), rate limits, token quotas, and zero data sovereignty. Local inference is capital expenditure: hardware purchased once, depreciating over time, with uncapped throughput and full data control.

**The compliance argument** is often decisive. Healthcare, legal, financial, and educational institutions handling sensitive data may be unable to use cloud AI APIs regardless of preference. On-premises inference is not a budget decision in these contexts — it is a regulatory requirement.

**The throughput argument** matters at scale. Enterprise cloud subscriptions impose rate limits and quotas. Local hardware transforms AI from a metered external utility into an internal resource — running continuously, without per-query cost, on institutional data that never leaves the network.

**Recommended approach for institutions:**

| Scenario | Recommendation |
|----------|---------------|
| Sensitive data, compliance requirements | Full local deployment — no cloud APIs for regulated data |
| Mixed workloads, some public data | Hybrid: local for sensitive/high-volume, cloud for complex reasoning |
| Evaluation / pilot phase | Start with the minimal stack (Open WebUI + Ollama), run LocoBench on available hardware, assess before committing to hardware procurement |

**Implementation sequence:**
1. Audit data sensitivity — determine what can and cannot leave institutional infrastructure
2. Run LocoBench on available hardware to establish capability baseline
3. Deploy the minimal stack; validate workflows before expanding
4. Procure hardware based on actual measured throughput requirements, not theoretical specs

*See [HARDWARE.md](HARDWARE.md) for hardware selection and procurement guidance.*

---

## What Puente Is Not

- A replacement for critical thinking
- A fact retrieval system (use SearXNG for that — it is in the stack for a reason)
- A substitute for domain expertise

What it is: a self-hosted environment that lets you experiment, build intuition, and develop a working relationship with these tools on your own terms — without giving your data or your cognitive autonomy to a third party.

---

*For hardware benchmarks specific to your machine, see [LocoBench](https://github.com/michael-borck/loco-bench).*
*For deployment configuration, see [README.md](README.md).*
