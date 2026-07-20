#!/usr/bin/env bash
# Free ComfyUI's VRAM after it has been idle for a while.
#
# WHY: ComfyUI holds its models resident indefinitely — it was observed sitting
# on 18GB of the 24GB 3090 after 4 days at 0% utilization. That leaves Ollama
# (sharing GPU 0) under 1GB of headroom, so every LibreChat model switch has to
# fully evict and reload from disk instead of keeping two models resident. The
# chat feels slow because the image generator is squatting on the card.
#
# WHAT: polls ComfyUI's queue; once it has been empty for IDLE_SECS, POSTs to
# /free to unload models. ComfyUI reloads on the next generation (a one-time
# few-second cost paid by whoever generates next).
#
# WHY NOT `docker restart puente-comfyui`: a restart drops SwarmUI's connection
# to its external-ComfyUI backend, which can latch `errored` (the "No backends
# available!" failure). /free leaves the process up, so SwarmUI never notices.
# /free is also safe to call mid-generation — ComfyUI queues it rather than
# dropping a model out from under a running job — so this needs no locking
# beyond the queue check below.
set -euo pipefail

COMFY_URL="${COMFY_URL:-http://localhost:8188}"
IDLE_SECS="${IDLE_SECS:-1800}"  # 30 min
# Tracks when the queue was last seen busy. /history is NOT usable for this —
# it is wiped on container restart, which would read as "idle forever" and
# unload a model that was just loaded.
STATE="${STATE:-/var/tmp/comfyui-idle-unload.stamp}"

now=$(date +%s)

# Unreachable ComfyUI (down, restarting) is not an error worth alerting on —
# there is also nothing loaded to free. Exit quietly and retry next tick.
queue=$(curl -sf --max-time 5 "$COMFY_URL/queue" 2>/dev/null) || exit 0

# Busy = anything running or pending. Touch the stamp and reset the idle clock.
if ! grep -q '"queue_running": \[\], "queue_pending": \[\]' <<<"$(tr -d '\n' <<<"$queue")"; then
    echo "$now" > "$STATE"
    exit 0
fi

# Idle. First observation just starts the clock — don't unload immediately, or
# a restart of this timer would free a model seconds after someone loaded it.
if [[ ! -f "$STATE" ]]; then
    echo "$now" > "$STATE"
    exit 0
fi

last_busy=$(<"$STATE")
idle_for=$(( now - last_busy ))

if (( idle_for < IDLE_SECS )); then
    exit 0
fi

# Nothing loaded => nothing to free. Skip the POST so the log stays meaningful:
# every "freed" line below corresponds to VRAM actually being released.
vram_before=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 0 2>/dev/null || echo 0)

curl -sf --max-time 15 -X POST "$COMFY_URL/free" \
    -H 'Content-Type: application/json' \
    -d '{"unload_models":true,"free_memory":true}' >/dev/null 2>&1 || {
    echo "comfyui-idle-unload: /free failed (ComfyUI up but not accepting) — will retry"
    exit 0
}

sleep 3  # let the allocator actually release before measuring
vram_after=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 0 2>/dev/null || echo 0)

echo "comfyui-idle-unload: idle ${idle_for}s — freed, GPU0 ${vram_before}MiB -> ${vram_after}MiB"

# Reset so the next unload waits another full idle window rather than firing
# every tick while the queue stays empty.
echo "$now" > "$STATE"
