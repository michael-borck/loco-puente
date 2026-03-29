---
title: "Student Services"
---

A single on-campus server. No subscriptions. No data leaving campus. Eight tools that every student can use.

:::tip[No subscription required]
Every service listed here runs on hardware the university owns. Students access them through a browser on the campus network. There is no account to create, no credit card to enter, and no data sent to any external provider.
:::

---

## What Students Get

| Service | What It Does |
|---|---|
| **AI Chat Interface** | A chat experience comparable to commercial tools, designed to encourage critical thinking rather than passive use |
| **Voice Interaction** | Speak to the system, hear responses. Fully local speech-to-text and text-to-speech |
| **Research and Notes** | An AI-powered environment for reading, annotating, and synthesising sources. Transforms research into podcasts |
| **Image Generation** | Generate images for presentations, projects, and creative work. Multiple model tiers from fast drafts to high quality |
| **API Access** | For students building their own tools as part of assessed work or personal projects. OpenAI-compatible endpoints |
| **Embedded Unit Assistants** | AI support embedded directly within course platforms, tailored to specific unit content and readings |
| **Rehearsal Environments** | Simulated professional organisations where students practise audits, interviews, negotiations, and client interactions before the stakes are real |
| **Coding Assistance** | Connect your editor to the local LLM. VS Code with Continue, CLI tools like OpenCode, or Claude Code with local models |

---

## AI Chat

The primary interface. Students interact with local LLMs through [Open WebUI](https://openwebui.com) -- a full-featured chat interface with conversation history, multi-model switching, voice input/output, image generation, and web search. Comparable to commercial tools, running entirely on campus hardware.

For research-focused work, [Perplexica](https://github.com/ItzCrazyKns/Perplexica) provides Perplexity-style answers with inline source citations and an academic search mode that prioritises scholarly sources.

---

## Voice

Fully local speech-to-text (Whisper) and text-to-speech (Kokoro) via [Speaches](https://speaches.ai). Integrated natively into Open WebUI -- students speak, the system listens, processes, and responds audibly. No audio data leaves the machine.

---

## Research and Notes

[Open Notebook AI](https://www.open-notebook.ai) is a research assistant that ingests PDFs, links, YouTube videos, and text documents. Students can annotate, synthesise, and generate structured summaries. The platform can transform research notes into podcasts -- useful for revision and accessibility.

---

## Image Generation

[ComfyUI](https://github.com/comfyanonymous/ComfyUI) provides local image generation. Simple requests go through Open WebUI's in-chat image generation (students never need to open ComfyUI directly). Students who want node-based workflow control, ControlNet, LoRAs, or advanced pipelines access ComfyUI directly in the browser.

---

## Unit Assistants

[AnythingLLM](https://anythingllm.com) powers unit-specific RAG chatbots embedded in Blackboard. Each unit gets its own document workspace -- the ISYS6020 assistant only knows ISYS6020 content. Students ask questions about readings, assessments, and course material and get answers grounded in the unit's actual documents.

---

## Rehearsal Environments

Powered by [LocoEnsayo](https://locoensayo.org), these are AI-populated organisations that students can interrogate, interview, audit, and negotiate with. Each persona has a backstory, a role, and information constraints. The scenario is not a quiz. It is a rehearsal.

Currently deployed: **CloudCore Networks** (IT services firm for security audits and systems analysis), **Pinnacle Tours** (hospitality and tourism), and **TalkBuddy** (high-stakes conversation practice).

---

## Coding Assistance

The same Ollama instances that power the chat interface are accessible from your code editor via OpenAI-compatible API endpoints. No separate setup needed -- point your tool at the local Ollama URL and start coding.

**Editor integrations:**
- **[Continue](https://continue.dev)** -- VS Code / JetBrains extension. Autocomplete, chat, and inline editing backed by local models. The most mature option.
- **[OpenCode](https://opencode.ai)** -- Terminal-based coding assistant. Lightweight, fast, connects to any OpenAI-compatible endpoint.
- **[Claude Code](https://claude.ai/claude-code)** -- Anthropic's CLI tool. Can be configured to use local models via OpenAI-compatible endpoints for privacy-sensitive work.
- **[Claude Desktop](https://claude.ai)** -- Can connect to local Ollama via MCP (Model Context Protocol) for a desktop AI assistant backed by your local stack.

:::caution[A note on agents]
Agentic coding tools (tools that autonomously write, run, and iterate on code in loops) are technically possible with local models. We recommend caution.

**Agentic drift** is the compounding of errors across multi-step loops. A model that is 90% accurate per turn is only 59% accurate over five turns. Small local models amplify this -- they are less reliable per step than frontier models, and the errors compound faster.

More fundamentally, agentic delegation bypasses the thinking that makes AI useful for learning. You get code in a folder; you don't get understanding in your head. The LocoPuente stack is designed for **conversation, not delegation** -- AI that amplifies your thinking rather than replacing it. See the [Philosophy](philosophy) page for more on this distinction.

Use local models as a **coding conversation partner**: explain your approach, ask it to review your logic, brainstorm alternatives, generate test cases. That interaction makes you a better developer. Handing it autonomous control does not.
:::

---

## Productivity Tools

Beyond AI services, LocoPuente includes tools students use daily:

- **[Stirling PDF](https://stirlingtools.com)** -- merge, split, compress, OCR, annotate, and convert PDFs. Every student needs PDF tools; no data leaves the machine.
- **[Excalidraw](https://excalidraw.com)** -- collaborative whiteboard and diagramming. Group projects, case study mapping, business process diagrams.
- **[CiteSight](https://citesight.eduserver.au)** -- citation verification and writing quality checker. Pre-submission check that catches citation errors and AI-generated writing patterns before they cost marks.
