# Demand-driven residency

Which models stay in memory, decided by what people are **actually doing** rather
than by guessing what they might ask next.

## Why demand, not classification

[`decide.py`](decision-layer.md) answers "which capability does this request
want?". That is a different question from "what should stay loaded", and the
second is better served by evidence:

- **The evidence already exists.** Ollama's `/api/ps` reports which models are
  resident and when each expires. ComfyUI has a job queue. Caddy has access
  logs. Nothing has to be inferred.
- **Prediction is speculative.** A router that guesses correctly three turns
  early has saved nothing — it ran a model that was not being used. One that
  guesses wrong evicts the model somebody was about to use, which on a
  single-card box is the entire cost.
- **It costs a dependency to be wrong.** Classification needs a model resident
  in order to make load decisions. Observing demand needs a log line.

So classification earns its place *upstream* — deciding which capability a
request wants before anything is loaded — while residency follows usage.

## The asymmetry that shapes everything

`residency_plan` is backend-agnostic: it says *what* should be resident, and
each backend decides *how*. What it cannot be is uniform, because eviction costs
differ by two orders of magnitude.

| Backend | Evict mechanism | Cost of an eviction |
| --- | --- | --- |
| Ollama | per-request `keep_alive: 0` | **~none** — weights unload, server stays up |
| llama.cpp | stop the container | minutes — no hot-swap; one server serves one GGUF |
| Containers | stop the container | minutes — weights reload from disk |

Ollama evicts cheaply because it already implements a residency TTL natively.
llama.cpp deliberately does not hot-swap models, so its load/unload is
container lifecycle and therefore **sticky**. A policy that thrashed it would be
worse than no policy at all.

That asymmetry is why `Demand` carries `evict_cost`. Something free to evict
releases after 30 idle minutes; something expensive waits 180.

## Working of the policy

```
keep     gemma4:12b     idle 5m, under the 180m threshold
release  qwen3.5:0.8b   idle 200m — past the 30m threshold for a free-to-evict item
release  llama3.1       idle 90m — past the 30m threshold for a free-to-evict item
keep     comfyui        idle 45m, under the 180m threshold
keep     voicebox       used 8x recently — release would thrash
```

Three properties, all deliberate:

- **Bias is one-directional.** An eviction that is wrong costs more than one that
  is merely early, so `never used` keeps rather than releases. Destroying
  something on a guess is the failure mode worth avoiding.
- **Repeated use protects.** A service people return to all session should not
  be released between visits, however long each gap was.
- **Every action carries a reason.** A plan an operator cannot explain is one
  they will not trust to run unattended.

Thresholds are configuration, not hardcoded behaviour — the default is
conservative because a card that cannot hold two models needs a shorter one, and
an operator should not have to edit source to get it.

## Not built yet

`residency_plan` decides. Nothing acts on it — there is no scheduler, no
periodic evaluation, and no adapter that actually evicts. That is deliberate for
a first slice: the policy is pure and testable without touching a running
service, and the actuation side wants a real load test before it stops anything
on a live box.

Reading demand is implemented (`ollama_demand`); container demand is a stub
taking an explicit idle time, because there is no trustworthy activity signal
from a container without adding one.

## Honest limits

- **`recent_uses` is not measured yet.** `ollama_demand` infers it from
  residency. Real counts want an access log or a counter, which Caddy already
  has and nothing reads yet.
- **"Idle" for a container is an assumption.** ComfyUI's queue is the honest
  signal; "was the container up" is not, and conflates them would mean never
  releasing anything.
- **Release is not the same as unload.** Stopping a container makes the service
  unavailable to the next request. True residency needs a load step that is not
  written yet.