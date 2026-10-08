#!/usr/bin/env bash
# Apply finite keep-alive to classroom Ollama (drops the permanent VRAM pin).
#
# Installs the edited 10-classroom.conf (OLLAMA_KEEP_ALIVE=3h) and the preload
# unit (no more request-level keep_alive:-1), then restarts ollama — which is
# what actually evicts the currently pinned models (gemma4:12b + the stray
# gemma4:e4b loaded by a LAN client on 2026-08-28).
#
# WARNING: the restart kills any in-flight generation. Run between labs.
set -euo pipefail
cd "${PUENTE_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

echo "== installing drop-in + preload unit (needs sudo) =="
sudo cp deploy/ollama-classroom/10-classroom.conf /etc/systemd/system/ollama.service.d/
sudo cp deploy/ollama-classroom/ollama-preload.service /etc/systemd/system/

echo "== reloading systemd and restarting ollama =="
sudo systemctl daemon-reload
sudo systemctl restart ollama

sleep 2
echo "== resident models after restart (expires_at should be ~3h out, not year 2318) =="
curl -s http://127.0.0.1:11434/api/ps | python3 -m json.tool

echo "== ollama service status =="
systemctl --no-pager status ollama | head -5

echo "== done =="
echo "Optional boot-warm now (rides the 3h TTL): sudo systemctl start ollama-preload"
