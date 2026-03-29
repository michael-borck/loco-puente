---
title: "Proof of Concept"
---

The LocoPuente PoC is running today on two consumer GPUs already in the LocoLabo fleet. This is not a simulation. These machines are running the full stack.

---

## Hardware

| | GPU 0 (Primary) | GPU 1 (Secondary) |
|---|---|---|
| **Machine** | Pulpo | Puente |
| **Card** | NVIDIA RTX 3060 | NVIDIA RTX 2060 Super |
| **VRAM** | 12 GB GDDR6 | 8 GB GDDR6 |
| **Bandwidth** | 360 GB/s | 448 GB/s |
| **CUDA Compute** | 8.6 | 7.5 |
| **Role** | Primary LLM + image generation | Voice (TTS/STT) + secondary LLM |

The dual-GPU arrangement eliminates the sequential switching constraint of a single-GPU setup. All services run concurrently -- voice and LLM inference happen simultaneously on separate cards.

---

## VRAM Budget

### GPU 0 -- Pulpo, RTX 3060 12 GB

| Service | Model | VRAM |
|---|---|---|
| Ollama instance 0 | Llama 3.1 8B Q4_K_M | ~5 GB |
| ComfyUI (SDXL) | SDXL 1.0 base | ~6.5 GB |
| **LLM only** | | **~5 GB** |
| **Image gen only** | | **~6.5 GB** |
| **LLM + image gen** | | **~11.5 GB -- tight, not recommended concurrently** |

### GPU 1 -- Puente, RTX 2060 Super 8 GB

| Service | Model | VRAM |
|---|---|---|
| Speaches STT | Whisper base/small | ~0.5 GB |
| Speaches TTS | Kokoro 82M | ~0.2 GB |
| Ollama instance 1 | Mistral 7B / Phi-3 Mini Q4 | ~4.5 GB |
| **Total concurrent** | | **~5.2 GB -- comfortable headroom** |

---

## PoC Capabilities

| Capability | Tool | GPU | Status |
|---|---|---|---|
| LLM chat -- general | Open WebUI + Ollama | Pulpo | Ready |
| LLM chat -- secondary | Open WebUI + Ollama | Puente | Ready |
| Web search in chat | Open WebUI + SearXNG | -- | Ready |
| Cited AI web search | Perplexica + SearXNG | Pulpo | Ready |
| Research nudge intervention | Custom chat | Pulpo | Ready |
| Domain RAG chatbot | AnythingLLM | Pulpo | Ready |
| Voice input (STT) | Speaches + Whisper | Puente | Ready |
| Voice output (TTS) | Speaches + Kokoro | Puente | Ready |
| Research assistant + podcast | Open Notebook AI | Pulpo | Ready |
| Image generation (in-chat) | Open WebUI + ComfyUI | Pulpo | Ready |
| Image generation (direct UI) | ComfyUI | Pulpo | Ready |
| PDF tools | Stirling PDF | -- | Ready |
| Collaborative whiteboard | Excalidraw | -- | Ready |
| Citation + writing check | CiteSight | External | Ready |
| **Voice + LLM concurrent** | **All services** | **Both cards** | **Ready** |

---

## Known Constraints

- LLM inference and SDXL image generation on Pulpo should not run simultaneously -- both together approach the 12 GB ceiling. In practice, Ollama unloads after inactivity before image generation is triggered.
- Puente's 8 GB VRAM is sufficient for voice + secondary LLM but cannot run SDXL. Image generation stays on Pulpo only.
- System RAM should be 32 GB minimum to avoid model paging to disk.
- The custom chat tool is the only interface with research consent and logging. Do not route research participants through other interfaces.

---

## The Cost Argument

The PoC hardware costs less than a year of commercial AI subscriptions for a small team. Two secondhand consumer GPUs. Running the full stack. Today.
