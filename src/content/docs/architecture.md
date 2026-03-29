---
title: "Architecture"
---

LocoPuente is the convergence point for the entire LocoLabo research programme. Five sibling projects each contribute a layer to what users experience.

---

## Three Layers, Five Projects

| Layer | Projects | What They Contribute |
|---|---|---|
| **Infrastructure** | [LocoBench](https://locobench.org) + [LocoConvoy](https://lococonvoy.org) | Hardware selection, capacity planning, multi-GPU scaling |
| **Intelligence** | [LocoLLM](https://locollm.org) + [LocoAgente](https://locoagente.org) | Routed specialist models, agentic tools, scaffolded reasoning |
| **Experience** | [LocoEnsayo](https://locoensayo.org) | AI-populated rehearsal environments, simulation scenarios |

---

## How Each Project Feeds LocoPuente

### LocoBench feeds the infrastructure decisions

LocoBench maps the floor of local LLM inference across every consumer GPU VRAM tier. That research answers the question every deployment starts with: what is the minimum viable hardware for a production service? LocoPuente PoC deployments are essentially LocoBench findings applied to a real environment, validating benchmarks under genuine production load.

### LocoConvoy handles concurrent load

When fifty users hit the service simultaneously, single-GPU inference becomes a bottleneck. LocoConvoy's research into multi-GPU parallelism on consumer PCIe hardware, load balancing, and Mixture of Agents architectures feeds directly into LocoPuente's capacity planning and scaling decisions.

### LocoLLM provides the intelligence layer

Rather than routing every request through one large model, LocoLLM's swarm of small specialist models behind a smart router delivers more efficient, more targeted responses at lower VRAM cost. As LocoPuente scales, LocoLLM is the architecture that makes it affordable.

### LocoAgente powers the sophisticated tools

The Study Buddy, the Curriculum Explainer, the research assistant that can read a PDF and generate a structured summary -- these require more than single-turn chat. LocoAgente's research into agentic scaffolding on small models is what makes these tools viable without frontier hardware.

### LocoEnsayo supplies the experiences

LocoEnsayo builds AI-populated rehearsal environments for professional education. In LocoPuente, those environments become the richest user-facing experiences on offer -- simulated organisations, role-play scenarios, virtual client meetings. The research and the deployment are the same system.

---

## API-First Design

All core AI services expose OpenAI-compatible APIs, enabling interoperability across the stack.

| Endpoint | Provided By | Consumed By |
|---|---|---|
| `/v1/chat/completions` | Ollama | Open WebUI, Perplexica, AnythingLLM, Open Notebook, Custom chat |
| `/v1/audio/transcriptions` | Speaches | Open WebUI, Open Notebook |
| `/v1/audio/speech` | Speaches | Open WebUI, Open Notebook |
| Image generation API | ComfyUI | Open WebUI (in-chat images), direct UI |
| Web search API | SearXNG | Open WebUI, Perplexica |

This means any component can be swapped or upgraded independently without breaking integrations.
