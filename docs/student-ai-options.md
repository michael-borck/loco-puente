# Using AI in this unit: your options

You have four ways to use an AI assistant for this unit. All are legitimate.
Pick the one that fits your hardware, your budget, and how private you need your work
to be — and understand what you are trading away in each case.

There is no option that is simultaneously free, private, and best-in-class. That
trade-off is the point, and it is worth understanding.

If you only read one line: **use Option 4 (NotebookLM) when you are working from
readings I have given you**, and one of the others when you are thinking out loud.

| | Cost | Install | Your data goes to | Best model | Good for |
|---|---|---|---|---|---|
| **1. My server** | Free | None (account needed) | My university machine | `qwen3.5:9b` | Everyday use, no setup |
| **2. Your laptop** | Free | One app | Nowhere | Whatever fits your RAM | Privacy, offline |
| **3. Paid provider** | ~$30/mo | None | The provider | Frontier | Hardest problems |
| **4. NotebookLM** | Free | None | Google | Gemini | Working from readings |

---

## Option 1 — Use my server (easiest, best local model)

**Go to <https://chat.eduserver.au>.** Nothing to install. You will need an account —
ask me and I will set one up for you.

This runs on a machine I administer at the university. The models run locally on that
machine; your conversations are not sent to any AI company.

| | |
|---|---|
| **Cost** | Free |
| **Install** | None — it's a website |
| **Account** | Yes — ask me |
| **Best model** | `qwen3.5:9b` (a 9-billion-parameter model) |
| **Privacy** | Your prompts stay on university hardware, but **I can see usage** |
| **Needs** | Network access |

**Choose this if** you want the best local model available to you, or your laptop can't
run a model at all.

**Be aware:** it is a shared machine. If everyone submits at once it will be slow. It is
not a good idea to rely on it an hour before a deadline.

---

## Option 2 — Run a model on your own laptop (most private)

Install one app; it downloads and runs models locally. Nothing leaves your machine, and
it works offline.

### LM Studio — <https://lmstudio.ai> ← recommended

Free for personal *and* commercial use (they dropped the commercial licence requirement
in July 2025). So if you later use it in a paid job, you're still fine.

### Msty — <https://msty.ai>

Comparable app, also free to download, and the easiest of the two to set up.

Msty's **Knowledge Stacks** are the closest thing to NotebookLM (Option 4) that runs
entirely on your own machine: upload your readings, and the model answers from them.
If you like what NotebookLM does but don't want to hand your sources to Google, this is
the option. It is included in the free tier.

> **Licence caution.** Msty's free licence covers *"your own, private, non-commercial
> purposes (e.g. taking notes, doing research)."* It explicitly excludes *"use ... for
> the exercise of your trade or profession for which you are compensated."*
> Coursework is fine. If you use it in **paid work**, you need a licence (Aurum,
> $149 USD/yr). LM Studio has no such restriction.

### What your laptop can actually run

This is the part people get wrong. A model needs to fit in memory — ideally GPU memory
(VRAM), otherwise it runs on the CPU and is very slow.

| Your hardware | Realistic model | Honest verdict |
|---|---|---|
| No discrete GPU, 8 GB RAM | `qwen3.5:2b` | Fine for drafting and summarising |
| No discrete GPU, 16 GB RAM | `qwen3.5:4b` | Usable thinking partner |
| GPU with 8 GB VRAM | `qwen3.5:9b` | Same as my server |
| Apple Silicon, 16 GB+ | `qwen3.5:9b` | Works well — unified memory helps |

A 2B model is **not** a small version of a 9B model. It will lose the thread of a long
argument, and it will state wrong facts confidently. That may be acceptable — see the
note on what these models are *for*, below.

| | |
|---|---|
| **Cost** | Free |
| **Install** | One app |
| **Privacy** | Total. Works on a plane. |
| **Trade-off** | Limited by your hardware |

---

## Option 3 — Pay a provider (best models, your data leaves)

A subscription to Claude, ChatGPT, Gemini or similar (~AU$30/month), or bring-your-own-key
(BYOK) API access where you pay per use.

The frontier models are genuinely, substantially better than anything you or I can run
locally. If you are doing serious work and can afford it, this is the strongest option.

**BYOK is often cheaper than a subscription** if you use it occasionally. Both LM Studio
and Msty can connect to a paid API with your own key, so you can keep one interface and
switch between a local model and a paid one.

| | |
|---|---|
| **Cost** | ~AU$30/month, or per-token for BYOK |
| **Privacy** | Your prompts go to the provider. Read their data-retention policy. |
| **Quality** | Best available |

**You are never required to pay for anything in this unit.** Options 1, 2 and 4 are
sufficient to complete all assessed work.

---

## Option 4 — NotebookLM, for working *from sources*

**<https://notebooklm.google.com>** — free, needs a Google account.

This is a different kind of tool, and for a lot of coursework it is the right one.
You upload your sources — lecture notes, PDFs, papers, a website — and it will only
answer **from those documents**, with citations pointing back to the passage it used.

That grounding is the point. It makes fabricated facts far easier to catch, because
every claim comes with a link to where it supposedly came from. (Check the link. It is
still capable of misreading a source.)

### Free tier limits (as of 2026)

| | Free |
|---|---|
| Notebooks | 100 |
| Sources per notebook | 50 |
| Chat queries | 50 / day |
| Audio Overviews | 3 / day |

Audio Overviews generate a surprisingly good two-host podcast discussing your sources.
Useful on the bus. Not a substitute for reading them.

### Sign in with your university account, not personal Gmail

Google's own documentation states that free-tier data *"is not used to train NotebookLM
unless you provide feedback"* — and if you do give feedback, human reviewers may see the
full context.

**Google Workspace for Education accounts get stronger terms:** uploads, queries and
responses *"will not be reviewed by human reviewers even when you provide thumbs up or
down feedback, and will not be used to train AI models."*

So use your Curtin account.

| | |
|---|---|
| **Cost** | Free |
| **Install** | None — it's a website |
| **Privacy** | Your sources go to Google. Better terms on a university account. |
| **Best for** | Working from a fixed set of readings; literature review; revision |
| **Not for** | Open-ended thinking, coding, anything outside your uploaded sources |

**Choose this when** the answer should come from the readings rather than from the
model's memory. That is most of what a literature review is.

---

## Mixing options

These aren't exclusive. Both LM Studio and Msty can point at a *remote* model, so you can
install one of them and connect it to my server — your preferred interface, my hardware,
my larger model. Ask me if you want the endpoint details.

---

## What these models are for

For this unit, I want you using AI as a **thinking partner**, not as an answer machine:
to argue with, to draft against, to ask "what am I missing?"

That matters for your choice of model. Quantised local models — the compressed versions
that fit on consumer hardware — lose *factual precision* long before they lose
*conversational coherence*. A small local model will happily invent a citation. It will
still push back on a weak argument.

This makes a small local model a **worse oracle and a better interlocutor**. Which,
for our purposes, is the right way round. You cannot outsource the thinking to it, so
you have to do the thinking with it.

Whichever option you choose: **verify every fact, every citation, and every number.**
This applies to the frontier models too. They are more fluent, which makes their errors
harder to spot, not rarer.

---

## Academic integrity

Using AI is permitted in this unit. Passing off its output as your own unaided work is
not. Follow the university's policy and the unit outline. If in doubt, ask me — asking
is never the wrong move.
