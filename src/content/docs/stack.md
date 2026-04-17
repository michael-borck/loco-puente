---
title: "Software Stack"
---

Every tool in the LocoPuente minimal PoC, its role, its port, and how it connects. One workstation, one GPU, three backend services, one tool-augmented general chat interface, and three companion research/study front ends.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                           Front-End Apps                                │
│                                                                         │
│  OpenWebUI                     Vane          DeepTutor    OpenNotebook  │
│  (general chat; augmented by   (deep         (research +  (podcasts,    │
│   ComfyUI, Speaches, and       research)      tutoring)    quizzes,     │
│   OpenTerminal as tools)                                   notes)       │
└──┬──────────────────────────────┬──────────────┬────────────┬─────────┘
   │                              │              │            │
   ▼                              ▼              ▼            ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    Backend Services on the RTX 3090                     │
│                                                                         │
│   Ollama :11434         ComfyUI :8188         Speaches :8000            │
│   (LLM, OpenAI API)     (image generation)    (STT + TTS)               │
│                                                                         │
│   OpenTerminal          (coding + terminal tool consumed by OpenWebUI)  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼─────────────────────────────────────┐
│  Puente -- Ryzen 5 2600                                                 │
│  NVIDIA RTX 3090 24 GB GDDR6X  (single card, all services)              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Backend Services (on RTX 3090)

### Ollama -- LLM Inference

OpenAI-compatible REST API on port 11434. Model format: GGUF (via llama.cpp). Deployed as a native systemd service.

| Model | Size | VRAM | Use case |
|---|---|---|---|
| Llama 3.1 8B Q4_K_M | ~5 GB | ~5 GB | General purpose default |
| Qwen 2.5 7B Q4_K_M | ~5 GB | ~5 GB | Strong reasoning |
| Llama 3.1 13B Q4_K_M | ~8 GB | ~8 GB | Higher-quality responses |
| 30B-class Q4 | ~18 GB | ~18 GB | Large-model inference when image gen is idle |

### ComfyUI -- Image Generation

Local image generation on port 8188. Deployed as a native Python venv service. Dual role: backend API (called by OpenWebUI for in-chat images) and direct UI (for node-based workflows, ControlNet, LoRAs).

| Model | VRAM | Resolution | Notes |
|---|---|---|---|
| SD 1.5 | ~4 GB | 512x512 | Fast baseline |
| SDXL 1.0 base + refiner | ~8-10 GB | 1024x1024 | Default production quality |
| FLUX.1 Schnell Q4 | ~8 GB | 1024x1024 | Modern generator, fast variant |
| FLUX.1 Dev GGUF Q8 | ~12 GB | 1024x1024 | Near-full quality |
| FLUX.1 Dev FP16 | ~16-24 GB | 1024x1024 | Full quality, run standalone |

### Speaches -- Audio

OpenAI Audio API-compatible STT and TTS on port 8000. STT via faster-whisper, TTS via Kokoro (primary) with Piper fallback. Deployed as a Docker container with GPU passthrough.

---

## Front-End Apps

### OpenWebUI -- The General-Purpose Chat Interface

OpenWebUI is the day-to-day chat interface. Text chat, conversation history, multi-model switching -- plus three tool integrations that give it functional equivalence with commercial chat UIs:

| Tool | Purpose | Backend |
|---|---|---|
| **Speaches** | Voice in (STT) and voice out (TTS) in-chat | Speaches :8000 |
| **ComfyUI** | In-chat image generation | ComfyUI :8188 |
| **OpenTerminal** | Coding assistant with shell / editor-style interaction | Ollama :11434 |

The design choice matters: OpenTerminal is wired in as an OpenWebUI tool, not as a separate window the student has to learn. Coding, image generation, and voice live next to the chat they're being used from.

Deployed as a Docker container on port 3000.

### Vane -- Deep Research

Deep-research agent: multi-step search, synthesis, citation. Consumes Ollama as its reasoning engine.

### DeepTutor -- Research and Tutoring

Research-and-tutoring assistant for students. Walks through topics, explains concepts, checks understanding. Consumes Ollama.

### OpenNotebook -- Podcasts, Quizzes, Notes

A NotebookLM-style research tool without the video side. Transforms uploaded sources (PDFs, links, YouTube transcripts, TXT, PPT) into:

- Structured notes
- Quizzes for self-testing
- Conversational podcasts (generated via Ollama + Speaches)

Deployed as a Docker container on port 8080.

---

## Network and Ports

| Service | Port | GPU | Notes |
|---|---|---|---|
| Ollama | 11434 | RTX 3090 | Primary LLM API; backend for all front-end apps and OpenTerminal |
| ComfyUI | 8188 | RTX 3090 | Image generation UI + API (called by OpenWebUI as a tool) |
| Speaches | 8000 | RTX 3090 | TTS/STT API (called by OpenWebUI as a tool) |
| OpenWebUI | 3000 | -- | General chat + voice + images + coding (tool-augmented) |
| OpenTerminal | (per deployment) | -- | Coding and terminal tool wired in as an OpenWebUI tool |
| Vane | (per deployment) | -- | Deep research |
| DeepTutor | (per deployment) | -- | Research and tutoring |
| OpenNotebook | 8080 | -- | Podcasts, quizzes, notes |

All services bind to localhost by default. For LAN access, bind to the workstation's local IP. No public internet exposure without authentication.

---

## Deployment

| Method | Services |
|---|---|
| **systemd** | Ollama |
| **Python venv** | ComfyUI |
| **Docker Compose** | Speaches, OpenWebUI, OpenNotebook |
| **OpenWebUI tool config** | OpenTerminal registered as a tool/service used by OpenWebUI |
| **App-specific** | Vane, DeepTutor (each per its project's deployment guide) |

---

## Broader Ecosystem

Puente's Ollama and Speaches endpoints also serve the wider LocoLabo app ecosystem -- the Keep Asking research chat tool, TalkBuddy, StuddyBuddy, Career Compass, and the LocoEnsayo rehearsal chatbots. Those are documented in their own project docs. They are not part of the minimal PoC demonstration scope; they are downstream consumers of the same backend.
