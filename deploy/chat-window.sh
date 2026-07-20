#!/usr/bin/env bash
# chat-window — open/close LibreChat for lab sessions.
#
# Closing stops the container outright: nothing listens on 3080, so
# chat.locopuente.org returns 502 and the Anthropic key is unreachable.
# Conversations live in Mongo (a separate container, left running), so
# nothing is lost across a close/open cycle.
#
# Usage: chat-window.sh open|close|status
# Cron:  0 14 * * 1 /home/michael/loco-puente/deploy/chat-window.sh open
set -euo pipefail

APP=puente-librechat
DB=puente-librechat-mongo
LOG=/home/michael/.puente/chat-window.log

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$1" | tee -a "$LOG"; }

case "${1:-}" in
  open)
    # Mongo first — the app exits at boot if it can't reach the DB.
    docker start "$DB" >/dev/null 2>&1 || true
    docker start "$APP" >/dev/null
    # Don't report success until it actually serves; boot takes ~20-30s.
    for _ in $(seq 1 30); do
      if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:3080/ 2>/dev/null)" = "200" ]; then
        log "OPEN — LibreChat serving on 3080"
        exit 0
      fi
      sleep 2
    done
    log "OPEN FAILED — container started but not serving after 60s"
    exit 1
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
    echo "Usage: $0 open|close|status" >&2
    exit 2
    ;;
esac
