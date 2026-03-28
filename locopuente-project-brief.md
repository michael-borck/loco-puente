# LocoPuente

**Domain:** locopuente.org  
**Parent:** LocoLabo (locolabo.org)  
**Status:** Active  
**Lead:** Michael Borck, School of Marketing and Management, Curtin University

---

## Tagline

*Where the research meets the student.*

---

## One-Line Description

LocoPuente is the deployment layer of LocoLabo -- a student-facing local AI service that bridges the digital divide by bringing equitable, privacy-first AI access to every student, regardless of what they can afford.

---

## The Problem

Some students have access to powerful AI tools. Some do not. The difference is not aptitude or motivation. It is money.

Students who can afford a monthly subscription to a premium AI service have a genuine academic advantage over those who cannot. That gap is growing. LocoPuente exists to close it.

---

## What LocoPuente Is

LocoPuente is not a research project. It is where the research becomes real.

Every other project in the LocoLabo family asks the same question from a different angle: what can local AI actually do on modest hardware? LocoPuente takes those answers and turns them into something a student can open in a browser on a Tuesday afternoon.

The name is deliberate. *Puente* is Spanish for bridge -- consistent with the LocoLabo naming family, and accurate about the mission. LocoPuente bridges the gap between students who can afford frontier AI tools and those who cannot, using infrastructure the University owns and controls.

---

## What It Provides

A single on-campus server running a suite of locally hosted AI services, accessible to all students on the university network. No subscription fees. No data leaving the institution. No dependency on external providers.

| Service | What Students Get |
|---|---|
| AI Chat Interface | A chat experience comparable to commercial tools, designed to encourage critical thinking rather than passive use |
| Voice Interaction | Speak to the system, hear responses. Fully local speech-to-text and text-to-speech |
| Research and Notes | An AI-powered environment for reading, annotating, and synthesising sources |
| Image Generation | Generate images for presentations, projects, and creative work |
| API Access | For students building their own tools as part of assessed work or personal projects |
| Embedded Unit Assistants | AI support embedded directly within course platforms, tailored to specific unit content |
| Rehearsal Environments | Simulated professional organisations where students practice before the stakes are real |

---

## The Deployment Layer

LocoPuente is the convergence point for the entire LocoLabo research programme. Each sibling project contributes a layer to what students experience.

```
LocoPuente
├── Infrastructure layer  <--  LocoBench + LocoConvoy
├── Intelligence layer    <--  LocoLLM + LocoAgente
└── Experience layer      <--  LocoEnsayo
```

### LocoBench feeds the infrastructure decisions

LocoBench maps the floor of local LLM inference across every consumer GPU VRAM tier. That research answers the question every deployment starts with: what is the minimum viable hardware for a student-facing service? LocoPuente PoC deployments are essentially LocoBench findings applied to a real environment, validating benchmarks under genuine academic load.

### LocoConvoy handles concurrent load

When fifty students hit the service simultaneously, single-GPU inference becomes a bottleneck. LocoConvoy's research into multi-GPU parallelism on consumer PCIe hardware, load balancing, and Mixture of Agents architectures feeds directly into LocoPuente's capacity planning and scaling decisions.

### LocoLLM provides the intelligence layer

Rather than routing every student request through one large model, LocoLLM's swarm of small specialist models behind a smart router delivers more efficient, more targeted responses at lower VRAM cost. As LocoPuente scales, LocoLLM is the architecture that makes it affordable.

### LocoAgente powers the sophisticated tools

The Study Buddy, the Curriculum Explainer, the research assistant that can read a PDF and generate a structured summary -- these require more than single-turn chat. LocoAgente's research into agentic scaffolding on small models is what makes these tools viable without frontier hardware.

### LocoEnsayo supplies the experiences

LocoEnsayo builds AI-populated rehearsal environments for professional education. In LocoPuente, those environments become the richest student-facing experiences on offer -- simulated organisations, role-play scenarios, virtual client meetings. The research and the deployment are the same system.

---

## Proof of Concept

The LocoPuente PoC runs on two consumer GPUs already in the LocoLabo fleet.

| Machine | GPU | Role |
|---|---|---|
| Puente | RTX 2060 Super 8GB | Voice services (TTS/STT), secondary LLM |
| Pulpo | RTX 3060 12GB | Primary LLM inference, image generation |

This is not a simulation. These machines are running the full stack today. The PoC demonstrates that the BridgeAI service model works on hardware that costs less than a single semester of commercial AI subscriptions for a cohort of students.

**Stack running on PoC hardware:**

| Service | Tool | GPU |
|---|---|---|
| LLM inference (primary) | Ollama | RTX 3060 |
| LLM inference (secondary) | Ollama | RTX 2060 Super |
| Voice STT/TTS | Speaches + Whisper + Kokoro | RTX 2060 Super |
| Chat interface | Open WebUI | -- |
| Research and notes | Open Notebook AI | -- |
| Image generation | ComfyUI (SD 1.5, SDXL) | RTX 3060 |

All services expose OpenAI-compatible APIs. All run without internet access. All student data stays on the machine.

---

## Scale Target

The PoC demonstrates the model. The scale target is a single Apple M3 Ultra (512 GB unified memory), which runs the full stack for 50 to 100 concurrent users with comfortable headroom, on a machine the institution owns outright.

The PoC to M3 Ultra transition is not a rebuild. It is a hardware upgrade. The software stack, the architecture, and the operational model carry forward unchanged.

---

## Relationship to BridgeAI

BridgeAI is the name this initiative carries in Faculty and institutional conversations. LocoPuente is its identity within the LocoLabo research programme.

Same project. Two audiences. One bridge.

---

## Philosophy

LocoLabo maps the floor of what local AI can do because most people live there and nobody is documenting it honestly.

LocoPuente takes the floor and builds something on it.

The students who need this most are not the ones with ChatGPT Plus subscriptions. They are the ones who have been quietly making do without. LocoPuente is built for them.

---

## Site Structure (for Claude Code)

```
locopuente.org/
├── index          Hero, tagline, one-line mission
├── /about         The problem, the solution, the philosophy
├── /projects      How LocoLabo projects converge here (diagram)
├── /services      What students get (service table)
├── /poc           Proof of concept -- hardware, stack, current status
├── /roadmap       PoC to M3 Ultra to Faculty scale
└── /contact       Michael Borck, SoMM, Curtin
```

**Design notes for Claude Code:**
- Match locolabo.org visual style for consistency across the project family
- Emoji project icons consistent with locolabo.org (bridge emoji for LocoPuente: 🌉)
- Dark theme preferred
- Convergence diagram (the three-layer architecture) should render as a visual, not a code block
- Mobile responsive
- No external dependencies -- static site, GitHub Pages hosted
- Tone: plain, direct, purposeful. No corporate AI hype language.

---

*LocoPuente is a LocoLabo initiative, School of Marketing and Management, Curtin University, Perth, Western Australia.*
