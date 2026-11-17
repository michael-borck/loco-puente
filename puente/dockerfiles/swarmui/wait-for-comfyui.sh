#!/usr/bin/env bash
# Wait for the external ComfyUI backend to answer, then launch SwarmUI.
#
# Why this exists: SwarmUI probes its "ComfyUI API By URL" backend exactly
# four times (~4 seconds total) at startup, then gives up and latches the
# backend into `errored` — every generation then returns "No backends
# available!" until someone hits Restart Backends by hand. When both
# containers start through a single `docker compose up`, the compose file's
# `depends_on: {comfyui: {condition: service_healthy}}` orders them and the
# race can't happen. But after a host reboot, a docker daemon restart, or a
# bare `docker restart` of both containers, each container restarts
# independently via its restart policy with no ordering — and SwarmUI,
# which compiles fast, routinely beats ComfyUI's slow custom-node import.
# This loop is the belt-and-braces for those paths.
#
# Behaviour:
#   - If the backend hostname doesn't resolve at all (ComfyUI service
#     disabled, SwarmUI running standalone), skip the wait and start.
#   - Poll every COMFYUI_WAIT_INTERVAL seconds up to COMFYUI_WAIT_TIMEOUT.
#     On timeout, start SwarmUI anyway — no worse than the old behaviour,
#     and SwarmUI's own retries get one more chance.
#
# Environment:
#   COMFYUI_WAIT_HOST     backend hostname   (default: puente-comfyui)
#   COMFYUI_WAIT_PORT     backend port       (default: 8188)
#   COMFYUI_WAIT_TIMEOUT  max wait seconds   (default: 300)
#   COMFYUI_WAIT_INTERVAL poll interval      (default: 2)

set -u

WAIT_HOST="${COMFYUI_WAIT_HOST:-puente-comfyui}"
WAIT_PORT="${COMFYUI_WAIT_PORT:-8188}"
WAIT_TIMEOUT="${COMFYUI_WAIT_TIMEOUT:-300}"
WAIT_INTERVAL="${COMFYUI_WAIT_INTERVAL:-2}"

if ! getent hosts "$WAIT_HOST" >/dev/null 2>&1; then
    echo "[wait-for-comfyui] host '$WAIT_HOST' does not resolve — starting SwarmUI without waiting."
    exec bash /SwarmUI/launchtools/docker-standard-inner.sh "$@"
fi

echo "[wait-for-comfyui] waiting for http://$WAIT_HOST:$WAIT_PORT (up to ${WAIT_TIMEOUT}s)..."
start=$SECONDS
ok=0
while [ $((SECONDS - start)) -lt "$WAIT_TIMEOUT" ]; do
    if wget -q -O /dev/null --timeout=5 "http://$WAIT_HOST:$WAIT_PORT/" 2>/dev/null; then
        ok=1
        break
    fi
    sleep "$WAIT_INTERVAL"
done

if [ "$ok" -eq 1 ]; then
    echo "[wait-for-comfyui] ComfyUI answering after $((SECONDS - start))s — launching SwarmUI."
else
    echo "[wait-for-comfyui] timed out after ${WAIT_TIMEOUT}s — launching SwarmUI anyway (backend may need Restart Backends)."
fi

exec bash /SwarmUI/launchtools/docker-standard-inner.sh "$@"
