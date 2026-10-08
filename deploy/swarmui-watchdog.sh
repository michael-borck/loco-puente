#!/usr/bin/env bash
# Self-heal SwarmUI ↔ ComfyUI image generation. Two observed failure modes:
#
# (1) SwarmUI's external-ComfyUI backend latched `errored` (the startup race —
#     SwarmUI probes once and never retries) or latched after a ComfyUI
#     restart. Fixed by SwarmUI's RestartBackends API.
# (2) CUDA gone stale inside a long-lived container — observed 2026-09-07 after
#     ~7 days uptime: host GPUs fine, driver libs matched, yet in-container
#     nvidia-smi "Failed to initialize NVML" and torch "No CUDA GPUs are
#     available", so every model load failed with a misleading OOM error.
#     Only a container restart re-establishes device access.
#
# Runs every 10 min via swarmui-watchdog.timer; quiet no-op when healthy.
# Never restarts a container while ComfyUI has a job running.
set -euo pipefail

SWARM_CONTAINER="${SWARM_CONTAINER:-puente-swarmui}"
COMFY_CONTAINER="${COMFY_CONTAINER:-puente-comfyui}"
# ComfyUI's torch lives in a runtime venv owned by the `comfy` user, not root.
COMFY_VENV_PY="${COMFY_VENV_PY:-/comfy/mnt/venv/bin/python3}"

swarm_state()  { docker inspect -f '{{.State.Status}}' "$SWARM_CONTAINER" 2>/dev/null || true; }
comfy_state()  { docker inspect -f '{{.State.Status}}' "$COMFY_CONTAINER" 2>/dev/null || true; }
comfy_healthy() { [ "$(docker inspect -f '{{.State.Health.Status}}' "$COMFY_CONTAINER" 2>/dev/null || true)" = healthy ]; }

swarm_api() { # <API method> <session id>
    docker exec "$SWARM_CONTAINER" curl -sf --max-time 10 -X POST \
        "http://localhost:7801/API/$1" \
        -H 'Content-Type: application/json' \
        -d "{\"session_id\":\"$2\"}"
}

comfy_idle() {
    # Same busy-detection as comfyui-idle-unload.sh: anything running or
    # pending means a job we must not kill.
    local queue
    queue=$(docker exec "$COMFY_CONTAINER" curl -sf --max-time 5 \
        http://localhost:8188/queue 2>/dev/null | tr -d '\n') || return 1
    grep -q '"queue_running": \[\], "queue_pending": \[\]' <<<"$queue"
}

# Containers not up at all is a docker/compose problem — out of scope here.
[ "$(comfy_state)" = running ] && [ "$(swarm_state)" = running ] || exit 0

# --- Mode 2: stale CUDA inside the ComfyUI container. Check this first: with
# CUDA dead, RestartBackends can never succeed, so healing mode 1 before this
# would just burn the tick. ---
cuda_gpus=$(docker exec -u comfy "$COMFY_CONTAINER" "$COMFY_VENV_PY" -c \
    "import torch; print(torch.cuda.device_count())" 2>/dev/null || echo 0)
if [ "${cuda_gpus:-0}" -eq 0 ]; then
    if comfy_idle; then
        echo "swarmui-watchdog: CUDA dead in $COMFY_CONTAINER (torch sees 0 GPUs) — restarting $COMFY_CONTAINER + $SWARM_CONTAINER"
        docker restart "$COMFY_CONTAINER" "$SWARM_CONTAINER" >/dev/null
        # ComfyUI's healthcheck gates whether its API is really up; give it
        # several minutes (node imports are slow on this box) before healing
        # the backend below.
        for _ in $(seq 1 48); do
            comfy_healthy && break
            sleep 5
        done
    else
        echo "swarmui-watchdog: CUDA dead but ComfyUI has a job — deferring restart to next tick"
        exit 0
    fi
fi

# --- Mode 1: backend latched `errored`. Also the post-restart heal for mode 2
# (the restart re-arms the startup race). ---
session=""
for _ in $(seq 1 30); do
    session=$(swarm_api GetNewSession "" 2>/dev/null | \
        sed -n 's/.*"session_id":"\([^"]*\)".*/\1/p') || true
    [ -n "$session" ] && break
    sleep 2
done
[ -n "$session" ] || { echo "swarmui-watchdog: SwarmUI not answering GetNewSession — skipping (next tick retries)"; exit 0; }

backends=$(swarm_api ListBackends "$session" 2>/dev/null) || exit 0
case "$backends" in
    *'"status":"errored"'*) ;;
    *) exit 0 ;;  # healthy — the overwhelmingly common path; stay quiet
esac

echo "swarmui-watchdog: SwarmUI backend errored — RestartBackends"
for attempt in 1 2 3; do
    swarm_api RestartBackends "$session" >/dev/null 2>&1 || true
    for _ in $(seq 1 15); do
        sleep 4
        backends=$(swarm_api ListBackends "$session" 2>/dev/null) || backends=""
        case "$backends" in
            *'"status":"running"'*)
                echo "swarmui-watchdog: backend recovered (running)"
                exit 0
                ;;
            *'"status":"errored"'*)
                break  # re-latched — fire another restart
                ;;
        esac
    done
done
echo "swarmui-watchdog: backend still errored after 3 attempts — will retry next tick"
exit 0
