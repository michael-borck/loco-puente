# Local AI Stack: Architecture and Infrastructure Specification

**Version:** 2.1  
**Status:** Draft  
**Target Environment:** LocoLabo / PoC Workstation (Puente, single RTX 3090)  
**Date:** April 2026

---

## 1. Overview

This document specifies the architecture and infrastructure for the LocoPuente "closing the gap" minimal PoC -- a fully local, privacy-preserving AI stack running on a single secondhand consumer GPU. The stack provides large language model (LLM) inference, image generation, and voice interaction (speech-to-text and text-to-speech) as backend services, with four purposeful front ends sitting on top.

The workstation (Puente) hosts a single NVIDIA RTX 3090 24 GB. The 24 GB of VRAM absorbs concurrent LLM inference, image generation, and voice services with comfortable headroom. No second card is required for the minimal PoC.

The four front ends are deliberately chosen. **OpenWebUI** is the general-purpose chat interface, augmented with **ComfyUI** (image generation), **Speaches** (voice in/out), and **OpenTerminal** (coding and terminal workflow) wired in as tools -- so a student gets commercial-chat-equivalent functionality (text, voice, images, code) in a single browser tab. Alongside it sit three companion apps: **Vane** (deep research), **DeepTutor** (research and tutoring), and **OpenNotebook** (podcasts, quizzes, and structured notes -- a NotebookLM clone without video). Together they cover the capability envelope a student actually needs from a local AI service.

The broader LocoLabo ecosystem -- the NBF Keep Asking research chat tool, AnythingLLM unit RAG chatbots, Perplexica, Stirling PDF, Excalidraw, CiteSight, LocoEnsayo rehearsal chatbots, and the TalkBuddy / StuddyBuddy / Career Compass desktop client apps -- consumes Puente's Ollama and Speaches endpoints where relevant. Those components are documented separately; the minimal PoC is deliberately narrower.

The design philosophy follows the LocoLabo 80-20 principle: achieve strong, demonstrable capability through hardware optimisation and open-source tooling rather than expensive infrastructure.

---

## 2. Hardware Specification

### 2.1 GPU Configuration

| | Primary (and only) GPU |
|---|---|
| Machine | Puente |
| Model | NVIDIA RTX 3090 |
| VRAM | 24 GB GDDR6X |
| Memory Bus | 384-bit |
| Memory Bandwidth | ~936 GB/s |
| CUDA Compute Capability | 8.6 |
| Tensor Cores | Yes (3rd gen) |
| Assigned role | Ollama + ComfyUI + Speaches (full minimal PoC stack) |

The minimal PoC is a single-card configuration. Running the full stack on one 3090 is the point of the "closing the gap" framing: one secondhand consumer GPU is enough.

### 2.2 System Configuration

| Component | Specification |
|---|---|
| Machine | Puente (Ryzen 5 2600 desktop) |
| Minimum System RAM | 32 GB DDR4 |
| Recommended System RAM | 64 GB DDR4 |
| Storage (models) | 500 GB NVMe SSD (minimum) |
| OS | Ubuntu 22.04 LTS |
| Driver | 570 series |
| CUDA Version | 12.4 |

### 2.3 VRAM Budget (RTX 3090, 24 GB)

| Service | Model | Estimated VRAM |
|---|---|---|
| Ollama | Llama 3.1 8B Q4_K_M (or Qwen 2.5 7B) | ~5 GB |
| Speaches STT | Whisper base / small | ~0.5 GB |
| Speaches TTS | Kokoro 82M (+ Piper fallback) | ~0.2 GB |
| ComfyUI | SDXL base + refiner | ~8-10 GB |
| **Full stack concurrent (LLM + voice + SDXL)** | | **~14-16 GB -- comfortable** |

Larger models fit when image generation is idle:

- Llama 3.1 13B Q4_K_M: ~8 GB
- 30B-class Q4: ~18 GB (image gen idle)
- FLUX.1 Dev FP16: ~16-24 GB (best run standalone)
- FLUX.1 Dev GGUF Q8 (~12 GB) or Schnell Q4 (~8 GB) leave room for concurrent LLM and voice services

### 2.4 GPU Assignment

| CUDA Device | Card | Services | Port(s) |
|---|---|---|---|
| `CUDA_VISIBLE_DEVICES=0` | RTX 3090 24 GB | Ollama, ComfyUI, Speaches | 11434, 8188, 8000 |

---

## 3. Software Stack

### 3.1 Component Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Minimal PoC Front Ends                            │
│                                                                          │
│  OpenWebUI (general chat)   Vane        DeepTutor       OpenNotebook     │
│  + tools: ComfyUI,          (deep       (research +     (podcasts,       │
│   Speaches, OpenTerminal    research)    tutoring)      quizzes, notes)  │
└──┬──────────────────────────────┬───────────┬──────────────┬────────────┘
   │                              │           │              │
   ▼                              ▼           ▼              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    Backend Services on the RTX 3090                       │
│                                                                           │
│   Ollama :11434         ComfyUI :8188         Speaches :8000              │
│   (LLM, OpenAI API)     (image generation)    (STT + TTS)                 │
│                                                                           │
│   OpenTerminal          (coding + terminal tool consumed by OpenWebUI)    │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│  Puente -- Ryzen 5 2600                                                  │
│  NVIDIA RTX 3090 24 GB GDDR6X  (single card, all three services)         │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Front-End Catalogue

The minimal PoC standardises on four front ends. OpenWebUI is the general chat interface; the other three are purpose-built companions. OpenTerminal is not a separate front end -- it is wired in as an OpenWebUI tool.

| App | Purpose | Backend dependencies |
|---|---|---|
| OpenWebUI | General chat with commercial-equivalent functionality: text, voice in/out (via Speaches tool), in-chat image generation (via ComfyUI tool), coding assistance (via OpenTerminal tool) | Ollama + ComfyUI + Speaches + OpenTerminal |
| Vane | Deep research | Ollama |
| DeepTutor | Research and tutoring | Ollama |
| OpenNotebook | Podcast generation, quizzes, structured notes (NotebookLM clone without video) | Ollama, Speaches |

The catalogue is deliberately short. The minimal PoC is a demonstration, not an exhaustive service directory.

---

### 3.3 Front-End Components

#### OpenWebUI
- **Role:** General student AI access -- the primary day-to-day interface; functional equivalent of commercial chat UIs when augmented with the three tool integrations below
- **API compatibility:** Ollama (chat), Speaches (voice tool), ComfyUI (image tool), OpenTerminal (coding tool)
- **Deployment:** Docker container (port 3000)
- **Features:** Multi-model switching, conversation history, voice input/output, in-chat image generation, in-chat coding assistance
- **URL:** https://openwebui.com

#### OpenTerminal
- **Role:** Coding assistant and terminal-workflow tool wired into OpenWebUI as a registered tool/service. Not a separate front end
- **Consumer:** OpenWebUI calls OpenTerminal when a chat turn requires coding assistance or a terminal context
- **API compatibility:** Ollama (chat/completions)
- **Use case:** Code assistance, shell interaction, and script drafting surfaced inside the same OpenWebUI conversation a student is already in

#### Vane
- **Role:** Deep research -- multi-step search, synthesis, and citation
- **API compatibility:** Ollama

#### DeepTutor
- **Role:** Research-and-tutoring assistant -- walks through topics, explains concepts, checks understanding
- **API compatibility:** Ollama

#### OpenNotebook
- **Role:** Research notebook that transforms uploaded sources (PDFs, links, YouTube transcripts, TXT, PPT) into structured notes, quizzes, and conversational podcasts
- **Key feature:** NotebookLM-style experience without the video side
- **API compatibility:** Ollama (LLM) + Speaches (podcast audio generation)
- **Deployment:** Docker container (port 8080)
- **URL:** https://www.open-notebook.ai

---

### 3.3.1 Beyond the Minimal PoC

The broader LocoLabo ecosystem also consumes Puente's Ollama and Speaches endpoints. These are documented in their own project docs and are **not** part of the minimal PoC demonstration:

- **Keep Asking custom chat** (chat.locolabo.org) -- controlled NBF research environment with consent, exit survey, and turn-based logging
- **Perplexica** -- cited AI web search using SearXNG as the search backend
- **AnythingLLM** -- unit-specific RAG chatbots embedded in Blackboard
- **Stirling PDF, Excalidraw, CiteSight** -- supporting productivity tools
- **LocoEnsayo rehearsal chatbots** -- CloudCore Networks, Pinnacle Tours
- **TalkBuddy, StuddyBuddy, Career Compass** -- LocoLabo desktop client apps that point at Puente's Ollama and Speaches endpoints

---

### 3.4 Backend and Infrastructure Components

#### Ollama
- **Role:** Local LLM inference backend
- **API:** OpenAI-compatible REST API
- **Model format:** GGUF (via llama.cpp)
- **Deployment:** Native Linux service (single systemd instance)
- **URL:** https://ollama.ai

**Instance assignment:**

| Instance | GPU | Port | Recommended models |
|---|---|---|---|
| ollama | RTX 3090 24 GB | 11434 | Llama 3.1 8B Q4_K_M, Qwen 2.5 7B, 13B Q4_K_M, 30B-class Q4 |

**Launch command:**

```bash
# Single instance on the RTX 3090 (CUDA device 0)
CUDA_VISIBLE_DEVICES=0 OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

**Recommended models:**

| Model | Size | VRAM | Use case |
|---|---|---|---|
| Llama 3.1 8B Q4_K_M | ~5 GB | ~5 GB | General-purpose default |
| Qwen 2.5 7B Q4_K_M | ~5 GB | ~5 GB | Strong reasoning |
| Llama 3.1 13B Q4_K_M | ~8 GB | ~8 GB | Higher-quality responses |
| 30B-class Q4 | ~18 GB | ~18 GB | Large-model inference when image gen is idle |

#### Speaches
- **Role:** Local TTS and STT server
- **API:** OpenAI Audio API-compatible (port 8000)
- **GPU assignment:** RTX 3090 (CUDA device 0) -- voice services co-reside on the primary card; their VRAM footprint is negligible relative to LLM and image-gen workloads
- **STT engine:** faster-whisper
- **TTS engines:** Kokoro (primary, ranked #1 TTS Arena), Piper (fallback)
- **Deployment:** Docker container with GPU passthrough
- **Integration:** Native Open WebUI plugin; OpenNotebook uses Speaches for podcast audio generation; usable by any OpenAI-compatible client (including downstream LocoLabo desktop apps such as TalkBuddy, StuddyBuddy, and Career Compass)
- **URL:** https://speaches.ai

```yaml
environment:
  - NVIDIA_VISIBLE_DEVICES=0
```

#### ComfyUI
- **Role:** Local AI image generation -- dual role as backend API and direct student UI
- **GPU assignment:** RTX 3090 24 GB (CUDA device 0)
- **Deployment:** Native Python (venv), GPU-accelerated
- **Port:** 8188
- **URL:** https://github.com/comfyanonymous/ComfyUI
- **As backend:** Open WebUI calls the ComfyUI API to provide in-chat image generation -- students never need to open ComfyUI directly for simple image requests
- **As direct UI:** Students who want node-based workflow control, ControlNet, LoRAs, or advanced pipelines access ComfyUI directly in the browser
- **Note:** Open Notebook AI does not support image generation -- ComfyUI is not connected to it

```bash
CUDA_VISIBLE_DEVICES=0 python main.py --port 8188
```

---

### 3.5 Ecosystem Components (Beyond the Minimal PoC)

The following productivity and supporting tools run alongside the minimal PoC on Puente or externally. They are not part of the minimal PoC scope but are listed here for operational reference:

- **SearXNG** -- shared private web search backend (Docker, port 8888); consumed by Perplexica and by OpenWebUI's optional web-search plugin
- **Stirling PDF** -- self-hosted PDF toolkit (Docker, port 8089)
- **Excalidraw** -- self-hosted collaborative whiteboard (Docker, port 3333)
- **CiteSight** -- academic citation verification and writing quality checker, externally hosted at citesight.eduserver.au (calls Crossref, Semantic Scholar, OpenAlex)
- **Keep Asking custom chat** -- NBF research environment at chat.locolabo.org, the only interface with participant consent and turn-based logging
- **Perplexica** -- cited AI web search using SearXNG as its search backend (Docker, port 3001)
- **AnythingLLM** -- unit-specific RAG chatbots embedded in Blackboard (Docker, port 3002)
- **LocoEnsayo chatbots** -- CloudCore Networks, Pinnacle Tours (server-side rehearsal scenarios running against Puente's Ollama)
- **TalkBuddy, StuddyBuddy, Career Compass** -- LocoLabo desktop client apps that point at Puente's Ollama and Speaches endpoints

These are documented in their own project docs. The minimal PoC demonstration scope (§8) intentionally covers only the four front ends from §3.2.

---

## 4. Image Generation Models

### 4.1 Model Tiers on the RTX 3090 (24 GB)

| Model | VRAM Required | Resolution | Gen Time | Quality |
|---|---|---|---|---|
| SD 1.5 | ~4 GB | 512x512 | ~2 sec | Baseline |
| SDXL 1.0 base | ~6.5 GB | 1024x1024 | ~15-20 sec | Good |
| SDXL + refiner | ~8-10 GB | 1024x1024 | ~25-35 sec | Better |
| FLUX.1 Schnell GGUF Q4 | ~8 GB | 1024x1024 | ~30 sec | Excellent |
| FLUX.1 Dev GGUF Q8 | ~12 GB | 1024x1024 | slower | Near full |
| FLUX.1 Dev FP16 | ~16-24 GB | 1024x1024 | slowest | Full quality |

> The 3090's 24 GB accommodates FLUX.1 Dev FP16 alongside the LLM and voice services when image generation is the active workload. For sustained concurrent use, FLUX.1 Dev GGUF Q8 leaves more headroom for Ollama and ComfyUI queue processing.

### 4.2 Recommended Community Checkpoints

| Checkpoint | Style | Source |
|---|---|---|
| Juggernaut XL v10 | Photorealistic | CivitAI |
| RealVisXL V4.0 | Photorealistic | CivitAI |
| DreamShaper XL | Artistic / stylised | CivitAI |

All available free from https://civitai.com.

---

## 5. Network and Ports

**Minimal PoC services:**

| Service | Port | Protocol | GPU | Notes |
|---|---|---|---|---|
| Ollama | 11434 | HTTP | RTX 3090 | LLM API; backend for all five PoC front ends |
| ComfyUI | 8188 | HTTP | RTX 3090 | Image generation UI + API |
| Speaches | 8000 | HTTP | RTX 3090 | TTS/STT API |
| OpenWebUI | 3000 | HTTP | -- | General chat + voice + images |
| OpenTerminal | (per deployment) | HTTP | -- | Coding + terminal tool registered with OpenWebUI (not a separate front end) |
| Vane | (per deployment) | HTTP | -- | Deep research front end |
| DeepTutor | (per deployment) | HTTP | -- | Research and tutoring front end |
| OpenNotebook | 8080 | HTTP | -- | Podcasts, quizzes, notes |

**Ecosystem services (beyond the minimal PoC):**

| Service | Port | Protocol | GPU | Notes |
|---|---|---|---|---|
| Perplexica | 3001 | HTTP | -- | Cited AI web search |
| AnythingLLM | 3002 | HTTP | -- | Blackboard RAG chatbots |
| SearXNG | 8888 | HTTP | -- | Shared private search backend |
| Stirling PDF | 8089 | HTTP | -- | PDF toolkit |
| Excalidraw | 3333 | HTTP | -- | Collaborative whiteboard |
| CiteSight | external | HTTPS | -- | citesight.eduserver.au -- citation checker |

All services bind to localhost by default. For LAN access within LocoLabo, bind to the workstation's local IP address. Do not expose to the public internet without authentication.

---

## 6. Deployment Architecture

### 6.1 Service Deployment Map

```
Minimal PoC
-----------
systemd services
└── ollama            (port 11434, GPU 0 -- RTX 3090)

Python venv
└── comfyui           (port 8188,  GPU 0 -- RTX 3090)

docker-compose.yml
├── speaches          (port 8000,  GPU 0 -- RTX 3090)
├── open-webui        (port 3000,  no GPU)
└── open-notebook     (port 8080,  no GPU)

OpenWebUI tool registrations (not deployed as a separate front end)
└── OpenTerminal      (coding + terminal tool, registered inside OpenWebUI)

Front ends deployed per their own project guides
├── Vane              (deep research)
└── DeepTutor         (research + tutoring)

Ecosystem (beyond the minimal PoC)
----------------------------------
docker-compose.yml (optional, not required for the minimal PoC)
├── perplexica        (port 3001,  no GPU)
├── anythingllm       (port 3002,  no GPU)
├── stirling-pdf      (port 8089,  no GPU)
├── searxng           (port 8888,  no GPU -- shared search backend)
└── excalidraw        (port 3333,  no GPU)

Client-side desktop apps (installed per user, point at Puente endpoints)
├── TalkBuddy         (Ollama :11434 + Speaches :8000)
├── StuddyBuddy       (Ollama :11434)
└── Career Compass    (Ollama :11434)

External / separately hosted
├── chat.locolabo.org (NBF Keep Asking research tool -- connects to Ollama API)
└── citesight.eduserver.au (citation checker -- calls Crossref, Semantic Scholar, OpenAlex)
```

### 6.2 Data Persistence

| Service | Volume / Path | Contents |
|---|---|---|
| Ollama | ~/.ollama | Downloaded models |
| Open WebUI | ./open-webui-data | Chat history, settings |
| Perplexica | ./perplexica-data | Search history, uploaded files |
| AnythingLLM | ./anythingllm-data | Document workspaces, embeddings |
| Speaches | ./speaches-data | TTS/STT model cache |
| Open Notebook | ./open-notebook-data | Notes, sources, embeddings |
| SearXNG | ./searxng-data | Configuration, engine settings |
| Stirling PDF | ./stirling-data | Temp processing only -- no persistence needed |
| ComfyUI | ./ComfyUI/models | Image generation models |

---

## 7. API Compatibility

All core AI services expose OpenAI-compatible APIs, enabling interoperability across the stack.

| Endpoint | Provided by | Consumed by |
|---|---|---|
| `/v1/chat/completions` | Ollama | Open WebUI, Perplexica, AnythingLLM, Open Notebook, Custom chat |
| `/v1/audio/transcriptions` | Speaches | Open WebUI, Open Notebook |
| `/v1/audio/speech` | Speaches | Open WebUI, Open Notebook |
| Image generation API | ComfyUI | Open WebUI (in-chat images), direct student UI |
| Web search API | SearXNG | Open WebUI, Perplexica |
| Citation verification | Crossref / Semantic Scholar / OpenAlex | CiteSight (external) |

---

## 8. PoC Demonstration Scope

The minimal PoC is demonstrated by these capabilities running on the single RTX 3090:

| Capability | Front end | Backend service | Status |
|---|---|---|---|
| General LLM chat with voice and images | OpenWebUI | Ollama + Speaches + ComfyUI | Ready |
| Coding assistant and terminal workflow | OpenWebUI (OpenTerminal tool) | Ollama | Ready |
| Deep research | Vane | Ollama | Ready |
| Research and tutoring | DeepTutor | Ollama | Ready |
| Podcast generation from sources | OpenNotebook | Ollama + Speaches | Ready |
| Quizzes and structured notes from sources | OpenNotebook | Ollama | Ready |
| Image generation (in-chat) | OpenWebUI + ComfyUI API | ComfyUI | Ready |
| Image generation (direct UI, incl. FLUX.1 Dev FP16) | ComfyUI | ComfyUI | Ready |
| Large-model inference (30B-class Q4) | OpenWebUI | Ollama | Ready (image gen idle) |
| **Full minimal PoC stack concurrent on one card** | All four front ends | Ollama + ComfyUI + Speaches (+ OpenTerminal as OpenWebUI tool) | **Ready -- the "closing the gap" claim** |

---

## 9. Known Constraints

- All services share the one 24 GB card. With the minimal workload mix (8B LLM + voice + SDXL) concurrent use stays around 14-16 GB. FLUX.1 Dev FP16 at full quality consumes most of the card on its own and is best run when image generation is the active workload.
- SDXL refiner adds approximately 2-3 GB VRAM overhead. Monitor with `nvidia-smi`.
- Automatic1111 (A1111) does not support FLUX. Use ComfyUI or Forge for FLUX models.
- System RAM should be 32 GB minimum to avoid model paging to disk, particularly with large Ollama model contexts.
- When research participants are running the Keep Asking custom chat tool (chat.locolabo.org, part of the broader ecosystem), that is the only interface with participant consent and turn-based logging -- do not route research participants through OpenWebUI or any other front end.

---

## 10. Future Expansion

This stack forms the foundation for LocoPuente (locopuente.org), the Faculty-facing BridgeAI initiative, and hosts most LocoEnsayo rehearsal chatbots as well. LocoBench benchmarking runs on the dedicated Colmena, Tortuga, and Hormiga machines in the LocoLabo fleet.

The next scale target is a single Apple M3 Ultra (512 GB unified memory), which would run the full stack for 50 to 100 concurrent users with comfortable headroom, on a machine the institution owns outright. The transition from the current RTX 3090 PoC to the M3 Ultra is not a rebuild -- it is a hardware upgrade. Ollama, ComfyUI, Speaches, the OpenWebUI tool integrations, the three companion front ends, and the broader ecosystem endpoints all carry forward unchanged.

**The frontier-capability argument at Phase 2.** On standardised benchmarks the best open-weight models sit roughly 5-10 percentage points behind the best frontier closed models. That gap is real but not decisive, particularly for the way students actually use AI -- dialogically, in conversation. A conversation that iterates, clarifies, and corrects closes most of that gap naturally: the student supplies context, notices errors, and asks again. On an M3 Ultra the open-weight models run large enough that the residual gap is not a reason to send student data to a commercial provider. The remaining reasons (habit, licensing defaults, integration inertia) are not capability arguments.

A planned LocoBench image-generation study will benchmark SD 1.5 and SDXL across all available GPU tiers at fixed parameters (prompt, seed, step count, resolution) to map the floor of local image-generation performance on consumer hardware -- following the same methodology as the LLM inference benchmarking work.

The OpenAI API-compatible design means any component can be swapped or upgraded independently without breaking integrations.

---

*Document maintained by Michael Borck, LocoLabo, Curtin University.*
