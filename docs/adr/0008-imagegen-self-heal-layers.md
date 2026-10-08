# 0008 — Image generation self-heals in layers: reconcile loop, watchdog, weekly restart

**Status:** Accepted (2026-09-07)

## Context

Image generation broke twice in a week, each time expensively:

1. **2026-08-31** — after a cold boot, `puente-boot.service` ran, its reconcile
   fired SwarmUI's `RestartBackends` **once**, polled 60 s, gave up (ComfyUI was
   still importing nodes), and the backend sat `errored` for six days. Every
   generate returned "No backends available!". The unit exits 0 either way, so
   nothing looked wrong.
2. **2026-09-07** — after ~7 days of container uptime, CUDA went stale *inside*
   the ComfyUI container: host GPUs fine, driver libs version-matched, no Xid
   errors, yet in-container NVML failed and torch saw **0 GPUs**. SwarmUI
   reported it as a misleading OOM ("Allocation on device"). Only restarting the
   containers re-established device access.

`reconcile_backends()`'s single `RestartBackends` attempt is the common thread:
it loses whenever ComfyUI is slower to become ready than SwarmUI's probe, and
nothing watches afterward.

## Decision

Three layers, each covering what the one above it gives up on:

1. **`reconcile_backends()` is a rounds loop** — re-fires `RestartBackends`
   while the backend reports `errored`, polling between rounds (~3 min budget).
   Still fired by `puente up` and `puente-boot`.
2. **`deploy/swarmui-watchdog.{sh,service,timer}`** — every 10 min, silent when
   healthy: heals an `errored` backend, and detects stale CUDA
   (`torch.cuda.device_count()` via `docker exec`) and restarts
   `puente-comfyui` + `puente-swarmui` — never with a ComfyUI job in flight.
3. **`deploy/imagegen-weekly-restart.{service,timer}`** — Sunday ~04:30,
   restart both containers, then run the watchdog. Resets the stale-CUDA clock
   before it bites.

## Consequences

- Image gen breaks for minutes, not days: the watchdog's tick bounds recovery.
- A stale-CUDA restart can cost one in-flight generation (the queue check
  narrows this to jobs started seconds before the tick); accepted — the
  alternative was multi-day outages.
- The weekly restart deliberately re-arms the startup race; the watchdog run
  right after it is part of the design, not an accident.
- Operator-facing symptom stays confusing (OOM for stale CUDA, "No backends"
  for the race) — but `docs/service-topology.md` now maps both to causes.

## Alternatives rejected

**Just reboot the box when image gen breaks.** Works for both failure modes but
requires a human to notice, and Ollama/LibreChat lose their resident models for
everyone. The watchdog heals in minutes, unattended.

**Make SwarmUI retry its backend probe itself.** Would fix the race at the
source but means patching SwarmUI (C#) in our image — a fork to maintain for
something a 10-minute watchdog covers. Revisit only if the watchdog ever misses.

**Fix "stale CUDA" at the driver level** (pin driver versions, hold package
upgrades). The 2026-09-07 incident had matching versions and no upgrade trail —
the cause is not established enough to fix upstream, and the restart costs
seconds.
