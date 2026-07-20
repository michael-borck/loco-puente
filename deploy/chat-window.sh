#!/usr/bin/env bash
# chat-window — open/close LibreChat for lab sessions.
#
# Closing stops the container outright: nothing listens on 3080, so
# chat.locopuente.org returns 502 and the Anthropic key is unreachable.
# Conversations live in Mongo (a separate container, left running), so
# nothing is lost across a close/open cycle.
#
# Usage: chat-window.sh open|close|status|warm
# Cron:  0 14 * * 1 /home/michael/loco-puente/deploy/chat-window.sh open
set -euo pipefail

APP=puente-librechat
DB=puente-librechat-mongo
LOG=/home/michael/.puente/chat-window.log

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$1" | tee -a "$LOG"; }

# Preload the classroom models — IN THIS ORDER. Order is load-bearing.
#
# Ollama splits a model across GPUs only when it does not fit on one. Loading
# the VISION model first fills the 3090 (17GB), so qwen3.5:9b no longer fits
# alone and Ollama splits it, putting ~5GB on the 2060S — both stay resident and
# a model switch costs ~0.4s.
#
# Load them the other way round and qwen3.5:9b takes the 3090 by itself (9.5GB,
# 2060S idle); the vision model then cannot fit in what is left, so Ollama
# EVICTS the text model instead of splitting it. Only one survives and every
# switch costs a 13-20s reload — which with 40 students means one person's
# switch stalls the room.
#
# Measured 2026-07-20; see deploy/ollama-classroom/10-classroom.conf.
warm_models() {
  local ollama="${OLLAMA_URL:-http://localhost:11434}"
  for m in qwen2.5vl:7b-16k qwen3.5:9b; do
    if curl -sf --max-time 300 "$ollama/api/generate" \
         -d "{\"model\":\"$m\",\"prompt\":\"hi\",\"stream\":false,\"keep_alive\":\"6h\"}" \
         -o /dev/null 2>/dev/null; then
      log "  warmed $m"
    else
      # Not fatal: the model still loads on first student use, just slowly.
      log "  WARN failed to warm $m — first use will be slow"
    fi
  done
}

case "${1:-}" in
  open)
    # Mongo first — the app exits at boot if it can't reach the DB.
    docker start "$DB" >/dev/null 2>&1 || true
    docker start "$APP" >/dev/null
    # Don't report success until it actually serves; boot takes ~20-30s.
    for _ in $(seq 1 30); do
      if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:3080/ 2>/dev/null)" = "200" ]; then
        log "OPEN — LibreChat serving on 3080"
        warm_models
        exit 0
      fi
      sleep 2
    done
    log "OPEN FAILED — container started but not serving after 60s"
    exit 1
    ;;
  warm)
    # Models only — does NOT open the chat. Called by comfyui-idle-unload's
    # sibling unit ollama-warm.service after Ollama (re)starts, so a reboot or
    # a manual `systemctl restart ollama` restores the two-GPU placement
    # without touching LibreChat's open/closed state. Wiring `open` to Ollama
    # instead would expose the chat — and the Anthropic key — at any hour.
    log "WARM — preloading classroom models"
    warm_models
    ;;
  close)
    docker stop "$APP" >/dev/null
    # Mongo stays up: cheap, holds no open port to the internet, and
    # leaving it running makes the next open faster.
    log "CLOSED — LibreChat stopped (chat.locopuente.org now 502)"
    ;;
  status)
    if [ "$(docker inspect -f '{{.State.Running}}' "$APP" 2>/dev/null)" = "true" ]; then
      echo "OPEN  — $APP running"
    else
      echo "CLOSED — $APP stopped"
    fi
    ;;
  *)
    echo "Usage: $0 open|close|status|warm" >&2
    exit 2
    ;;
esac
