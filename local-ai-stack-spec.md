# Local AI Stack: Architecture and Infrastructure Specification

**Version:** 1.4  
**Status:** Draft  
**Target Environment:** LocoLabo / PoC Workstation (Puente + Pulpo)  
**Date:** March 2026

---

## 1. Overview

This document specifies the architecture and infrastructure for a fully local, privacy-preserving AI stack running on a dual-GPU consumer workstation. The stack provides large language model (LLM) inference, voice interaction (speech-to-text and text-to-speech), AI-powered research and note-taking, and image generation -- all without cloud dependencies.

Two GPUs are assigned dedicated workload roles: the RTX 3060 12GB (Pulpo) handles LLM inference and image generation, while the RTX 2060 Super 8GB (Puente) handles voice services and a secondary LLM instance. This eliminates the sequential switching constraint of a single-GPU setup and allows all services to run concurrently.

Three distinct chat interfaces serve clearly separated purposes: a custom research tool for the NBF Keep Asking study, Open WebUI for general student access, and AnythingLLM for unit-specific RAG chatbots embedded in Blackboard -- all backed by the same Ollama instances. A shared SearXNG instance provides private web search to both Open WebUI and Perplexica without external API keys. Additional student tools -- Perplexica (cited AI search), Stirling PDF (document tools), Excalidraw (collaborative whiteboard), and CiteSight (citation and writing checker) -- round out the stack.

The design philosophy follows the LocoLabo 80-20 principle: achieve strong, demonstrable capability through hardware optimisation and open-source tooling rather than expensive infrastructure.

---

## 2. Hardware Specification

### 2.1 GPU Configuration

| | GPU 0 (Primary) | GPU 1 (Secondary) |
|---|---|---|
| Machine | Pulpo | Puente |
| Model | NVIDIA RTX 3060 | NVIDIA RTX 2060 Super |
| VRAM | 12 GB GDDR6 | 8 GB GDDR6 |
| Memory Bus | 192-bit | 256-bit |
| Memory Bandwidth | ~360 GB/s | ~448 GB/s |
| CUDA Compute Capability | 8.6 | 7.5 |
| Power cap (actual) | 170W | 184W |
| Assigned role | LLM (primary) + Image Gen | Voice (TTS/STT) + LLM (secondary) |

> GPU index confirmed via nvidia-smi: RTX 3060 = device 0, RTX 2060 Super = device 1.

### 2.2 System Configuration

| Component | Specification |
|---|---|
| Minimum System RAM | 32 GB DDR4 |
| Recommended System RAM | 64 GB DDR4 |
| Storage (models) | 500 GB NVMe SSD (minimum) |
| OS | Ubuntu 22.04 LTS |
| Driver | 550.163.01 |
| CUDA Version | 12.4 |

### 2.3 VRAM Budget by Card

**GPU 0 -- Pulpo, RTX 3060 12GB (LLM primary + image gen)**

| Service | Model | Estimated VRAM |
|---|---|---|
| Ollama instance 0 | Llama 3.1 8B Q4_K_M | ~5 GB |
| ComfyUI (SDXL) | SDXL 1.0 base | ~6.5 GB |
| **LLM only** | | **~5 GB** |
| **Image gen only** | | **~6.5 GB** |
| **LLM + Image gen** | | **~11.5 GB -- tight, not recommended concurrently** |

**GPU 1 -- Puente, RTX 2060 Super 8GB (voice + LLM secondary)**

| Service | Model | Estimated VRAM |
|---|---|---|
| Speaches STT | Whisper base / small | ~0.5 GB |
| Speaches TTS | Kokoro 82M | ~0.2 GB |
| Ollama instance 1 | Mistral 7B / Phi-3 Mini Q4 | ~4.5 GB |
| **Total concurrent** | | **~5.2 GB -- comfortable headroom** |

### 2.4 GPU Assignment

| CUDA Device | Card | Machine | Services | Port(s) |
|---|---|---|---|---|
| `CUDA_VISIBLE_DEVICES=0` | RTX 3060 12GB | Pulpo | Ollama instance 0, ComfyUI | 11434, 8188 |
| `CUDA_VISIBLE_DEVICES=1` | RTX 2060 Super 8GB | Puente | Ollama instance 1, Speaches | 11435, 8000 |

### 2.5 Upgrade Path

| Card | VRAM | Unlocks |
|---|---|---|
| RTX 2060 Super 8GB (current) | 8 GB | Voice stack, secondary LLM |
| RTX 3060 12GB (current) | 12 GB | SD 1.5, SDXL, Ollama 8B |
| RTX 4060 Ti 16GB (incoming) | 16 GB | FLUX.1 Dev GGUF Q8, fully concurrent LLM + image gen on one card |
| RTX 3090 24GB (likely upgrade) | 24 GB | Full stack on one card, FLUX.1 Dev FP16, 30B+ models |

### 2.6 Single-Card Consolidation: RTX 3090 24GB

The RTX 3090 24GB is the likely upgrade target and would allow the entire stack to run on a single card, retiring the dual-GPU arrangement. At 24 GB, all services can run concurrently with comfortable headroom:

| Service | VRAM |
|---|---|
| Ollama 8B Q4_K_M | ~5 GB |
| Speaches (Whisper + Kokoro) | ~0.7 GB |
| SDXL base + refiner | ~8-10 GB |
| **Full stack concurrent (LLM + voice + SDXL)** | **~16 GB -- comfortable** |

> FLUX.1 Dev FP16 occupies the full card and should run standalone. For concurrent workloads, FLUX.1 Dev GGUF Q8 (~12 GB) is the practical choice, leaving headroom for LLM and voice services.

---

## 3. Software Stack

### 3.1 Component Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                  User Interfaces                                      │
│                                                                                       │
│  Custom Chat     Open WebUI    Perplexica    AnythingLLM   Open Notebook   ComfyUI   │
│  (NBF Study)     (General)     (AI Search)   (Blackboard)  (Research)      (Images)  │
│                                                                                       │
│  Stirling PDF    Excalidraw    CiteSight                                              │
│  (PDF Tools)     (Whiteboard)  (Citations -- citesight.eduserver.au)                 │
└──┬───────────────────┬──────────────────────────────────────────┬────────────────────┘
   │                   │                                          │
┌──▼───────────────────▼────────────┐  ┌────────▼──────┐  ┌──────▼──────┐
│  Ollama :11434 (GPU 0 / Pulpo)    │  │   Speaches    │  │   SearXNG   │
│  Ollama :11435 (GPU 1 / Puente)   │  │   :8000       │  │   :8888     │
└──┬────────────────────────────────┘  └────────┬──────┘  └──────┬──────┘
   │                                             │                │
┌──▼─────────────────────────┐  ┌───────────────▼────────────────▼──────┐
│  Pulpo                     │  │  Puente                                │
│  RTX 3060 12GB             │  │  RTX 2060 Super 8GB                    │
│  CUDA device 0             │  │  CUDA device 1                         │
│  Primary LLM + Image Gen   │  │  Voice + Secondary LLM                 │
└────────────────────────────┘  └────────────────────────────────────────┘
```

> SearXNG is a shared backend -- one instance serves both Open WebUI (web search in chat) and Perplexica (cited AI search). No external search API keys required.
> CiteSight is externally hosted at citesight.eduserver.au and calls public academic APIs (Crossref, Semantic Scholar, OpenAlex). No local infrastructure required.

### 3.2 Chat and Search Interface Strategy

| Tool | Purpose | Audience | Key feature |
|---|---|---|---|
| Custom chat (chat.locolabo.org) | NBF research / Keep Asking study | Research participants | Consent, exit survey, turn logging, scheduled uptime |
| Open WebUI | General student AI access | All students | Full-featured, voice, images, web search via SearXNG |
| Perplexica | Cited AI-powered web search | Research-focused students | Perplexity-style cited answers, academic search mode |
| AnythingLLM | Unit-specific RAG chatbots | Students per unit | Embeds in Blackboard, per-unit document workspaces |

Open WebUI and Perplexica are complementary rather than duplicating -- Open WebUI is the general AI assistant, Perplexica is specifically for "find me cited information from the web." Both share the same SearXNG instance as their search backend, meaning no external search API keys are required for either.

Research integrity note: the custom chat tool is the only controlled research environment with consent and logging. Students using any other interface are not research participants.

---

### 3.3 Chat and Search Interface Components

#### Custom Chat Tool (chat.locolabo.org)
- **Role:** Controlled research environment for the NBF Keep Asking study
- **Backend:** Ollama (OpenAI-compatible API)
- **Deployment:** Hosted at chat.locolabo.org
- **Key features:**
  - Privacy-by-design consent mechanism built into the interface
  - Exit survey instrument
  - Scheduled uptime windows
  - Turn-based conversation logging for research analysis
  - Nudge prompt intervention (the Keep Asking experimental condition)
- **Research note:** Minimal interface by design -- reduces confounds and keeps research focus on conversational behaviour, not tool features.


#### Open WebUI
- **Role:** General student AI access -- the primary day-to-day interface
- **API compatibility:** Connects natively to Ollama API
- **Deployment:** Docker container (port 3000)
- **Features:** Multi-model switching, conversation history, RAG support, voice input/output via Speaches, image generation via ComfyUI API, web search via SearXNG
- **URL:** https://openwebui.com

#### Perplexica
- **Role:** Cited AI-powered web search -- the research-focused chat interface
- **Backend:** Ollama (LLM) + SearXNG (search)
- **Deployment:** Docker container (port 3001) -- bundles SearXNG internally, or points to shared SearXNG instance
- **Key features:**
  - Perplexity-style answers with inline source citations
  - Academic search mode (prioritises scholarly sources)
  - Speed / Balanced / Quality search modes
  - File upload and document Q&A
  - No external search API keys required -- SearXNG aggregates 70+ search engines privately
- **URL:** https://github.com/ItzCrazyKns/Perplexica

#### AnythingLLM
- **Role:** Unit-specific RAG chatbots embedded in Blackboard
- **Backend:** Ollama (OpenAI-compatible API)
- **Deployment:** Docker container (port 3002)
- **Key features:**
  - Per-unit document workspaces (unit readings, assessments, course content)
  - Embeddable chatbot widget for Blackboard pages
  - Isolated knowledge bases per unit -- ISYS6020 assistant only knows ISYS6020 content
  - Multi-user support with usage tracking
- **Example use cases:** CloudCore simulation assistant, ISYS6020 course Q&A, assessment explainer
- **URL:** https://anythingllm.com

---

### 3.4 Backend and Infrastructure Components

#### Ollama
- **Role:** Local LLM inference backend (two instances, one per GPU)
- **API:** OpenAI-compatible REST API
- **Model format:** GGUF (via llama.cpp)
- **Deployment:** Native Linux service (two systemd instances)
- **URL:** https://ollama.ai

**Instance assignment:**

| Instance | GPU | Port | Recommended models |
|---|---|---|---|
| ollama-0 | RTX 3060 12GB (Pulpo) | 11434 | Llama 3.1 8B Q4_K_M, Qwen2.5 7B |
| ollama-1 | RTX 2060 Super 8GB (Puente) | 11435 | Mistral 7B Q4_K_M, Phi-3 Mini |

**Launch commands:**

```bash
# Instance 0 on RTX 3060 (CUDA device 0)
CUDA_VISIBLE_DEVICES=0 OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Instance 1 on RTX 2060 Super (CUDA device 1)
CUDA_VISIBLE_DEVICES=1 OLLAMA_HOST=0.0.0.0:11435 ollama serve
```

**Recommended models:**

| Model | Size | VRAM | Use case |
|---|---|---|---|
| Llama 3.1 8B Q4_K_M | ~5 GB | ~5 GB | General purpose (GPU 0) |
| Qwen2.5 7B Q4_K_M | ~5 GB | ~5 GB | Strong reasoning (GPU 0) |
| Mistral 7B Q4_K_M | ~4.5 GB | ~4.5 GB | Instruction following (GPU 1) |
| Phi-3 Mini | ~2.5 GB | ~2.5 GB | Lightweight / fast (GPU 1) |

#### Speaches
- **Role:** Local TTS and STT server
- **API:** OpenAI Audio API-compatible (port 8000)
- **GPU assignment:** RTX 2060 Super / Puente (CUDA device 1)
- **STT engine:** faster-whisper
- **TTS engines:** Kokoro (primary, ranked #1 TTS Arena), Piper (fallback)
- **Deployment:** Docker container with GPU passthrough
- **Integration:** Native Open WebUI plugin; usable by any OpenAI-compatible client
- **URL:** https://speaches.ai

```yaml
environment:
  - NVIDIA_VISIBLE_DEVICES=1
```

#### Open Notebook AI
- **Role:** AI-powered research assistant and note-taking platform
- **Backend:** Ollama (LLM) + Speaches (podcast/audio generation)
- **Input formats:** PDF, links, YouTube, TXT, PPT
- **Key feature:** Transforms research notes into podcasts
- **Deployment:** Docker container (port 8080)
- **URL:** https://www.open-notebook.ai

#### ComfyUI
- **Role:** Local AI image generation -- dual role as backend API and direct student UI
- **GPU assignment:** RTX 3060 12GB / Pulpo (CUDA device 0)
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

### 3.5 Productivity and Study Tools

#### SearXNG
- **Role:** Shared private web search backend
- **Deployment:** Docker container (port 8888)
- **Consumed by:** Open WebUI (web search in chat), Perplexica (cited AI search)
- **Key feature:** Aggregates 70+ search engines without tracking users or requiring API keys. One instance serves the entire stack.
- **URL:** https://searxng.org

#### Stirling PDF
- **Role:** Self-hosted PDF toolkit for students
- **Deployment:** Docker container (port 8089)
- **Key features:** Merge, split, compress, rotate, OCR, annotate, convert PDF to/from Word
- **Student value:** Every student needs PDF tools for assignments, readings, and submissions. No data leaves the machine.
- **URL:** https://stirlingtools.com

#### Excalidraw
- **Role:** Self-hosted collaborative whiteboard and diagramming tool
- **Deployment:** Docker container (port 3333)
- **Key features:** Real-time collaborative drawing, mind maps, system diagrams, freehand sketching, shareable boards
- **Student value:** Group project work, case study mapping, business process diagrams, brainstorming. Relevant for Business and Law students doing visual analysis.
- **URL:** https://excalidraw.com

#### CiteSight
- **Role:** Academic citation verification and writing quality checker
- **Deployment:** Externally hosted at citesight.eduserver.au (no local infrastructure required)
- **Backend:** Calls public academic APIs -- Crossref (DOI resolution), Semantic Scholar, OpenAlex (fallback verification), YouTube/Vimeo oEmbed, Open Library (non-academic sources)
- **Key features:**
  - Verifies whether referenced sources actually exist
  - Four-status verification: Verified, Likely Valid, Suspicious, Not Found
  - Citation formatting check against APA, MLA, and Chicago
  - In-text citation matching against bibliography
  - Writing quality metrics: readability scores, passive voice, academic tone, hedging phrases, sentence variety
  - Writing pattern detection: placeholder text, repetitive starters, formulaic transitions, overused vocabulary, excessive em-dashes, intensifier phrases, excessive bullet points
  - Privacy-first: files processed and immediately deleted, no data stored
- **Student value:** Pre-submission check that catches citation errors and writing issues before they cost marks. Particularly valuable for AI-assisted writing -- students can self-check for patterns associated with AI-generated text before submission.
- **URL:** https://citesight.eduserver.au

---

## 4. Image Generation Models

### 4.1 Model Tiers for 12 GB VRAM

| Model | VRAM Required | Resolution | Gen Time | Quality |
|---|---|---|---|---|
| SD 1.5 | ~4 GB | 512x512 | ~2 sec | Baseline |
| SDXL 1.0 base | ~6.5 GB | 1024x1024 | ~15-20 sec | Good |
| SDXL + refiner | ~8-10 GB | 1024x1024 | ~25-35 sec | Better |
| FLUX.1 Schnell GGUF Q4 | ~8 GB | 1024x1024 | ~30 sec | Excellent |

> FLUX.1 Dev at full quality requires 16-24 GB VRAM. Available after hardware upgrades.

### 4.2 Recommended Community Checkpoints

| Checkpoint | Style | Source |
|---|---|---|
| Juggernaut XL v10 | Photorealistic | CivitAI |
| RealVisXL V4.0 | Photorealistic | CivitAI |
| DreamShaper XL | Artistic / stylised | CivitAI |

All available free from https://civitai.com.

---

## 5. Network and Ports

| Service | Port | Protocol | GPU | Notes |
|---|---|---|---|---|
| Ollama instance 0 | 11434 | HTTP | Pulpo / RTX 3060 | Primary LLM API |
| Ollama instance 1 | 11435 | HTTP | Puente / RTX 2060 Super | Secondary LLM API |
| Open WebUI | 3000 | HTTP | -- | General student chat + images + voice + web search |
| Perplexica | 3001 | HTTP | -- | Cited AI web search |
| AnythingLLM | 3002 | HTTP | -- | Blackboard RAG chatbots |
| Speaches | 8000 | HTTP | Puente / RTX 2060 Super | TTS/STT API |
| Open Notebook AI | 8080 | HTTP | -- | Research, notes, podcast |
| Stirling PDF | 8089 | HTTP | -- | PDF tools |
| ComfyUI | 8188 | HTTP | Pulpo / RTX 3060 | Image generation UI + API backend |
| SearXNG | 8888 | HTTP | -- | Shared search backend (WebUI + Perplexica) |
| Excalidraw | 3333 | HTTP | -- | Collaborative whiteboard |
| CiteSight | external | HTTPS | -- | citesight.eduserver.au -- citation checker |

All services bind to localhost by default. For LAN access within LocoLabo, bind to the workstation's local IP address. Do not expose to the public internet without authentication.

---

## 6. Deployment Architecture

### 6.1 Service Deployment Map

```
docker-compose.yml
├── open-webui        (port 3000,  no GPU)
├── perplexica        (port 3001,  no GPU -- includes bundled SearXNG or points to shared)
├── anythingllm       (port 3002,  no GPU)
├── speaches          (port 8000,  GPU 1 -- Puente / RTX 2060 Super)
├── open-notebook     (port 8080,  no GPU)
├── stirling-pdf      (port 8089,  no GPU)
├── searxng           (port 8888,  no GPU -- shared backend)
└── excalidraw        (port 3333,  no GPU)

systemd services
├── ollama@0          (port 11434, GPU 0 -- Pulpo / RTX 3060)
└── ollama@1          (port 11435, GPU 1 -- Puente / RTX 2060 Super)

Python venv
└── comfyui           (port 8188,  GPU 0 -- Pulpo / RTX 3060)

External / separately hosted
├── chat.locolabo.org (NBF research tool -- connects to Ollama API)
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

The following capabilities are demonstrable on the dual-GPU configuration:

| Capability | Tool | GPU | Status |
|---|---|---|---|
| LLM chat -- general | Open WebUI + Ollama :11434 | Pulpo | Ready |
| LLM chat -- secondary | Open WebUI + Ollama :11435 | Puente | Ready |
| Web search in chat | Open WebUI + SearXNG | -- | Ready |
| Cited AI web search | Perplexica + SearXNG + Ollama | Pulpo | Ready |
| Research nudge intervention | Custom chat (chat.locolabo.org) | Pulpo | Ready |
| Unit RAG chatbot (Blackboard) | AnythingLLM | Pulpo | Ready |
| Voice input (STT) | Speaches + Whisper | Puente | Ready |
| Voice output (TTS) | Speaches + Kokoro | Puente | Ready |
| Research assistant + podcast | Open Notebook AI | Pulpo | Ready |
| Image generation (in-chat) | Open WebUI + ComfyUI API | Pulpo | Ready |
| Image generation (direct UI) | ComfyUI | Pulpo | Ready |
| PDF tools | Stirling PDF | -- | Ready |
| Collaborative whiteboard | Excalidraw | -- | Ready |
| Citation + writing check | CiteSight | External | Ready |
| **Voice + LLM concurrent** | All services | Both cards | **Ready -- key PoC advantage** |

Capabilities requiring hardware upgrade:

| Capability | Requires | ETA |
|---|---|---|
| FLUX.1 Dev Q8 (near-full quality) | RTX 4060 Ti 16GB | Incoming |
| FLUX.1 Dev FP16 (full quality) | RTX 3090 24GB | Incoming |
| LLM + image gen truly concurrent | RTX 4060 Ti 16GB | Incoming |
| Large model inference (30B+) | RTX 3090 / multi-GPU | LocoBench roadmap |

---

## 9. Known Constraints

- LLM inference and SDXL image generation on Pulpo (GPU 0) should not run simultaneously -- both together approach the 12 GB ceiling. In practice, Ollama unloads after inactivity before image generation is triggered.
- SDXL refiner adds approximately 2-3 GB VRAM overhead on GPU 0. Monitor with `nvidia-smi`.
- Automatic1111 (A1111) does not support FLUX. Use ComfyUI or Forge for FLUX models.
- Puente's 8 GB VRAM is sufficient for voice + secondary LLM but cannot run SDXL reliably. Image generation stays on Pulpo only.
- System RAM should be 32 GB minimum to avoid model paging to disk, particularly with large Ollama model contexts.
- The dual-Ollama arrangement requires careful use of the `OLLAMA_MODELS` environment variable to avoid model duplication on disk.
- The custom chat tool (chat.locolabo.org) is the only interface with research consent and logging. Do not route research participants through Open WebUI or AnythingLLM.

---

## 10. Future Expansion

This stack forms the foundation for LocoEnsayo production services and LocoBench benchmarking studies. It is also the PoC infrastructure for LocoPuente (locopuente.org) -- the Faculty-facing BridgeAI initiative.

The immediate upgrade target is the RTX 3090 24GB, which consolidates the entire stack onto a single card and eliminates the dual-GPU workload split. Once in place, Pulpo and Puente are freed for dedicated LocoBench benchmarking roles.

A planned LocoBench image generation study will benchmark SD 1.5 and SDXL across all available GPU tiers at fixed parameters (prompt, seed, step count, resolution) to map the floor of local image generation performance on consumer hardware -- following the same methodology as the LLM inference benchmarking work.

The OpenAI API-compatible design means any component can be swapped or upgraded independently without breaking integrations.

---

*Document maintained by Michael Borck, LocoLabo, Curtin University.*
