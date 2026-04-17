---
title: "Proof of Concept"
---

LocoPuente is the "closing the gap" PoC: a minimal, credible demonstration that local AI on one secondhand consumer GPU can deliver the student-facing capabilities an institution currently leans on frontier cloud AI for. One workstation, one card, three backend inference services, one tool-augmented general chat front end, and three purpose-built research and study front ends.

OpenWebUI, augmented with ComfyUI (image generation), Speaches (voice), and OpenTerminal (coding and terminal workflow), provides functional equivalence to commercial chat interfaces -- chat, voice in/out, image generation, code assistance -- in a single browser tab. The three companion front ends cover deep research, tutoring, and NotebookLM-style research-to-media. The claim is not that local small models match frontier models on every benchmark; the claim is that for the way students actually use AI -- dialogically, in conversation -- they are close enough to close the gap.

---

## Hardware

| | |
|---|---|
| **Machine** | Puente |
| **Chassis** | AMD Ryzen 5 2600 desktop tower |
| **GPU** | NVIDIA RTX 3090 24 GB GDDR6X |
| **Memory bandwidth** | 936 GB/s |
| **CUDA compute** | 8.6 |
| **System RAM** | 32 GB DDR4 (minimum) |
| **OS** | Ubuntu 22.04 LTS |

The entire PoC runs on a single RTX 3090. The 24 GB of VRAM is what makes the minimal PoC work -- it absorbs LLM inference, image generation, and voice services concurrently.

---

## Backend Services

Three services run on the RTX 3090, each exposing a clean API that the front-end apps consume:

| Service | Role | Port |
|---|---|---|
| **Ollama** | LLM inference (OpenAI-compatible chat/completions API) | 11434 |
| **ComfyUI** | Image generation (backend API + optional direct UI) | 8188 |
| **Speaches** | Audio in/out -- STT (faster-whisper) and TTS (Kokoro, Piper fallback) | 8000 |

Every capability the PoC demonstrates routes through one of these three services. OpenTerminal, a coding-and-terminal tool, is configured as an additional OpenWebUI tool/service rather than as a stand-alone front end.

---

## Front-End Apps

Four purpose-built front ends sit on top of the backend services:

| App | Purpose | Consumes |
|---|---|---|
| **OpenWebUI** | General-purpose chat interface with tool augmentation -- text chat, voice in/out (Speaches), image generation (ComfyUI), and coding assistance (OpenTerminal). Functional equivalent of commercial chat UIs. | Ollama, Speaches, ComfyUI, OpenTerminal |
| **Vane** | Deep research | Ollama |
| **DeepTutor** | Research and tutoring | Ollama |
| **OpenNotebook** | Podcast generation, quizzes, structured notes -- a NotebookLM clone without video | Ollama, Speaches |

OpenWebUI carries the general-purpose chat envelope a student would otherwise get from a commercial service. The three companion apps sit beside it for deep research, tutoring, and notebook-style research-to-media. Each is an existing open-source project; the PoC is the integration and the hardware, not novel app code.

---

## VRAM Budget (RTX 3090, 24 GB)

Headline: the full stack fits concurrently with comfortable headroom.

| Service | Model | VRAM |
|---|---|---|
| Ollama -- primary LLM | Llama 3.1 8B Q4_K_M (or Qwen 2.5 7B) | ~5 GB |
| Speaches STT + TTS | Whisper base/small + Kokoro 82M | ~0.7 GB |
| ComfyUI -- image generation | SDXL base + refiner | ~8-10 GB |
| **Full stack concurrent** | | **~14-16 GB -- comfortable** |

Larger models fit when the card is not doing image generation at the same time:

- Llama 3.1 13B Q4_K_M: ~8 GB
- 30B-class Q4: ~18 GB (image gen idle)
- FLUX.1 Dev FP16: ~16-24 GB (standalone image run)

---

## PoC Capabilities

| Capability | Provided by | Front-end |
|---|---|---|
| General chat | Ollama | OpenWebUI |
| Voice input / voice output | Speaches | OpenWebUI (via tool integration) |
| Image generation | ComfyUI | OpenWebUI (via tool integration) or ComfyUI directly |
| Coding assistant and terminal workflow | Ollama + OpenTerminal | OpenWebUI (via tool integration) |
| Deep research | Ollama | Vane |
| Research and tutoring | Ollama | DeepTutor |
| Podcast generation from notes | Ollama + Speaches | OpenNotebook |
| Quizzes and structured summaries | Ollama | OpenNotebook |

All services expose OpenAI-compatible APIs. All run without internet access. All student data stays on the machine.

---

## Known Constraints

- All services share the one 24 GB card. Concurrent LLM + SDXL + voice runs comfortably. FLUX.1 Dev FP16 at full quality consumes most of the card on its own and is best run when other workloads are idle.
- System RAM should be 32 GB minimum to avoid model paging to disk.

---

## What Is Deliberately Out of Scope

The minimal PoC is the four front ends above. The broader LocoLabo ecosystem -- the Keep Asking research chat tool, AnythingLLM unit RAG chatbots, Perplexica, Stirling PDF, Excalidraw, CiteSight, LocoEnsayo rehearsal chatbots, and the TalkBuddy / StuddyBuddy / Career Compass desktop clients -- also runs against Puente's Ollama and Speaches endpoints where relevant. Those are documented in their own project docs. Keeping the PoC itself narrow is the point of "closing the gap": prove the core on one card, then expand.

---

## The Cost Argument

One secondhand AMD Ryzen 5 2600 desktop. One secondhand RTX 3090. The full student-facing stack. For less than a year of frontier cloud AI subscriptions for a small team.
