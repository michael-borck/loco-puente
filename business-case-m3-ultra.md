# Business Case: Local AI Infrastructure for Equitable Student Access
**Prepared for:** Faculty of Business and Law, Curtin University
**Prepared by:** School of Marketing and Management
**Status:** Draft for Discussion
**Classification:** Internal

---

## Executive Summary

Right now, some of our students have access to powerful AI tools and some do not. The difference is not aptitude, motivation, or academic preparation. It is money.

Students who can afford a monthly subscription to a premium AI service have a genuine academic advantage over those who cannot. That gap is growing, and it runs directly against everything the Faculty stands for in terms of equity, access, and preparing all of our graduates for the world they are entering.

This proposal asks the Faculty to close that gap.

The solution is two purpose-built AI servers housed within Curtin's own infrastructure, giving every student in the Faculty access to AI capability equivalent to the commercial tools their wealthier peers are already using. No subscription fees. No data leaving the University. No dependency on external providers who can change their pricing at any time. Two machines rather than one means the service is always available, even during maintenance or hardware failure.

The total cost is approximately AUD $18,000 to $22,000, paid once. The equivalent commercial cloud service would cost that much every two to three months.

Critically, this is not a proposal to build something from scratch. The School of Marketing and Management has been running a version of this service for two years, on minimal hardware, across six units, serving hundreds of students per semester. The software stack is proven. The demand is proven. The team has the skills.

What is missing is the hardware to run the larger AI models that match commercial frontier tools in quality. The existing prototype demonstrates that the architecture works. The M3 Ultra proof of concept demonstrates that the *models* are good enough -- that open-source AI running locally can genuinely match the experience students currently pay for. That is a qualitatively different proposition, and it requires hardware with enough memory to run the same class of models that power ChatGPT and Claude.

The proposal has one immediate ask: funding for a proof of concept using two M3 Ultra machines, run as a structured pilot within the School of Marketing and Management. Every governance question, every cybersecurity concern, every data management question gets answered by a working machine that stakeholders can actually inspect, rather than a document they are asked to approve on faith.

The Faculty of Business and Law trains the next generation of business leaders. Those leaders will work in organisations shaped by AI. Giving all of our students, not just the ones who can afford it, the tools and the critical thinking skills to engage with AI on their own terms is not a technology project. It is a statement about what this Faculty believes.

---

## The Problem: AI Is Creating a Two-Tier Student Experience

Artificial intelligence tools have become a genuine academic advantage. Students with the means to pay for premium subscriptions to services like ChatGPT Plus, Claude Pro, or Gemini Advanced are accessing capabilities that are measurably better than free alternatives. Students without those means are not.

This is not a hypothetical concern. It is a digital divide playing out inside our classrooms right now, across every school in the Faculty.

At the same time, the University is actively promoting AI literacy as a graduate capability. We cannot in good conscience do that while leaving access to chance based on personal income. The question is not whether to provide equitable access, but how.

---

## Why Not Just Subsidise Student Subscriptions?

This is the obvious alternative and it deserves a direct answer before it becomes the default counter-argument.

Subsidising student subscriptions to commercial AI services would be cheaper in the short term and require no infrastructure investment. But it would also:

- Create permanent, ongoing financial dependency on external providers, with pricing subject to change at any time and entirely outside the University's control
- Send all student queries, all coursework interactions, and all generated content to servers operated by private companies under their own data governance frameworks, not Curtin's
- Give the University no capability of its own, only rented access to someone else's capability
- Provide nothing that can be customised to Curtin's curriculum, values, or academic integrity standards
- Offer no foundation for research, for building student-facing applications, or for developing the kind of applied AI expertise that distinguishes this Faculty

Subscription subsidies solve access today at the cost of sovereignty, capability, and long-term affordability. Local infrastructure solves access today and builds something the Faculty owns.

---

## The Proposed Solution: A Dedicated On-Campus AI Server

This proposal recommends the purchase and deployment of two Apple M3 Ultra workstations, each with 256 GB of unified memory, hosted on the Curtin network and made available to all students across the Faculty of Business and Law.

Two machines rather than one is a deliberate design choice. The 256 GB memory in each machine is more than sufficient to run the largest AI models relevant to student use cases, and the paired configuration delivers genuine benefits that a single, larger machine cannot: built-in redundancy (if one machine is down, the other keeps the service running), load balancing across concurrent users, and the operational confidence that comes from knowing the service does not depend on a single point of failure.

These machines would run a suite of AI services locally, entirely within Curtin's infrastructure. No student data would leave the University. No subscription fees would be charged to students. The capability on offer would be comparable, for the majority of student use cases, to the frontier commercial tools that only well-resourced students can currently access.

The Faculty of Business and Law is a natural home for this initiative. Business graduates will operate in AI-enabled workplaces. Equipping them with genuine AI capability, not just familiarity with commercial products they do not own or understand, is a curriculum imperative.

---

## Why This Specific Configuration?

The Apple M3 Ultra is not a luxury purchase. It is the minimum viable hardware for the task. And two of them is the minimum viable architecture for a service that needs to be reliable.

Running a large AI model well requires two things: enough memory to load the model, and fast enough memory bandwidth to run it responsively. Think of memory as the size of the desk you are working on, and bandwidth as how quickly you can move things around on it. You need both.

The M3 Ultra with 256 GB of unified memory meets both requirements comfortably for every AI model relevant to student use cases. The largest openly available models that are comparable in quality to the commercial frontier tools, for tasks including writing assistance, analysis, research support, and structured reasoning, fit well within 256 GB.

- **256 GB of memory per machine** is sufficient to run every realistic student-facing model at full quality. There is no student use case in this Faculty that requires a model too large for 256 GB.
- **The memory bandwidth** is what makes the experience responsive. A machine with lots of memory but slow bandwidth produces frustratingly slow responses. The M3 Ultra avoids this.
- **Two machines** means double the concurrent capacity, built-in failover, and the ability to update or maintain one machine without taking the service offline. This is not over-engineering; it is the standard expectation for any service that students are asked to rely on.

No other consumer or prosumer configuration currently matches this combination of capability, redundancy, and price. Cloud alternatives that match this capability cost significantly more over a three-to-five year horizon, as detailed below.

---

## What Would It Provide?

The server would host several services accessible to students on the Curtin network, whether on campus or connected via the University VPN.

| Service | What It Means for Students |
|---|---|
| **AI Chat** | A chat experience comparable to ChatGPT or Claude, with the ability to search the web and cite sources. Designed to encourage critical thinking rather than passive use |
| **Voice Interaction** | Speak to the system and hear responses. Fully local -- no audio data leaves the machine |
| **Research and Notes** | An AI-powered environment for reading, annotating, and synthesising sources. Can generate audio summaries from research notes |
| **Image Generation** | Generate images for presentations, projects, and creative work. Multiple quality levels from quick drafts to high resolution |
| **Coding Assistance** | AI-assisted coding for Information Systems students, integrated directly into their development tools |
| **Unit Assistants** | AI support embedded directly within Blackboard, tailored to specific unit content. A student asking about ISYS6020 gets answers grounded in ISYS6020 materials, not generic responses |
| **Rehearsal Environments** | AI-populated simulated organisations where students practise professional skills -- conducting audits, interviewing stakeholders, handling client negotiations -- before the stakes are real |
| **Productivity Tools** | PDF tools (merge, split, annotate), collaborative whiteboard for group work, and a citation checker that catches referencing errors before submission |
| **API Access** | For students in technical units who are building their own applications as part of assessed work |

All services run on two load-balanced machines. Students access them through a browser. There is nothing to install, nothing to subscribe to, and nothing that sends data outside the University.

---

## Security, Privacy, and Data Governance

**Data stays at Curtin.** Every conversation, every query, every generated image remains on machines physically located within Curtin's infrastructure. Nothing is sent to an external provider. This is a stronger data governance position than any subscription service can offer, regardless of contractual protections.

**Access is controlled by Curtin's existing systems.** The machines would sit on the Curtin network. Access to the Curtin network already requires a valid Curtin account, meaning only current students, staff, and VPN-connected Curtin community members can reach it, without requiring any additional login system.

**The machines can be hardened to meet Curtin's cybersecurity requirements.** Apple hardware runs a well-supported, enterprise-grade operating system. The services can be configured to log access, limit misuse, and comply with the University's existing policies. These are not theoretical commitments; they are standard configuration options for the software stack proposed.

**On authentication:** For a proof of concept, relying on Curtin network access as the authentication layer is sufficient and avoids the delays associated with integrating a new service into Curtin's Single Sign-On infrastructure. SSO integration is achievable at a later stage if required, but it is not a prerequisite for demonstrating value.

**On model licensing:** Only AI models with licences appropriate for institutional, non-commercial educational use would be deployed. This is a condition of deployment, not an afterthought, and is verifiable before any model is made available to students.

---

## Data Storage: Practical Limits by Design

Retaining every conversation, notebook, and generated image for every student indefinitely would create a genuine storage problem. This proposal does not do that.

Storage would be managed through simple, per-user limits set at the outset:

| Content Type | Limit | Rationale |
|---|---|---|
| **Notebooks** | 10 per student | A full-time student carries four units per semester: one notebook per unit, one for a current assignment, and a small buffer |
| **Saved conversations** | 5 most recent | Enough for continuity within a project; older conversations expire automatically |
| **Generated images** | 5 saved per student | Sufficient for active work; students download what they want to keep |

These are not arbitrary restrictions. They reflect realistic usage patterns and they keep the storage footprint of the service predictable and manageable across both machines.

Students who need to retain more would download or export their work, which is standard practice in every other tool they use. The service is a workspace, not an archive.

This approach also has a governance benefit: limiting retention reduces the data governance surface area considerably. There is less to protect, less to audit, and less to manage if a student account is ever closed or disputed.

---

## A Pedagogically Designed Interface, Not Just an Access Tool

One of the most significant advantages of running a locally controlled service is that the University owns the interface. That ownership matters more than it might initially appear.

Commercial AI tools are designed to maximise engagement. They prompt users with suggestions like "would you like me to expand on this?" or "shall I write that for you?", mechanisms borrowed directly from social media, optimised to keep users returning and to deepen dependency. These are deliberate design choices that serve the provider's interests, not the student's learning.

This service can do the opposite.

Because the interface is fully configurable, it is possible to append prompts at the end of every AI response that nudge students toward critical engagement rather than passive acceptance. Instead of "shall I do more for you?", the interface can ask:

- *"What assumptions is this response making?"*
- *"Can you find a source that supports or challenges this?"*
- *"How would you rewrite this in your own words?"*
- *"Does this response change your original thinking? Why or why not?"*

This mechanism, a lightweight conversational nudge appended to each response, costs nothing to implement, requires no change to the underlying AI model, and directly addresses the passive delegation concern that sits at the heart of most academic integrity debates around AI.

Importantly, this is not an untested idea. Current research within the School is specifically investigating whether minimal conversational nudges of this kind shift students toward more reflective AI use. This Faculty-level infrastructure would provide the platform to test, refine, and scale those interventions across a much larger cohort, turning a research question into an institutional capability.

The nudge approach also reframes what this service is. It is not a shortcut tool with guardrails bolted on. It is an AI environment designed from the ground up to support learning, not to replace it.

---

## Academic Integrity

Providing students with institutional AI access will raise questions about academic integrity, and it should. These are legitimate questions and the proposal does not sidestep them.

The position here is that AI access is already unequal, not absent. Students who can afford commercial subscriptions are already using them. Providing institutional access does not introduce AI into assessed work; it changes who has access to it, and crucially, it changes the environment in which that access occurs.

A student using a commercial tool receives an interface designed to maximise their reliance on it. A student using this service receives an interface designed to push back, to prompt reflection, and to encourage them to interrogate rather than simply accept what the AI produces. That is a meaningfully different academic experience, and it is one that only a locally controlled service can provide.

Acceptable use policies governing what the service can and cannot be used for in an assessed context would be developed in consultation with the relevant academic governance bodies before the service is made available to students at scale. The proof of concept phase provides an opportunity to develop these policies alongside the technology, rather than retrospectively.

---

## On Policy and DTS

There is currently no Curtin policy that explicitly prohibits a deployment of this kind, and none that explicitly authorises it. This ambiguity has, informally, been treated as a barrier.

The position here is that absence of prohibition is not prohibition. This machine would:

- Operate within Curtin's physical and network infrastructure
- Comply with existing cybersecurity standards
- Handle no personally identifiable information beyond what is already managed under existing University data governance frameworks
- Require no integration with core University systems for a proof of concept
- Sit well within the category of research and teaching infrastructure that Schools and Faculties routinely acquire and manage

The appropriate path forward is not to wait for policy to catch up, but to demonstrate responsible implementation and allow policy to form around evidence. The proof of concept is how that evidence is created.

For the proof of concept stage, the only infrastructure requirement from DTS would be a fixed IP address within the Curtin network. That is a low-friction, low-risk request.

---

## The Integration Risk: How Good Intentions Become Two-Year Delays

There is a predictable institutional response to proposals like this, and it is worth naming it honestly rather than discovering it mid-process.

Once a proposal touches departments responsible for cybersecurity, data governance, authentication, and network management, each group applies its own rigour. Each group is doing its job correctly. The problem is not bad faith; it is sequencing. Individually reasonable requirements, applied in series, can turn a four-week project into an eighteen-month review process.

The typical progression looks like this:

- *"It should integrate with Curtin's Single Sign-On"* (valid requirement, but SSO integration for a new service routinely takes six to twelve months)
- *"We need a cybersecurity assessment"* (valid requirement, but assessments require detailed documentation of a system that does not yet exist)
- *"Data governance needs to review how student data is handled"* (valid requirement, but the data handling model cannot be fully specified until the services are defined, which requires a working system)
- *"DTS needs to be the long-term support owner"* (valid question, but DTS cannot scope support for something they have not seen operate)

Each of these is a legitimate concern. None of them is answerable in the abstract. They are all, however, answerable by a working machine.

This is precisely why the proof of concept must be protected from the integration conversation until it has produced something tangible. The goal is not to bypass these processes. The goal is to give every stakeholder something real to evaluate, rather than asking them to approve a document.

A cybersecurity team that can interrogate an actual running service, on an actual Curtin network connection, with actual usage logs, can do their job properly. A data governance team that can see how queries are handled, where data is stored, and what leaves the University (nothing) can assess the real risk rather than a theoretical one. DTS, presented with a working system and real usage data, can scope support honestly.

The proof of concept converts hypothetical risk into manageable evidence. Without it, the proposal is at the mercy of every stakeholder's worst-case assumptions. With it, the conversation changes from *"what might go wrong"* to *"here is what is actually happening, and here is how we address it."*

The ask is not to skip the governance process. It is to do the governance process on something real. Every major enterprise manages integration risk through proof of concept deployments for exactly this reason: it is standard practice, not a shortcut.

---

## Cost: Local vs Cloud

A common response to proposals like this is: *why not just use the cloud?*

The honest answer is that cloud solutions are not cheaper when you account for sustained, high-volume use. The table below provides indicative figures for comparison over a three-year period.

| | **2× Local M3 Ultra (256 GB each)** | **Equivalent Cloud Service** |
|---|---|---|
| **Hardware / Subscription Cost** | ~AUD $18,000–22,000 (one-time) | ~AUD $3,000–6,000 per month |
| **Three-Year Total** | ~AUD $18,000–22,000 | ~AUD $108,000–216,000 |
| **Redundancy** | Built-in, service survives single machine failure | Depends on provider SLA |
| **Data Sovereignty** | Full, data stays at Curtin | Partial, depends on provider contract |
| **Customisation** | Full | Limited by provider |
| **Dependency Risk** | Low | High, pricing and availability subject to provider decisions |
| **Capability Ownership** | Yes, the Faculty builds genuine expertise | No, access only, no transferable capability |

*Note: Cloud cost estimates assume moderate to heavy academic use across a faculty-sized cohort. Actual figures will vary. A detailed TCO analysis is available on request.*

The cloud comparison also misses two less quantifiable points. First, locally hosted infrastructure gives the Faculty genuine capability, not just access. It creates something that can be used for research, for curriculum development, and for building the kind of applied AI literacy that no external provider can develop on our behalf. Second, the two-machine configuration provides redundancy that many cloud services charge a premium for, built into the architecture from the outset.

---

## Why Not Wait for the M5 Ultra?

In the interest of transparency, Apple is expected to release the M5 Ultra chip in late 2026. Industry commentary suggests it may offer a 512 GB or higher unified memory option, which would reopen the possibility of a single, larger machine.

This proposal recommends proceeding with the M3 Ultra now, for three reasons:

1. **The M3 Ultra is a known quantity.** It is shipping, benchmarked, and available for purchase today. The M5 Ultra timeline is speculative and subject to change.
2. **Waiting has a real cost.** Every semester that passes without this infrastructure is another semester where the equity gap widens. Students who cannot afford commercial AI subscriptions right now are not helped by hardware that might be available later.
3. **The two-machine M3 Ultra configuration is arguably stronger than a single M5 Ultra would be.** Even if the M5 Ultra ships with 512 GB, a single machine is still a single point of failure. Two M3 Ultra machines provide redundancy, load balancing, and double the concurrent capacity. There is no configuration of a single machine, regardless of how powerful, that offers these operational advantages.

If the M5 Ultra does ship with significantly greater capability at a comparable price, it becomes a natural upgrade path: one or both M3 Ultra machines could be replaced or supplemented over time. The software stack is hardware-agnostic and scales horizontally by design. Buying the M3 Ultra now does not lock the Faculty out of future hardware; it locks students in to equitable access starting this year.

---

## How Many Students Can Use It?

Rather than relying on theoretical benchmarks, it is possible to anchor these estimates in something more useful: a real deployment, already running within the School of Marketing and Management, on a fraction of the proposed hardware.

**What the existing infrastructure already handles**

The School currently operates a suite of AI services on a single consumer-grade desktop machine: a mid-range processor paired with an entry-level gaming GPU with 8 GB of dedicated memory. This is not research infrastructure. It is a repurposed workstation.

Across two years and four semesters, that machine has delivered:

- **14,565 messages** through 17 purpose-built chatbots embedded in Blackboard units
- Coverage across four units, distributed across both semesters of the academic year:

| Unit | Cohort | Semester |
|---|---|---|
| AI in Business: Strategy and Management (ISYS6020) | ~50 students | Semester 1 |
| Information Systems Security and Audit (ISYS6018) | ~55 students | Semester 2 |
| Information Systems Analysis (ISYS5002/2002) | ~120 students | Both semesters |
| AI-Driven Knowledge Systems (ISYS6014) | ~70 students | Both semesters |

- A separate API service exposing a local AI model directly to student Python environments, used as an assessed requirement in Information Systems Fundamentals (ISYS2001), which also runs both semesters with a combined cohort of approximately 100 students. This ensured every student, regardless of means, had access to the same AI service for their assignments without sharing commercial API keys

This is not a single-semester pilot. The service runs continuously across the full academic year, with different units drawing on it at different points. That distribution is also a natural form of load management; peak demand from one unit rarely coincides with peak demand from another.

In total, up to 270 students per semester interact with these services in some form, generating roughly 20–25 chat interactions per student per semester through the interface alone, with additional programmatic load from the API service during assessment periods.

No significant performance issues have been reported. The machine is still running.

**What this means for the two M3 Ultra machines**

Each M3 Ultra has approximately one hundred times the memory bandwidth of the existing machine and thirty-two times the available memory. Two of them together are not a modest upgrade. They are a categorically different class of infrastructure.

With that context, realistic estimates for the paired M3 Ultra configuration under typical academic load are:

| Service | Estimated Concurrent Users (per machine) | Combined Capacity |
|---|---|---|
| AI chat (text) | 50–100+ with good response times | 100–200+ |
| Notebook environments | 20–40 | 40–80 |
| Image generation | 10–20 concurrent jobs | 20–40 |
| API access (programmatic) | Rate-limited by design to ensure fair access | Load balanced |

These are conservative estimates. The proof of concept phase will produce real data to replace these projections. But the existing deployment makes one thing clear: even minimal hardware serves a meaningful student cohort reliably. Two M3 Ultra machines are not minimal hardware.

For a Faculty-wide deployment, this capacity is not only sufficient; it is comfortable for the full academic year, with genuine headroom to grow. Load balancing across two machines also means that peak demand from one school or unit can be absorbed without degrading the experience for others.

**Use of this service is not, and should not be, mandatory.** Many students already use and prefer commercial frontier tools, and nothing in this proposal changes that. Students with ChatGPT Plus subscriptions will continue to use them. Students who prefer a particular interface will continue to use it. This is entirely appropriate. The aim of this service is not to replace every student's existing workflow; it is to ensure that students who cannot afford commercial alternatives have access to something genuinely equivalent.

This self-selection is also, practically speaking, a natural load balancing mechanism. Not every student in the Faculty will use the service simultaneously, or even regularly. Those who have alternatives will use them. Those who do not will use this. That distribution is exactly what makes the concurrent user numbers workable at Faculty scale.

The crux of the matter is straightforward: students who can afford frontier AI tools already have access. This proposal ensures that those who cannot are not left behind.

If demand grows beyond comfortable capacity, there are straightforward options: add a third machine (the software stack scales horizontally), or implement a queuing system that manages peak load gracefully. Neither requires starting again.

**On redundancy:** Two machines means the service does not have a single point of failure. If one machine requires maintenance, encounters a hardware issue, or needs a software update, the other continues serving students without interruption. This is not a theoretical benefit; it is what any governance committee will expect from a service that students are told to rely on. The two-machine architecture answers the availability question from day one, rather than deferring it to a future phase.

---

## From Working Prototype to Proof of Concept

The software stack is not theoretical. The School of Marketing and Management already operates a working prototype on consumer-grade hardware. The full service stack -- AI chat, voice interaction, image generation, unit assistants, research tools, and productivity tools -- is running today and accessible for one to two concurrent users.

The prototype demonstrates that:

- The full service stack works end-to-end
- The software configuration is stable and reproducible
- No data leaves the machine, verifiable by inspection
- The architecture scales -- the same software runs identically on more powerful hardware

What the prototype *cannot* demonstrate is the quality gap. The small AI models that fit on consumer hardware are useful for many tasks, but they are visibly weaker than the commercial frontier tools students are paying for. A 4-billion-parameter model running on a gaming GPU is not the same experience as ChatGPT Plus or Claude Pro. It is good enough to prove the architecture; it is not good enough to close the equity gap.

That is what the M3 Ultra proof of concept is for.

With 256 GB of memory per machine, the M3 Ultra can run the largest openly available AI models -- the same class of models that power the commercial tools. The proof of concept answers the question the prototype cannot: **are open-source models, running locally on hardware the University owns, genuinely comparable to the commercial services students are currently paying for?**

If the answer is yes -- and the existing evidence strongly suggests it will be -- the path to Faculty-wide deployment is straightforward. If it is not, the investment is two machines, not a multi-year commitment.

A structured proof of concept period of eight to twelve weeks, with a student cohort from the School of Marketing and Management, would produce the usage data, quality comparisons, student feedback, and acceptable use framework needed to support a Faculty-wide deployment decision.

---

## What About Long-Term Support?

This is the most legitimate concern and it deserves a direct answer.

For the proof of concept phase, support would be handled by the team that built it, within the School of Marketing and Management. This is appropriate for a research and development activity and requires no DTS involvement.

For a sustained Faculty-wide deployment, there are three credible paths:

1. **Assign internal responsibility** to a staff member with appropriate technical skills, as part of an existing or expanded role. This is not a full-time position for two machines running identical configurations.
2. **Formalise as Faculty research infrastructure**, which brings it within scope for existing IT research support frameworks and makes the case for ongoing resourcing more straightforward.
3. **Transition to DTS management** once the proof of concept has demonstrated value, the operational model is understood, and a service definition can be agreed. This is the natural long-term home if the service scales to a University-wide offering.

The skills required to manage this machine are not exotic or rare. They exist within the University already, and this proposal would actively build them in the team responsible for the proof of concept. Talent development is a by-product of doing this well.

It is also worth noting that the Faculty of Business and Law managing applied technology infrastructure is not unusual in a higher education context. It is increasingly expected. The question is whether the Faculty builds this capability now, on its own terms, or waits for a central initiative that may or may not arrive.

---

## Positioning: A Faculty Initiative, Not Shadow IT

It would be easy to read a School-initiated technology project as shadow IT, a workaround built outside proper governance channels. That framing would be incorrect, and it is worth addressing directly.

This proposal is a Faculty-level initiative, prepared and presented through Faculty leadership, motivated by a Faculty-wide equity challenge. The School of Marketing and Management is the natural home for the proof of concept because the expertise and the urgency both exist there. But the intent, from the outset, is to demonstrate a model that serves the whole Faculty and, if successful, the whole University.

If the proof of concept succeeds, the invitation to DTS, to IT governance, and to other Faculties is open. The goal is not to build something separate. It is to build something first, well enough that others want to join it.

---

## Summary: What We Are Asking For

| | |
|---|---|
| **Immediate request** | Approval and funding for two Apple M3 Ultra machines (256 GB each), approximately AUD $18,000–22,000, for a structured proof of concept within SoMM |
| **Medium-term request** | Faculty-wide deployment based on PoC evidence |
| **What it delivers** | Equitable, sovereign, cost-effective, and redundant AI access for all Faculty of Business and Law students |
| **What it avoids** | Ongoing cloud subscription costs, external data exposure, subscription dependency, single points of failure, and a widening AI access gap between students |
| **What it builds** | Faculty capability, research infrastructure, and a replicable model for the broader University |

---

## Next Steps

1. Approve funding for two M3 Ultra machines (~AUD $18,000–22,000)
2. Deploy the proven software stack on the new hardware (days, not months -- the software is ready)
3. Run a structured proof of concept with a student cohort from SoMM (eight to twelve weeks)
4. Compile usage data, quality comparisons, student feedback, and acceptable use framework
5. Present evidence-based case for Faculty-wide deployment
6. Invite DTS and broader University engagement on the basis of demonstrated outcomes

---

*A more detailed technical project proposal, including architecture diagrams, service configuration options, model licensing schedule, acceptable use policy framework, and a full TCO model, is available on request.*
