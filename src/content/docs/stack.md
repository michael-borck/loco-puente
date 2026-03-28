---
title: "Software Stack"
---

Every tool in the LocoPuente stack, its role, its port, and how it connects.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            User Interfaces                               │
│                                                                          │
│  Custom Chat    Open WebUI   Perplexica   AnythingLLM   Open Notebook   │
│  (NBF Study)    (General)    (AI Search)  (Blackboard)  (Research)      │
│                                                                          │
│  ComfyUI        Stirling PDF   Excalidraw   CiteSight                   │
│  (Images)       (PDF Tools)    (Whiteboard)  (Citations)                │
└──┬──────────────────┬─────────────────────────────┬─────────────────────┘
   │                  │                              │
┌──▼──────────────────▼──────────┐  ┌───────▼─────┐  ┌─────▼─────┐
│  Ollama :11434 (GPU 0 / Pulpo) │  │  Speaches   │  │  SearXNG  │
│  Ollama :11435 (GPU 1 / Puente)│  │  :8000      │  │  :8888    │
└──┬─────────────────────────────┘  └───────┬─────┘  └─────┬─────┘
   │                                         │              │
┌──▼────────────────────┐  ┌────────────────▼──────────────▼──────┐
│  Pulpo                │  │  Puente                               │
│  RTX 3060 12GB        │  │  RTX 2060 Super 8GB                   │
│  Primary LLM + Images │  │  Voice + Secondary LLM                │
└───────────────────────┘  └───────────────────────────────────────┘
```

---

## Chat and Search Interfaces

| Tool | Purpose | Audience | Key Feature |
|---|---|---|---|
| Custom chat | NBF research / Keep Asking study | Research participants | Consent, exit survey, turn logging |
| Open WebUI | General student AI access | All students | Full-featured: voice, images, web search |
| Perplexica | Cited AI-powered web search | Research-focused students | Perplexity-style cited answers, academic mode |
| AnythingLLM | Unit-specific RAG chatbots | Students per unit | Embeds in Blackboard, per-unit document workspaces |

Open WebUI and Perplexica are complementary -- Open WebUI is the general AI assistant, Perplexica is specifically for "find me cited information from the web." Both share the same SearXNG instance as their search backend.

---

## Backend Services

### Ollama -- LLM Inference

Two instances, one per GPU, each exposing an OpenAI-compatible REST API.

| Instance | GPU | Port | Recommended Models |
|---|---|---|---|
| ollama-0 | RTX 3060 (Pulpo) | 11434 | Llama 3.1 8B Q4_K_M, Qwen2.5 7B |
| ollama-1 | RTX 2060 Super (Puente) | 11435 | Mistral 7B Q4_K_M, Phi-3 Mini |

### Speaches -- Voice

Local TTS and STT server on port 8000. OpenAI Audio API-compatible. STT via faster-whisper, TTS via Kokoro (primary) with Piper fallback. Integrated natively into Open WebUI.

### SearXNG -- Web Search

Shared private web search backend on port 8888. Aggregates 70+ search engines without tracking users or requiring API keys. One instance serves both Open WebUI and Perplexica.

### ComfyUI -- Image Generation

Local image generation on port 8188. Dual role as backend API (serving Open WebUI's in-chat image generation) and direct student UI (for advanced workflows).

| Model | VRAM | Resolution | Gen Time |
|---|---|---|---|
| SD 1.5 | ~4 GB | 512x512 | ~2 sec |
| SDXL 1.0 base | ~6.5 GB | 1024x1024 | ~15-20 sec |
| FLUX.1 Schnell Q4 | ~8 GB | 1024x1024 | ~30 sec |

---

## Network and Ports

| Service | Port | GPU | Notes |
|---|---|---|---|
| Ollama instance 0 | 11434 | Pulpo / RTX 3060 | Primary LLM API |
| Ollama instance 1 | 11435 | Puente / RTX 2060 Super | Secondary LLM API |
| Open WebUI | 3000 | -- | General student chat |
| Perplexica | 3001 | -- | Cited AI web search |
| AnythingLLM | 3002 | -- | Blackboard RAG chatbots |
| Speaches | 8000 | Puente / RTX 2060 Super | TTS/STT API |
| Open Notebook AI | 8080 | -- | Research, notes, podcast |
| Stirling PDF | 8089 | -- | PDF tools |
| ComfyUI | 8188 | Pulpo / RTX 3060 | Image generation |
| SearXNG | 8888 | -- | Shared search backend |
| Excalidraw | 3333 | -- | Collaborative whiteboard |
| CiteSight | external | -- | citesight.eduserver.au |

All services bind to localhost by default. For LAN access, bind to the workstation's local IP. No public internet exposure without authentication.

---

## Deployment

| Method | Services |
|---|---|
| **Docker Compose** | Open WebUI, Perplexica, AnythingLLM, Speaches, Open Notebook, Stirling PDF, SearXNG, Excalidraw |
| **systemd** | Ollama instance 0, Ollama instance 1 |
| **Python venv** | ComfyUI |
| **External** | Custom chat (chat.locolabo.org), CiteSight (citesight.eduserver.au) |
