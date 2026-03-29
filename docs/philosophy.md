---
title: "Philosophy"
---

LocoPuente is an opinionated stack. The opinions come from a single idea:

**Conversation amplifies your thinking. Delegation amplifies the hallucinations.**

---

## The Core Formula

> Your expertise + AI's breadth = amplified thinking. The bottleneck is your thinking, not the model.

LLMs have read everything and experienced nothing. They interpolate patterns from training data -- they do not retrieve facts, reason from first principles, or understand context the way you do. This makes them extraordinary conversation partners and unreliable autonomous agents.

The LocoPuente stack is designed around this reality.

---

## Conversation, Not Delegation

| | Delegation | Conversation |
|---|---|---|
| **You ask** | "Write me a marketing plan" | "What are the weaknesses in my plan?" |
| **You get** | A finished artifact | A sharper understanding |
| **You lose** | The thinking | Nothing -- you gain capability |

Delegation produces outputs that sit in folders. Conversation produces understanding that compounds in your head.

The distinction matters because **conversation compounds and delegation does not**. Each conversation builds on the last -- your mental model gets richer, your questions get sharper, your judgment improves. Delegation gives you a deliverable and leaves your thinking exactly where it was.

This is why the LocoPuente stack is chat-first. The primary interface is a conversation, not a generation pipeline.

---

## The Decision Framework

Not all tasks are equal. The risk of AI involvement depends on two dimensions: the size of the task and the precision required.

| | Small task | Large task |
|---|---|---|
| **Average precision** | Sweet spot | Plausible but brittle |
| **Precise requirements** | Workable with verification | Danger zone |

Small tasks at average precision -- brainstorming, ideation, drafting, exploring alternatives -- are where AI shines. The outputs are good enough to be useful and small enough to verify. This is the conversational sweet spot.

Large tasks requiring precision -- legal documents, medical advice, financial analysis, production code -- are where delegation becomes dangerous. The model's confidence does not correlate with its correctness, and the stakes of being wrong are high.

Local small models are naturally suited to the sweet spot. They are less likely to produce convincingly wrong output at scale, and their constraints encourage the human to stay in the loop.

---

## Why Agents Require Caution

Agentic AI -- systems that autonomously plan, execute, and iterate in loops -- is an active research area in the lab (see [LocoAgente](https://locoagente.org)). The research is important. The deployment requires caution.

**Agentic drift** is the compounding of errors across multi-step autonomous loops. A model that is 90% accurate per turn is only 59% accurate over five turns. At 80% per turn, five steps gives you 33% accuracy. Small local models are less reliable per step than frontier models, and the errors compound faster.

More fundamentally, agents bypass the human thinking that makes AI useful. When you delegate a multi-step task to an agent, you get an output. You do not get the understanding that would have come from working through those steps in conversation. The agent did the thinking; you just received the result.

This is not a blanket rejection of agents. LocoAgente is studying exactly where the capability floor is and which scaffolding strategies make small-model agents viable. But for the LocoPuente stack -- designed for learning, professional development, and research -- the default mode is conversation with a human in the loop at every step.

---

## Practical Habits

These habits operationalise the philosophy:

**AI Last** -- use AI where it adds value you cannot easily generate yourself. Solve what you can with conventional tools first (search engines, calculators, linters, test harnesses), then bring AI to the parts that genuinely benefit from its breadth. This naturally scopes problems to where small models excel.

**VET** -- Verify, Explain, Test. Before acting on any AI output: verify the claims, explain the reasoning in your own words (if you cannot, you do not understand it), and test the output against reality. If it passes all three, use it. If not, the conversation continues.

**RTCF** -- Role, Task, Context, Format. One prompt, one job. Give the model a role ("You are a security auditor"), a task ("Review this access control logic"), context ("This runs on a shared campus server"), and format ("List vulnerabilities as a numbered checklist"). Structured prompts produce structured outputs.

**Two-Chat Workflow** -- separate thinking from building. Use one conversation to explore, brainstorm, and decide. Use a second conversation to execute. Mixing exploration and execution in a single thread produces muddled outputs and muddled thinking.

---

## Cognitive Traps

Three traps to watch for when working with AI:

**Gell-Mann Amnesia** -- you read an AI response about something you know well, spot the errors, correct them -- and then trust the next response about something you know less well. The model's reliability did not change between topics. Your ability to detect errors did.

**The Sycophancy Trap** -- LLMs are trained to be agreeable. If you state a position and ask the model to evaluate it, it will tend to agree. This feels like validation but it is not. Deliberately ask the model to argue against your position. The disagreement is more valuable than the agreement.

**AI Dismissal Fallacy** -- rejecting an idea solely because AI was involved in producing it. If a conversation with AI helped you reach a genuine insight, the insight is yours. The origin of the prompt does not determine the quality of the thinking.

---

## The Transparency Test

> Would you put your name on this and explain exactly how you produced it? If yes, you are using AI well. If no, something has gone wrong.

---

## Further Reading

These ideas are developed in full in *Conversation, Not Delegation: A Practical Guide to AI-Assisted Thinking* -- available online at [books.borck.education](https://books.borck.education).

The book provides the conceptual framework behind the LocoPuente stack's design decisions. The stack is the implementation; the book is the argument for why it is built this way.

---

*The output is a byproduct. The thinking is the point.*
