---
title: "Local AI for WorkReady teaching and research"
subtitle: "Decision paper for the WorkReady Simulation project lead"
author: "School of Marketing and Management, Faculty of Business and Law, Curtin University"
date: "14 September 2026"
---

**Prepared for:** Project lead, WorkReady Simulation

**Status:** For project-leader decision; indicative costs subject to quotes

**Classification:** Internal

# Executive summary and decision requested

**We propose using existing project funds to purchase one Apple Mac Studio M5 Ultra with 512GB of memory and 2TB of storage for WorkReady teaching and research.** The computer will host the local AI service for an 8–12-week pilot involving approximately **1,500 students**. We will introduce access in stages, with a design target of **150 active users at once**, subject to load testing.

WorkReady gives students repeated practice with job applications, interviews, workplace conversations, and feedback. The proposed service provides this access through an ordinary web browser, without a personal AI subscription. Local hosting gives the University control over model selection and student-data handling. The 512GB configuration provides capacity for larger models and several models kept ready together, with research scheduled around teaching. This broader use is the justification for the additional memory; the text-based pilot alone may fit within 256GB.

The financial plan assumes **three years of service**, with five years as the useful-life objective. At 1,500 new participants each year, the investment serves **4,500 students over three years**. Beyond the equipment purchase, we allow approximately **A$2,300 annually for electricity, hosting, backup storage and minor maintenance**. Staffing is a separate allocation of **10 staff-days for setup and evaluation preparation**, followed by **up to four hours per week during the pilot**. The project leader will confirm whether existing staff allocations can cover this work. Section 5 separates these commitments from a conservative full resource-cost scenario; the pilot will establish ongoing staffing needs. Research benefits and use beyond year three are additional value, excluded from the financial return.

**The decision requested is endorsement of this use of project funds and permission to obtain the final equipment quotes.** The project team will return with the total price, delivery date, support allocation and model-memory assessment before ordering. One 512GB computer is the recommended starting configuration. One 256GB computer is the fallback if the larger memory has no substantiated teaching or research use at the quoted premium. A second computer is a later investment decision. The pilot will establish the service's usable capacity, educational value and actual operating cost.

# 1. Student experience and educational value

WorkReady is a simulated workplace where students can practise professional skills before using them in a real job. They explore fictional employers, apply for a role, attend an interview, complete workplace tasks, communicate with colleagues, and reflect on what they have learned.

AI supplies the simulated conversations and personalised feedback. Students can make mistakes, receive guidance, and try again in a setting designed for learning. We propose providing every participant with the same core service, without requiring a personal AI subscription.

| Student activity | What WorkReady provides |
|---|---|
| Applying for a role | Feedback on a resume and cover letter |
| Attending an interview | A simulated interviewer who asks questions and follows up on answers |
| Completing workplace tasks | Feedback that helps students improve their work |
| Working with others | Practice conversations with simulated colleagues and mentors |
| Reflecting on the experience | An exit interview that helps students identify what they have learned |

## Equitable access to practice and feedback

The University computer will perform the AI processing, allowing students to participate through a supported web browser on ordinary student or campus devices. Required practice and feedback will be included in the teaching service, rather than depending on a student's ability to purchase premium tools.

Repeated practice gives students time to prepare answers and rehearse before live activities. The pilot will examine whether students use this opportunity and whether it improves their work, including for those who need more preparation time.

The commissioning plan includes checks on ordinary student and campus computers, slower connections, keyboard navigation and assistive technology. The teaching team will provide an introduction, fair usage limits and an equivalent supported activity for students unable to access the simulation. The evaluation will record access barriers and completion without paid supplementary tools.

This strengthens the case for a University-funded teaching service. A suitably funded cloud service could offer the same student access benefits; equity alone does not establish the need for local ownership or 512GB of memory.

## Why proceed now?

The application has already been built and checked in a development setting. It includes six fictional employers, a job board, a student workspace, and the conversation and feedback features. The next step is to establish how well it works with a teaching cohort and how many students it can serve comfortably.

The next investment would move WorkReady from development into a supported teaching trial. Without dedicated or approved shared AI capacity, access would need to remain limited or depend on a separately funded external service. Deferring the purchase preserves funds, but also defers evidence about learning benefits and real teaching demand. The reason to proceed is readiness to evaluate the application, rather than the release of a new computer alone.

The School reports prior experience with local AI through Blackboard chatbots and programming assignments. This experience provides a starting point for operating the service; WorkReady still needs its own teaching and performance evaluation. Project evidence is listed in the technical appendix.

# 2. Proposed service and data management

**Keeping the AI model on University equipment gives the University direct control over the model, its settings, and the handling of student conversations.** The team can choose when to update it, restrict access, and set how long records are kept. That control matters when the simulation contains student work, feedback, and discussions of personal experience.

There are three different arrangements to distinguish:

| Arrangement | Where AI questions are processed | What the University controls |
|---|---|---|
| **University computer running our own model** | Within University-controlled facilities, if all AI functions are configured that way | The model and software, physical equipment, access, and record handling |
| **Rented computer running our own model** | On the rented computer at the hosting provider's premises | The model and installed software, subject to the rental terms; the host operates the underlying facilities |
| **An external AI service answering each question** | At the AI provider, which receives the question and any conversation history or documents sent with it | The application instructions and data submitted; model operation and provider-side handling depend on the service and contract |

**Renting does not necessarily mean sending every question to a separate AI company.** With a suitable rented computer, we can install the model there and generate answers on that machine. However, the student information still travels to and is processed in the rented environment. If we rent only the website server and it calls an external AI service, the relevant content is sent onward to that AI provider as well.

The rental comparison will assess processing and backup locations, provider access, data use, deletion and incident reporting. Australian hosting addresses location but does not establish exclusive University control. Appendix F sets out these responsibilities and the limits of encryption in a hosted environment.

Local ownership also requires proper administration, secure access, backups, and checks that software is not sending content to external services. The advantage is **direct institutional control and fewer external parties involved in student AI processing**. It is not an automatic guarantee of security or policy compliance.

We propose hosting the WorkReady website and student progress records on approved University application infrastructure, with a private connection to the dedicated AI computer. The computer will generate conversations and feedback. This separates durable student records from the AI processing service and allows the model to be maintained without moving the records. The connection and recovery procedures form part of commissioning.

The proposed operating model assigns teaching and evaluation to an academic lead, day-to-day administration to a technical lead, and recovery cover to a second trained staff member. The project leader will confirm these staff allocations with Faculty leadership and the University's IT team, DTS, before purchase. Commissioning will establish the approved equipment location, access permissions, record storage and recovery procedure.

The development version includes student sign-in, record-ownership checks, and tools to filter and delete submitted material. The technical lead will validate these controls in the teaching environment. Pilot activities will use fictional identities and practice resumes. Access and retention rules will also cover personal details that students enter despite this guidance.

The proposed pilot will process AI conversations within approved University facilities. Because WorkReady also supports external providers, commissioning includes disabling external AI endpoints and checking outbound traffic across all conversation tools, including separate employer chat tools.

Lecturers retain responsibility for assessment. The academic lead will review a fixed sample of AI feedback for usefulness, accuracy and professional appropriateness before student access begins. The pilot evaluation will examine changes in student work alongside satisfaction and completion. These measures will distinguish an engaging experience from evidence of learning.

# 3. Rationale for the 512GB configuration

**The reason for requesting 512GB is to provide working space for a broader local AI service: a larger model, several complementary models kept ready together, and the information they process.** This could support text, speech, images, and selected video experiments as the service develops.

Working memory holds the active AI models and the information they are processing. More memory allows larger models or several models to remain available without repeated loading from storage.

Apple calls this *unified memory* because the computer's processing components share that working space. The requested **512GB is working memory**; the separate **2TB of file storage** holds software, model files, and working documents.

## More than one kind of AI

| Possible capability | Potential teaching or research use |
|---|---|
| Text conversations and document feedback | WorkReady interviews, simulated colleagues, and feedback on submissions |
| Speech recognition and spoken responses | Explore spoken interview practice, transcription, and optional audio responses alongside text |
| Image understanding and generation | Explore feedback on visual business material and preparation of fictional campaign or workplace images |
| Video generation or analysis | Scheduled experiments with short training scenarios or research material, subject to model support and acceptable processing times |

The text-based pilot is the immediate commitment. Speech, image, and video functions are possible extensions requiring software integration and evaluation. Apple's MLX examples cover text, image, video, and speech-recognition models; the MLX Audio project also supports speech generation. These establish available software approaches, not tested WorkReady features or a requirement for 512GB. [MLX examples](https://github.com/ml-explore/mlx-examples) and [MLX Audio](https://github.com/Blaizzy/mlx-audio)

**Keeping several models loaded can reduce delays from unloading one and loading another.** For example, a future spoken interview could use separate models to transcribe a student's answer, generate a reply, and speak it aloud. Ollama documents keeping models loaded and loading multiple models when memory permits. The benefit for the proposed service must be measured. [Ollama memory and concurrency guidance](https://docs.ollama.com/faq)

Models kept ready still share the computer's processors. We will schedule heavy image and video work outside teaching periods because it can slow student replies. Suitable combinations of text, speech and image models may fit within 256GB; the case for 512GB rests on the size of the selected workloads and reduced model-loading delays. Processing speed remains a separate acceptance criterion.

**We recommend 512GB to support a reusable teaching and research service over several years.** Before purchase, the technical lead will prepare a model-memory schedule covering weights, active conversation caches, processing buffers and the operating system. The academic lead will identify the planned use of each larger model or model combination. This assessment and the quoted memory premium will determine whether the broader service warrants 512GB. If the identified workloads fit comfortably within 256GB, we will recommend the smaller configuration. No selected model inventory or measured memory profile is yet available, so the premium remains the main unresolved part of the configuration decision.

Apple has announced the M5 Ultra Mac Studio, with general availability from **22 September 2026** and the **512GB version expected in late October**. The pilot start must depend on confirmed delivery of the requested version. [Apple Australian announcement](https://www.apple.com/au/newsroom/2026/08/apple-introduces-new-mac-studio-with-m5-max-and-m5-ultra/)

# 4. Capacity plan and service targets

**The initial target is 150 students using WorkReady at the same time, within a total pilot group of about 1,500. That target still needs to be tested.**

A student reading a job advertisement or preparing an answer uses very little AI capacity. The heavier work happens when the system generates a reply or assesses a submission. This means 150 students online usually creates less demand than 150 students all asking the AI for an answer at the same moment.

Our central workload assumption is one AI interaction every five minutes per active student. At 150 active students, that gives **30 requests per minute**. With an assumed mean processing time of 20 seconds, approximately **10 requests are in process at once**, excluding queueing. At 300 output tokens per request, the model service needs aggregate output of **150 tokens per second**, in addition to prompt processing. These calculations define the load to test; they do not establish that the proposed computer can deliver it.

WorkReady also generates messages from simulated colleagues and feedback on tasks. These add to the workload. The tests must include a class starting interviews together and several students submitting work at once.

We will commission the service at 25 concurrent users, then test 75 and 150 using the same representative activity mix. Access will expand when the response-time and reliability targets are met. Tests at 300 and 500 users will assess future headroom after the 150-user target passes. The initial teaching plan does not depend on that higher capacity.

The proposed goals are:

- Ordinary progress and inbox updates appear within one second for at least 95% of requests.
- Short AI replies arrive within 20 seconds for at least 95% of requests, including any waiting time.
- Feedback on submitted work is available within two minutes for at least 95% of submissions, with an immediate acknowledgement of receipt.
- Busy periods produce clear waiting messages and preserve student progress.
- The team demonstrates recovery after the AI computer becomes unavailable, including preservation of student progress. If a second computer is later added, test continued service using that computer.

These targets define the proposed student experience. The academic and technical leads will confirm the test workload before commissioning and record any change to the targets. Appendix B gives the calculation method and acceptance tests. The 150-user figure is a design target derived from the planned cohort and interaction pattern, not a measured hardware capacity estimate.

# 5. Cost and value for money

Australian pricing was researched on **14 September 2026**. Apple lists starting prices of **A$9,499 retail** and **A$8,809 through its public Education Store**, including GST. These prices are for the entry model. **The requested 512GB version needs a written quote**, and Curtin's purchasing arrangements may produce a different price. [Apple Australian pricing](https://www.apple.com/au/newsroom/2026/08/apple-introduces-new-mac-studio-with-m5-max-and-m5-ultra/)

The equipment package will be priced through University purchasing. The current evidence does not establish the 512GB purchase price, so we retain that cost as a quoted variable. The operating estimate below gives the project leader a basis for assessing the commitment now, rather than deferring every cost until procurement.

We propose meeting the purchase cost from existing project funds. The decision is whether this is a worthwhile use of that budget relative to other project priorities and suitable AI services. Availability of project funds does not establish unrestricted spending authority; the project leader will confirm eligible expenditure and the applicable purchasing delegation before an order is placed.

| Quote required | Scope |
|---|---|
| Preferred configuration | One M5 Ultra computer with 512GB memory and 2TB storage |
| Smaller starting option | One M5 Ultra computer with 256GB memory and 2TB storage |
| Alternative for separate workloads and continuity | Two M5 Ultra computers, each with 256GB memory and 2TB storage |
| Supporting equipment and services | Itemised support cover, backup power, connections, backup equipment, and delivery appropriate to each option |

The quote comparison will use the same chip configuration where available and identify chip differences separately. The project leader will receive the equipment package price and operating estimate together. Finance will confirm GST treatment and the amount charged to the project.

## Expected working life

The service plan provides for **three years of primary teaching use**, with **five years as the working-life objective**. Annual reviews will assess reliability, security updates and teaching requirements. In years four and five, continued teaching or less time-sensitive research can extend the value of the investment.

This is a planning assumption, not a manufacturer guarantee. Apple describes access to hardware service and parts for at least five years after it last distributes a product for sale, subject to its stated conditions. That repair policy does not guarantee five years of software support or suitability for future AI models. [Apple service policy](https://support.apple.com/en-au/102772)

The financial case assumes no resale value or research income. Finance will determine the accounting depreciation period separately from this service-life assumption.

## Non-staff operating costs

We allow approximately **A$2,300 per year in non-staff running costs**, excluding equipment. The amount charged to the project will depend on which services the University provides centrally.

| Cost item | Planning basis | Estimated cost |
|---|---|---:|
| Electricity for one AI computer | 0.2kW average × 8,760 hours × A$0.30/kWh | A$526/year |
| Application hosting and backup storage | A$100/month allowance | A$1,200/year |
| Maintenance and minor operating expenses | A$50/month allowance, excluding cover included in the equipment quote | A$600/year |
| **Total non-staff running costs** | Before confirming centrally provided services | **A$2,326/year** |

The electricity estimate assumes continuous operation at an average 200W. A 100W to 400W average gives approximately **A$263 to A$1,051 per year** at the same tariff. Power will be metered during commissioning. The estimate excludes any separately charged room cooling or network upgrade, which the IT location assessment will identify before purchase. Hosting and maintenance figures are provisional allowances to be replaced by internal charges or supplier prices.

## Staff allocation and resource-cost comparison

We propose **10 staff-days for setup and evaluation preparation**, followed by **up to four hours per week during the 8–12-week pilot** for administration and routine teaching support. This represents 75 setup hours and a further 32–48 support hours at the full allowance. The project leader will confirm whether existing staff allocations can accommodate this work or whether additional paid hours or backfill are required. Staff time has an opportunity cost even when it creates no additional project expenditure.

For comparison purposes, we value staff time at an indicative fully loaded rate of **A$85 per hour**, using a 7.5-hour working day. This is not a confirmed Curtin salary or charge-out rate. At that rate, setup effort is worth A$6,375 and pilot support A$2,720–A$4,080. Adding pro-rated non-staff costs gives a total pilot resource cost of approximately **A$9,500 to A$11,000**, excluding equipment. This is distinct from the pilot's cash requirement.

The conservative annual comparison scenario retains four support hours each week for all 52 weeks, valued at **A$17,680 per year**. With non-staff costs, this gives approximately **A$20,000 annually in total resource use**. It is a scenario for comparison, rather than an established ongoing staffing requirement. The pilot will record actual effort and distinguish teaching-period support from quieter-period maintenance. Every additional average support hour per week over a full year adds A$4,420 at the assumed rate. Substantial feature development, formal research studies and teaching delivery beyond routine support require separate staff allocations.

These figures express the economic cost of resources used. Existing salaried staff, University hosting or centrally paid electricity may reduce the additional cash charged to the project, but still consume institutional resources. The final budget will show project cash expenditure and in-kind contributions separately. Non-staff allowances are treated as gross costs with no GST recovery assumed; Finance will align the quote and operating charges before the final comparison.

Let **P** be the complete equipment package price, including selected support cover, backup power, connections, backup equipment and delivery. Equipment plus three years of non-staff running costs total **P + approximately A$7,000**, before any additional paid staffing or backfill. Actual project charges may be lower where central services cover these costs. Under the conservative year-round staffing scenario, the **full three-year resource cost is P + approximately A$66,400**, including setup effort. At 4,500 participants, that scenario corresponds to **P ÷ 4,500 + approximately A$14.75 per student**. Equipment alone costs P ÷ 1,500 per initial participant, falling to P ÷ 4,500 with three annual cohorts. Lower participation raises the cost per student.

## Buying versus renting: a simple break-even example

A cloud provider can rent us a powerful computer on which we install and run our own AI model. The relevant comparison is the cost of keeping suitable AI capacity available for teaching, with the necessary support and data protections.

The calculation is straightforward: **payback = quoted equipment and additional setup cost ÷ monthly saving compared with rental**. Monthly saving is the rental charge less any additional cost of operating locally. If ownership does not produce a monthly saving, there is no financial payback on that basis.

For the central comparison scenario, we use rental of **A$1,500 per month** and an additional local operating cost of **A$250 per month relative to rental**. This produces **A$1,250 per month available to recover the equipment and additional local setup cost**, or **A$45,000 over three years**. Ownership breaks even within three years if equipment plus additional local setup cost is below A$45,000 and these monthly assumptions hold. This is a comparison scenario, not a supplier quote or an estimate of equivalent rental capacity.

The A$250 monthly difference is distinct from both the non-staff running-cost allowance and the full resource-cost scenario above. Both local and rented services require application hosting, model administration and student support. The comparison assumes most of those costs are shared between the options. We will replace the A$250 difference with itemised local and rental costs once the hosting and support arrangements are known.

This comparison assumes continuous rental, comparable teaching service, and a consistent GST basis. It assigns no financial benefit to research, resale, or years four and five. The appendix provides the ROI formula, sensitivity calculations, and published rental references. Short or seasonal use can favour rental; the final calculation must reflect the required student access schedule and actual staff costs.

## Why ownership is the preferred option

Local ownership is preferred for the combination of direct control, large-model access, and reuse across teaching cohorts. The choice remains subject to the confirmed cost and workload requirements.

| Option | Where it could be the better choice | Implication for this proposal |
|---|---|---|
| Existing University AI or research equipment | Suitable models, approved data handling, and capacity available when classes need it | Check availability before buying; avoid duplicating a suitable existing service |
| One or two 256GB local computers | The models fit within 256GB per machine; lower initial commitment or separate teaching and development systems is preferable | Obtain complete package quotes and apply the configuration choices in section 7 |
| A dedicated rented computer running our model | Short or seasonal use, or a need to establish demand before buying | Obtain a quote for the required teaching schedule and data arrangements |
| An external AI service charged by usage | Low or uncertain demand, with suitable feedback quality and approved data handling | Compare all conversation, document, and automated-character charges |
| The proposed local computer | Sustained use, direct equipment control, and a substantiated need for large-model capacity | Preferred if the procurement comparison supports these requirements |

The pilot will record staff effort and model usage so that the final comparison reflects equivalent teaching quality and access hours. Our preference for ownership rests on repeated use and institutional control. The project leader will see any additional cost of that choice explicitly, rather than treating research potential or unmeasured capacity as a financial saving.

# 6. Research value during quieter teaching periods

We propose making the same computer available for approved research during evenings, semester breaks and other periods of low teaching demand. A booking arrangement will extend access to researchers while preserving the teaching service.

Potential uses include:

- **Research into AI and learning:** test whether different kinds of feedback and follow-up questions help students think more carefully and improve their work.
- **Business and management research:** develop simulated customers, employees, or negotiating partners for studies of decisions and workplace communication.
- **Working with research documents:** explore AI assistance with finding information, grouping material by theme, and preparing summaries, with researchers checking the results.
- **AI using speech, images, and video:** evaluate spoken simulations, visual business material, and short media experiments, with heavier generation scheduled outside teaching. These are possible extensions, not promised pilot features.
- **Postgraduate projects and grant preparation:** give researchers access to equipment for testing ideas and collecting preliminary results before seeking larger research funding.

The large memory would let researchers explore models and document sizes beyond those chosen for quick classroom responses. Keeping the work local can also give the University more control over where approved research material is processed.

Teaching will retain priority. Research bookings will identify the model, expected memory use and duration. Jobs will stop before required teaching access resumes. Experiments using most of the computer's memory will run in dedicated periods when the teaching service is not required.

The pilot report will record research bookings and resulting studies, teaching materials or grant applications. These opportunities are additional to the teaching justification; no research income or savings are included in the budget. Each study will follow the applicable data-access and research ethics requirements.

# 7. Configuration choices and when a second computer would add value

We recommend starting with one 512GB computer, with the configuration decision governed by the memory assessment in section 3. This keeps the initial deployment manageable while providing room for larger research workloads. The alternatives address two different priorities, lower acquisition cost or separation of teaching and development:

| Configuration | Best reason to choose it | Main trade-off |
|---|---|---|
| **One 512GB computer** | Preferred for a specified larger model or model combination that exceeds practical 256GB capacity | One processing system and one point of interruption; selection depends on the quoted memory premium |
| **One 256GB computer** | Lower-cost starting option if the selected teaching and research workloads fit | Less capacity for larger models; research and teaching share one computer |
| **Two 256GB computers** | Alternative when separating workloads and providing fault cover offers greater value | Two computers to buy and support; fault cover requires configured routing and sufficient spare capacity |

**Two 256GB computers do not automatically act as one 512GB computer.** This proposal assigns work to separate machines. Splitting a single model across machines would be a different technical design requiring its own software and performance tests. For fault cover, the surviving computer must be able to run the essential teaching models even if optional functions are paused.

The quote comparison will include two 256GB systems to establish the cost of separating teaching and development. We will recommend a pair before the pilot only if that separation offers greater value than a single larger memory pool. The project leader would then approve a revised package and support allocation. The present recommendation and operating estimate cover one computer.

The strongest reason for two computers is that teaching and development need to happen alongside each other. Students need a dependable service, while the team needs to try improvements and check new AI models.

| Need | With two computers | With one computer |
|---|---|---|
| Busy teaching periods | Both can share the AI work | Activities may need to be staggered |
| Maintenance or a fault | The other can continue a reduced service once the switch has been set up and tested | AI activities stop until the computer is available again |
| Testing improvements | One can support classes while the other is used for testing | Testing is scheduled outside teaching periods |
| Research | More opportunities to use spare capacity alongside teaching | Mainly scheduled outside teaching periods |

If a second computer is approved, it could support development and approved research alongside teaching. Research and development tasks would pause whenever teaching needs that capacity.

The ability to switch work between computers must be set up and tested; it does not happen simply because two computers have been purchased. A student might need to retry an answer interrupted by a fault, and the remaining computer might respond more slowly. A shared power or network failure could still affect both.

The pilot will record waiting times, interrupted activities and development work deferred to protect teaching. These results will establish whether a second computer is needed and the improvement required to justify its cost.

# 8. Pilot timetable and next decision

The **8–12-week evaluation starts after the first computer has arrived and the service has been set up and checked**. Purchasing, planning, and preparation can begin while waiting for delivery.

| Stage | What happens |
|---|---|
| Before delivery | Confirm costs, staff support, University IT arrangements, and how success will be measured |
| Setup | Install and check the AI service, protect student records, and test backup and recovery arrangements |
| Weeks 1–2 | Staff and a small student group complete the full simulation and check feedback, ease of use, and accessibility |
| Weeks 3–6 | Expand towards 150 students at once if tests pass; introduce the wider group in stages |
| Weeks 7–10 | Measure learning, waiting times, costs, support effort, research use, and recovery after an interruption; test larger groups if practical |
| Weeks 11–12, if needed | Address significant issues and recommend whether to continue or expand |

The academic lead will report changes in student work and professional skills against common criteria before and after the activity. The technical lead will report response times, demonstrated capacity, interruptions and support effort. The project leader will receive these results alongside actual operating costs, research use and a recommendation on continuation.

## Evidence required to continue or expand

The evaluation will use completion data, a sample of student work assessed against a common rubric, lecturer review of AI feedback and the service measures in section 4. The academic and technical leads will finalise the sampling plan and assessment criteria before launch. This avoids selecting favourable measures after seeing the results.

| Question for the pilot report | Evidence and responsibility |
|---|---|
| Does it help students learn? | Academic lead: completion rates, a sample of work assessed against the same criteria before and after the activity, and lecturer review of AI feedback; agree the required improvement before launch |
| Can students use it comfortably? | Technical lead: the response-time and reliability results in section 4, accessibility checks, recovery results, and a record of student support issues |
| Can students participate without extra cost or access barriers? | Academic lead with accessibility support: completion on ordinary and campus devices, reported connection or accessibility problems, and access to an equivalent supported activity; collect only the information needed for evaluation |
| Does ownership provide value? | Project lead with Finance: actual staff effort and usage, updated three-year costs, and quotes for suitable alternatives using the same access schedule |
| Is the larger memory being used productively? | Academic and technical leads: models kept loaded together, peak memory use, delays when changing models, scheduled research use, and whether one or two 256GB systems would have met those needs |

A before-and-after comparison can identify change but cannot, by itself, attribute that change to WorkReady. The academic lead will assess the feasibility of a suitable comparison group during evaluation preparation. The report will state the design's limits and distinguish observed improvement from evidence of causation.

## Delivery risks and response

| Main uncertainty | Planned response |
|---|---|
| Delivery or setup takes longer than expected | Confirm delivery and staff availability before committing a teaching date; start the evaluation after commissioning |
| Replies are too slow or feedback is unsuitable | Begin with a small group, evaluate model quality and response times, and adjust the model or activity schedule before expanding |
| The computer or its sole maintainer is unavailable | Document restart and recovery, train a second support person, and arrange an alternative teaching activity during interruptions |
| Use or learning benefit is lower than expected | Pause expansion and any second purchase; consider a smaller ongoing service or approved research reuse, with a named owner and operating budget |

We recommend continuation within the capacity demonstrated by the pilot, provided feedback quality, student access and support effort are acceptable. If response targets fail, the team will first test a smaller model and staggered activity scheduling. A second purchase will require evidence that additional hardware addresses the limiting factor. If educational value or operating feasibility is inadequate, the project leader will decide whether to change the service or end teaching use. Research reuse will require an identified project and operating allocation.

# Recommended decision wording

> Endorse the proposed use of existing project funds for one Apple Mac Studio M5 Ultra with 512GB of memory and 2TB of storage, supporting a WorkReady pilot for approximately 1,500 students and research outside required teaching periods. Authorise the project team to obtain the equipment package quote and confirm delivery and eligible expenditure. Allow approximately A$2,300 annually for non-staff running costs. Separately, allocate 10 staff-days for setup and evaluation preparation and up to four hours per week during the pilot. The project leader will confirm staff availability, any additional paid staffing or backfill, centrally provided services and the final cash commitment before ordering.
>
> Select 512GB if the model-memory assessment and quoted premium support the planned teaching and research use. Otherwise, adopt a revised 256GB specification. Commission the service with local-only AI processing, protected student records and staged access, working towards the 150-user target through load testing.
>
> Review continuation and expansion after the pilot against learning evidence, demonstrated capacity, support effort and actual costs. A second computer requires a separate decision supported by measured demand or a documented continuity requirement.

The staged approach limits the initial commitment while preserving the local, University-controlled service needed to evaluate WorkReady. A second purchase is justified when the pilot demonstrates demand beyond one system, a material need for fault cover during teaching, or a sustained requirement to undertake research and development without reducing student service.

---

# Technical appendix for IT and purchasing reviewers

The business decision is described above. The following details support equipment selection, testing, costing, and service preparation.

## A. Hardware specification and model memory

| Component | Requested configuration | Purpose |
|---|---|---|
| Processor | M5 Ultra, 36-core CPU / 80-core GPU | The chip configuration Apple specifies for the 512GB option |
| Unified memory | **512GB per system** | Model weights, conversation context, concurrent inference, and room to evaluate larger models |
| Internal storage | **2TB SSD** | Operating system, active model library, and local working files; capacity to be checked against the selected model inventory |
| Network | Wired connection using built-in 10Gb Ethernet | Connection to the institutional application service; available switch capacity to be confirmed |
| Operation | Dedicated AI service, remotely administered | Preserve compute for teaching and approved AI development |

Apple lists **1.2TB/s memory bandwidth** for M5 Ultra. This and its large unified memory make it a credible local inference candidate, but neither specification establishes WorkReady throughput. Runtime support and application performance must be tested on the delivered systems. [Apple Australian technical specifications](https://www.apple.com/au/mac-studio/specs/)

For illustration, 70 billion parameters at four bits require about **35GB for raw weights**, while 400 billion parameters at eight bits require about **400GB**. These are arithmetic lower bounds, excluding model-format overhead, working memory, conversation caches, and the operating system. They illustrate why a larger memory pool expands model choice; they do not demonstrate that either model would meet teaching response-time targets.

The technical lead will select the smallest model that meets the teaching quality and response-time targets. Larger models will be evaluated for research and more demanding feedback tasks. The initial deployment uses one computer with its own 512GB memory pool. Any later machine will handle independent work; the design does not rely on pooling memory across computers. The operating system, inference runtime and conversation caches also require memory.

### Memory for several models

Budget for the combined memory of models kept loaded, concurrent conversation caches, temporary processing buffers, the operating system, and spare capacity. Model-file sizes alone do not establish the working-memory requirement. A model kept loaded is ready for use; it need not be actively generating output at that moment.

Measure memory and response times for the intended mix: teaching text alone; text with speech recognition and speech generation if proposed; and teaching with any planned image or video task. Record both first-use loading delays and subsequent response times. Compare keeping models loaded against loading them on demand, and stop secondary work if teaching targets are missed. Separate speech or media runtimes need coordinated resource limits; Ollama's settings do not manage every program on the computer.

This assessment will identify whether the additional memory avoids material loading delays or enables a specified workload that 256GB cannot comfortably accommodate. The decision record will link the memory premium to those identified uses.

## B. Workload calculations and acceptance tests

The following are **illustrative workload scenarios**, assuming 150 active users, one model call per interaction, an average 20-second processing time excluding queueing, and 300 generated tokens per call:

| AI interaction rate per active user | Model calls per minute | Average requests being processed | Aggregate output rate required |
|---|---:|---:|---:|
| One every 10 minutes | 15 | 5 | 75 tokens/second |
| One every 5 minutes | 30 | 10 | 150 tokens/second |
| One every 2 minutes | 75 | 25 | 375 tokens/second |

Calculations: calls/minute = active users ÷ minutes between interactions; average in-process requests = calls/minute × processing seconds ÷ 60; output demand = calls/minute × output tokens ÷ 60.

These figures describe demand, **not measured M5 Ultra performance**. Prompt processing, growing histories, additional reviews, simulated colleagues, and bursty arrivals all add work. If each interaction invokes two equivalent model calls, the call and token demand doubles. A class of 150 starting interviews together is a separate burst test, even if average use is light.

Ollama supports parallel requests and queueing, with memory demand increasing as parallel context capacity grows. The serving configuration must be tuned and measured for the selected model; its defaults are not a 150-user service specification. [Ollama concurrency documentation](https://docs.ollama.com/faq#how-does-ollama-handle-concurrent-requests)

Proposed acceptance targets, to be agreed before testing:

| Measure | Proposed target |
|---|---|
| Ordinary API reads | 95% complete within 1 second at the agreed 150-user workload |
| Short conversational reply | 95% complete within 20 seconds end to end, including queueing, using a documented prompt and output limit |
| Feedback on a submitted document or completed activity | 95% available within 2 minutes, with an immediate receipt acknowledgement |
| Reliability | Fewer than 1% unexpected request failures during a sustained one-hour representative run; planned overload rejections recorded separately |
| Capacity during overload | Bounded queues, clear waiting messages, and preserved student progress |
| Interruption with the initial single AI system | Preserve student progress, show a clear service message, and demonstrate restart and recovery within a recovery time agreed with the teaching team before launch |
| Interruption after a second AI system is added | New AI requests routed to the surviving system within 60 seconds; resulting capacity and failed in-flight requests reported |

The current Ollama conversation adapter waits for a complete response (`stream: False`). Therefore, a fast first token is not yet a student-visible success measure. Streaming could improve perceived responsiveness, but the initial acceptance test must measure the complete reply the student actually receives. [Current conversation adapter](../../workready/workready-api/workready_api/interview.py)

Test at 25, 75, and 150 active users, followed by 300 and 500 if targets pass. Document the activity mix, prompt/context sizes, output limits, selected model, runtime version, and serving settings. Include synchronised interview starts, task-submission bursts, automated lunchroom calls, long histories, and one-system operation. A static-page load test alone cannot validate the AI service.

## C. Deployment and commissioning

Use institutional web/application hosting for the WorkReady sites, API, and durable student records, with a private connection to the dedicated AI systems:

```text
Student browser
      |
WorkReady web service + authenticated API + student database/backups
      |
Private AI gateway: access control, request limits, queueing, health checks
      |                                      |
Mac Studio A                            Optional later computer
M5 Ultra / 512GB                        Specification based on pilot results
Local teaching model                   Teaching / scheduled evaluation
```

The first stage connects the application to Mac Studio A. Mac Studio B and routing between the two computers are a later expansion, subject to approval. The gateway is proposed commissioning work; the current deployment is a single application service with a configurable model endpoint.

Commissioning must cover:

- **Native accelerated inference.** Run the inference service on macOS and verify GPU use, model compatibility, and unattended restart. Ollama documents that its Docker container cannot use GPU acceleration through Docker Desktop on macOS; the web application can retain its separate deployment environment. [Ollama GPU deployment guidance](https://docs.ollama.com/faq#how-do-i-use-ollama-with-gpu-acceleration-in-docker)
- **Fair access and bounded work.** Set per-user budgets, context/output limits, queue capacity, timeout behaviour, and teaching priority. Measure total model calls across all conversation and feedback paths.
- **Application concurrency.** Profile database writes, polling, document parsing, and duplicate submissions. Keep the current single database until tests justify a change; do not assume two AI machines provide database redundancy. Before adding API workers, address the process-local limits identified in the release notes.
- **Recovery and operation.** Keep model versions reproducible, protect the inference endpoints from direct student access, test consistent database/attachment backups, and rehearse loss and recovery of the first AI machine. Test switching between machines if the second is added.

The release process will test model changes against a fixed evaluation set covering persona consistency, relevant feedback, unsupported claims, professional behaviour and attempts to override simulation instructions. Lecturers retain responsibility for assessment decisions.

Teaching priority must include memory reservations and model availability, not just spare processor time. On the first computer, schedule research outside required teaching availability. With two computers, research jobs using the reserve machine must be interruptible within the recovery target, or scheduled in a period with explicitly reduced teaching/maintenance cover. Gateway, application host, database, power, and network dependencies need recovery arrangements as well as the AI machines.

## D. Pricing evidence and costing assumptions

Prices researched on **14 September 2026**. Published Australian prices below include GST; an institutional procurement quote may differ from the public Education Store.

| Pricing evidence | AUD including GST | Interpretation |
|---|---:|---|
| M5 Ultra Mac Studio starting retail price | **A$9,499** | Entry configuration, not the requested system |
| M5 Ultra starting public education price | **A$8,809** | Entry configuration; not a Curtin institutional quote |
| Apple Store indexed configuration: 30-core CPU / 64-core GPU, 256GB, 2TB | **A$16,249** | Indicative reference from indexed configurator content; live page extraction did not expose a reproducible configured checkout |
| Upgrade to 36-core CPU / 80-core GPU in that indexed configuration | **+A$1,950** | Gives an arithmetic reference of **A$18,199 for 256GB / 2TB** with the larger chip |
| Requested 36-core CPU / 80-core GPU, **512GB**, 2TB | **Written quote required** | The 256GB reference excludes the unknown 512GB memory premium |

Sources: [Apple Australian launch pricing](https://www.apple.com/au/newsroom/2026/08/apple-introduces-new-mac-studio-with-m5-max-and-m5-ultra/) and [Apple Australian 256GB / 2TB configurator](https://www.apple.com/au/shop/buy-mac/mac-studio/m5-ultra-chip-30-core-cpu-64-core-gpu-256gb-memory-2tb-storage). The configurator signals late-October availability for 512GB; no verified price for the requested configuration was found. Published prices are reference points for procurement, not a requested spending amount.

University purchasing will be asked to provide itemised equipment package quotes for the shortlisted configurations. Section 5 provides the preliminary resource budget while the equipment price remains outstanding. Finance will confirm GST treatment, project charges and in-kind contributions before the final decision.

Compare alternatives over the same three-year period:

- **Local total cost:** equipment, setup labour, and three years of support labour, electricity, hosting, backup, and recurring charges.
- **External AI total cost:** integration, application operation, and metered input/output usage, including automated characters, retries, and evaluation calls.

The initial single-computer power allowance is **A$526 per year**, calculated as 0.2kW × 8,760 hours × A$0.30/kWh. A future pair with the same average draw per computer would cost approximately A$1,051 per year before cooling or other infrastructure charges. Commissioning will measure actual consumption.

The conservative full resource-cost scenario in section 5 values 75 setup hours at A$85, giving A$6,375, and 208 annual support hours at A$85, giving A$17,680. Annual non-staff allowances total A$2,325.60, or A$6,976.80 over three years. Including the year-round staffing scenario and setup effort gives A$66,391.80 over three years before equipment, rounded to A$66,400. Dividing by 4,500 participants gives A$14.75 per student before equipment. The pilot estimate pro-rates recurring costs over 8–12 weeks and adds setup, giving A$9,452.78 to A$10,991.68 before equipment at the full support allowance. These are resource-cost estimates, not confirmed project cash charges. Ongoing staffing will be based on recorded pilot effort.

## E. Cloud rental references and break-even calculations

### Published rental references

Checked **14 September 2026**. No confirmed rental quote for the requested M5 Ultra / 512GB configuration was found. The references below use older hardware and are **memory-capacity comparisons, not verified equivalents in performance, support, or availability**. Obtain Australian hosting quotes and test the proposed model before making a purchasing decision.

For conversion, the RBA lists **A$1 = £0.5293 and US$0.7149** on 14 September 2026. Divide the foreign price by the relevant rate. AUD amounts below exclude taxes, currency-conversion fees, and any unlisted extras. [RBA exchange rates](https://www.rba.gov.au/statistics/frequency/exchange-rates.html)

| Published offer | Advertised price per machine | Approximate AUD | Comparison limits |
|---|---|---:|---|
| MetalCloud M3 Ultra, 512GB, reserved monthly | £2,995/month before VAT | **A$5,658/month** | Same memory capacity; older chip. Confirm location, administration rights, service terms, and availability |
| MetalCloud M3 Ultra, 512GB, on demand | £6.95/hour before VAT | **A$13.13/hour** | Confirm billing minimums, persistent storage, model loading, and capacity when needed |
| MacWeb M3 Ultra, 256GB, 2TB | $799/month, treated as USD pending confirmation | **A$1,118/month if USD** | Half the requested memory; listed out of stock when researched. A lower-cost comparison only if the selected model fits and service is suitable |

Sources: [MetalCloud pricing](https://www.metalcloud.space/) and [MacWeb Mac Studio offers](https://macweb.com/macstudio). These public offers are market references, not approved suppliers or institutional quotes. Do not use their advertised prices as proof of contractual availability or compliance.

At the published 512GB monthly rate, one reserved host would cost approximately **A$203,703 over three years**; two would cost **A$407,406**, before tax and extras, holding price and exchange rate constant. This is one provider's reference price; seek lower-cost offers and compare the required teaching performance.

A generic cloud server advertised with 512GB of system RAM is not necessarily a substitute: the selected model also needs suitable accelerated processing and accessible accelerator memory. Equally, an eight-GPU server may offer far more computing power than a Mac and serve a different number of users. Neither total RAM nor the price of a much larger GPU system establishes equivalent WorkReady capacity. Compare measured service and required availability.

### Simple financial model

Use a consistent basis excluding recoverable GST; Finance must confirm local GST recovery and the treatment of overseas charges. Enter the actual quote when available rather than assuming a purchase price.

- **C:** complete quoted local equipment cost.
- **D:** local setup cost minus rental setup cost.
- **R:** monthly rental for comparable teaching capacity.
- **O:** monthly local operating cost minus rental operating cost, excluding the rental charge itself.
- **N:** comparison period in months, initially 36.

**Net saving from ownership = N × (R − O) − (C + D).**

**Payback in months = (C + D) ÷ (R − O)**, provided monthly savings and the initial investment are positive.

**Simple ROI = net saving ÷ (C + D) × 100%**, for a positive initial investment.

This is an undiscounted savings calculation, not revenue or an annualised investment return. It excludes research benefits, resale, financing, inflation, and tax depreciation. Staff time for the application, model administration, and data governance exists in both options; include only the difference here, while retaining both full operating budgets in the final cost comparison. Renting a bare machine does not remove software-support work.

| Illustrative monthly rental for suitable capacity | Monthly saving before equipment and setup | Three-year saving before equipment and setup |
|---|---:|---:|
| A$1,000 | A$750 | A$27,000 |
| A$1,500 | A$1,250 | A$45,000 |
| A$2,500 | A$2,250 | A$81,000 |

All rows assume O = A$250/month and 36 months of continuous rental. They are sensitivity examples, not quotes, equipment valuations, or proposed funding limits. Subtract C + D from the last column to calculate net saving. Every extra A$100/month of local operating cost reduces the three-year saving by A$3,600; every extra A$1,000 of equipment or additional setup cost reduces it by A$1,000.

For the middle row, **payback = (C + D) ÷ A$1,250 months**, and **three-year ROI = [A$45,000 − (C + D)] ÷ (C + D) × 100%**. These produce a specific result once the procurement and setup costs are entered.

The monthly rental break-even point is **(C + D) ÷ 36 + O** over three years, or **(C + D) ÷ 60 + O** over five years, assuming continued suitability. Calculate each configuration separately; two computers have different purchase and support costs. A later second purchase requires a comparison from its own purchase date.

### Teaching periods rather than continuous rental

Annual billing must match the actual availability required. For rental during six months each year over three years, use **net saving = 18 × R − 36 × O − (C + D)**. At illustrative R = A$1,500 and O = A$250, this leaves **A$18,000 before equipment and additional setup costs**, compared with A$45,000 for continuous rental. This retains a year-round operating difference for illustration; use the actual seasonal costs and support requirements in the final model.

For a short-hours illustration, one host used for 10 billable hours each week over 24 teaching weeks costs about **A$3,151 per year**, or **A$9,454 over three years**, at the listed hourly reference rate. That can favour rental before extras. It assumes the provider supports that schedule and that model loading, storage, booking, and access outside class do not add material charges. It offers much less availability than keeping a machine ready throughout the year.

WorkReady needs its own measured schedule: include student access outside classes, automated simulation activity, preparation, and maintenance cover. Research use is excluded from the financial justification above. An efficient smaller model or metered external AI service may also change the result; evaluate those against the same teaching quality and data requirements.

## F. Data location and control when using rented equipment

Self-hosting describes who runs the AI model; it does not specify who owns the building or computer. A dedicated rented Mac with administrator access can run our chosen model without a separate model-provider API. As a concrete example, AI KIZAI advertises a dedicated M3 Ultra / 512GB machine in Kobe, Japan, with administrator access and support for installing Ollama or MLX. It advertises only one machine, so it does not establish availability of a two-host teaching service. [AI KIZAI service description](https://ai-kizai.com/)

The data path is:

- **On campus:** student → University application → University model server → student.
- **Self-hosted on rental:** student → application → rented model server → student. Prompts and any supplied history/documents enter the hosting environment; they need not go onward to a model vendor.
- **External AI API:** student → application → model provider → student. Hosting the application on a private server does not keep the API request local.

Responses travel back to the application or browser, and any enabled logging, backups, search, monitoring, or additional AI services can create further data flows. Verify all of them before describing the service as local-only. Ollama distinguishes locally run models from its cloud features and provides a setting to disable cloud functions. [Ollama local/cloud behaviour](https://docs.ollama.com/faq)

Control of installed software is different from control of the hosting infrastructure. AWS's shared-responsibility explanation illustrates this distinction: customers manage their applications and relevant system configuration while the provider manages underlying cloud facilities and infrastructure. Each shortlisted host's own terms must establish the actual division of responsibility. [AWS shared-responsibility model](https://aws.amazon.com/compliance/shared-responsibility-model/)

For a rental quote, document processing and backup locations; privileged/support access and audit records; subprocessors; encryption and key control; permitted use of student data; retention and verified deletion; incident response; and exit/export arrangements. Review whether provider management software captures content. A host's claim that data stays on its machine does not establish that the University has exclusive physical or administrative control.

For on-campus operation, confirm the same record-handling controls within University systems, protect model endpoints, manage administrator privileges, and restrict unapproved outbound AI traffic. The proposal seeks direct control over the deployed model and student-data handling, with accountable University operation rather than an absolute claim that no risk remains.

## G. Project evidence and operational limits

The [WorkReady system map](../../workready/workready-api/SYSTEM.md) describes the student journey and AI activity. The [deployment guide](../../workready/workready-deploy/README.md) describes Caddy static serving, FastAPI, and a single SQLite database. [Portal polling](../../workready/workready-portal/app.js) and [lunchroom generation](../../workready/workready-api/workready_api/lunchroom_chat.py) show why some browser activity triggers additional AI work.

The [local release evidence](../../workready/workready-deploy/PRIVACY-RELEASE.md) records functional and privacy checks, while stating that the changes were not deployed as part of that release and that no production concurrency benchmark was established. Prior chatbot experience is internally reported. Historical message totals have been omitted from the funding argument because supporting usage exports were not available for this review.

The teaching deployment will retain expiring student sessions and record-ownership checks alongside network access controls. Commissioning will review staff identity, protected backups, attachment recovery and classroom login limits. Additional API workers require a separate review of process-local request limits.

The supplied retention setting is 120 days of inactivity with an operator-triggered purge, not automatic deletion. Agree record retention and backup expiry, check deletion, review model licences for institutional use, and retain lecturer oversight of grading. Student research requires the relevant ethics process where applicable.

For the local-only pilot, configure approved local model endpoints, disable cloud inference and external search, and verify outbound data flows, including any separate hiring-desk chatbot. [WorkReady provider configuration](../../workready/workready-api/README.md)
