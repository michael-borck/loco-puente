#!/usr/bin/env bash
# course-mode — flip the stack between everyday state and course-day state.
#
# WHY THIS EXISTS: a course day needs a handful of changes that are all wrong
# for the other 180 days of the year, and reverting them by hand (or worse, by
# `git checkout`) either misses something or overwrites things that should
# stay. This script is COMMITTED, so it survives any checkout, and both
# directions are idempotent — running `on` twice is harmless.
#
# What ON changes (OFF reverses every line):
#   * puente.yml librechat.models        -> the course model (thinking is
#        already forced off globally by disable_thinking; this swap does not
#        touch that flag)
#   * puente.yml registration domains    -> open to any address
#   * ComfyUI + SwarmUI containers       -> stopped (VRAM for Ollama)
#   * Ollama parallel slots              -> 4, via a systemd drop-in (sudo).
#        NOTE 2026-10-27: qwen3.5's runner caps at ONE sequence regardless
#        (hybrid-attention arch) — see 20-course-day.conf. Harmless no-op for
#        qwen3.5; engages for standard-attention models (llama/gemma).
#   * LibreChat login banner             -> "deleted tomorrow" notice (Mongo)
#   * librechat.yaml                     -> regenerated via chat-window.sh
#        close, so the picker changes are live but the chat stays in whatever
#        open/closed state the lab schedule put it in
#
# What ON does NOT touch: the Anthropic key schedule (cron owns open/close),
# thinking_comparison, the banner text (it says "deleted tomorrow" — that is
# the course-day promise), and the 10-classroom.conf Ollama drop-in.
#
# NEXT TIME (six months on): check the KNOBS below still name real things —
# model tags change, domains change — then run:
#   deploy/course-mode.sh on      # morning of the course
#   deploy/course-mode.sh off     # after, or the next working day
#   deploy/course-mode.sh status  # anytime, prints the current state
# The sudo prompt inside `on`/`off` is the systemd drop-in install/remove.
#
# KNOWN LIMITATION: the puente.yml edits are a pyyaml load/dump round-trip,
# which drops comments (same as puente's own `save_config` on every `puente
# enable`). The curated comments live in git — after a toggle, `git diff
# puente.yml` shows only the real value changes; `git checkout -- puente.yml`
# restores comments at the cost of the values.
#
# Usage: course-mode.sh on|off|status
set -euo pipefail

REPO="${PUENTE_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PUENTE_DATA_DIR="${PUENTE_DATA_DIR:-$HOME/.puente}"
LOG="$PUENTE_DATA_DIR/course-mode.log"
CHAT_WINDOW="$REPO/deploy/chat-window.sh"

# ---- THE KNOBS — review these before every course day --------------------
COURSE_MODEL="llama3.1:latest" # picker model on course day; llama-arch so the 4-slot drop-in actually engages (qwen3.5 caps at 1 sequence — see 20-course-day.conf)
STEADY_MODEL="gemma4:12b"      # everyday picker model
# Course day = any email may register. Steady state = Curtin only.
STEADY_DOMAINS=(curtin.edu.au student.curtin.edu.au postgrad.curtin.edu.au postgraduate.curtin.edu.au)
BANNER_ID="course-notice"
BANNER_TEXT="Course tool for today. Chats are stored on Michael's server and deleted tomorrow. Don't paste anything confidential."
GPU_APPS="puente-comfyui puente-swarmui"   # stopped on course day
OLLAMA_CONF_SRC="$REPO/deploy/ollama-classroom/20-course-day.conf"
OLLAMA_CONF_DST="/etc/systemd/system/ollama.service.d/20-course-day.conf"
# ---------------------------------------------------------------------------

PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY=python3   # best effort; pyyaml needed for the yaml edits

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$1" | tee -a "$LOG"; }

# Read/write the two LibreChat values through pydantic-shaped yaml so the file
# stays exactly as `puente` itself writes it (safe_dump, sort_keys=False —
# same as puente's save_config).
lc_models() { "$PY" -c 'import yaml; print("\n".join(yaml.safe_load(open("'"$REPO/puente.yml"'"))["services"]["librechat"]["models"] or []))'; }

set_course_yaml() {
  "$PY" - "$REPO/puente.yml" "$COURSE_MODEL" <<'PYEOF'
import sys, yaml
p, model = sys.argv[1], sys.argv[2]
c = yaml.safe_load(open(p))
lc = c["services"]["librechat"]
lc["models"] = [model]
lc["allowed_registration_domains"] = []
yaml.safe_dump(c, open(p, "w"), sort_keys=False)
PYEOF
}

set_steady_yaml() {
  "$PY" - "$REPO/puente.yml" "$STEADY_MODEL" "${STEADY_DOMAINS[@]}" <<'PYEOF'
import sys, yaml
p, model, domains = sys.argv[1], sys.argv[2], sys.argv[3:]
c = yaml.safe_load(open(p))
lc = c["services"]["librechat"]
lc["models"] = [model]
lc["allowed_registration_domains"] = domains
yaml.safe_dump(c, open(p, "w"), sort_keys=False)
PYEOF
}

banner_install() {
  # Escape for a JS single-quoted string: backslashes first, then quotes
  # (the message contains apostrophes — "Michael's", "Don't").
  local msg="${BANNER_TEXT//\\/\\\\}"; msg="${msg//\'/\\\'}"
  docker exec puente-librechat-mongo mongosh --quiet LibreChat --eval "
    db.banners.deleteOne({bannerId: '$BANNER_ID'});
    db.banners.insertOne({bannerId: '$BANNER_ID', message: '$msg',
      displayFrom: new Date(), displayTo: null, type: 'banner',
      isPublic: true, persistable: true, createdAt: new Date(), updatedAt: new Date()});
  " >/dev/null
  log "  banner '$BANNER_ID' installed (public, non-dismissible)"
}

banner_remove() {
  docker exec puente-librechat-mongo mongosh --quiet LibreChat --eval \
    "db.banners.deleteOne({bannerId: '$BANNER_ID'});" >/dev/null
  log "  banner '$BANNER_ID' removed"
}

regen_librechat() {
  # chat-window.sh close regenerates librechat.yaml AND recreates the
  # container (the config digest label changes), keeping the lab CLOSED —
  # cron still owns open/close, so course-mode never opens the chat itself.
  "$CHAT_WINDOW" close >>"$LOG" 2>&1
  log "  librechat.yaml regenerated (picker + registration live)"
}

do_on() {
  log "COURSE MODE ON"
  set_course_yaml
  log "  puente.yml: model=$COURSE_MODEL, registration open to any domain"
  for app in $GPU_APPS; do
    if [ "$(docker inspect -f '{{.State.Running}}' "$app" 2>/dev/null)" = "true" ]; then
      docker stop "$app" >/dev/null
      log "  stopped $app"
    fi
  done
  sudo sh -c "cp '$OLLAMA_CONF_SRC' '$OLLAMA_CONF_DST' && systemctl daemon-reload && systemctl restart ollama"
  log "  ollama: 4 parallel slots installed ($OLLAMA_CONF_DST), restarted"
  banner_install
  regen_librechat
  # The ollama restart above evicted any resident models; reload the course
  # model + titler so the first participant doesn't wait for a cold load.
  "$CHAT_WINDOW" warm >>"$LOG" 2>&1 || log "  WARN warming failed — models load on first use"
  log "COURSE MODE ON — done."
}

do_off() {
  log "COURSE MODE OFF"
  set_steady_yaml
  log "  puente.yml: model=$STEADY_MODEL, registration back to ${STEADY_DOMAINS[*]}"
  for app in $GPU_APPS; do
    if [ "$(docker inspect -f '{{.State.Running}}' "$app" 2>/dev/null)" != "true" ]; then
      docker start "$app" >/dev/null
      log "  started $app"
    fi
  done
  sudo sh -c "rm -f '$OLLAMA_CONF_DST' && systemctl daemon-reload && systemctl restart ollama"
  log "  ollama: course-day drop-in removed, restarted (back to 1 slot)"
  banner_remove
  regen_librechat
  log "COURSE MODE OFF — done."
}

do_status() {
  local model domains conf banner mode down=""
  # status is read-only and must not die on a missing venv/yaml — degrade.
  model="$(lc_models 2>/dev/null | head -1)" || model="(unknown)"
  domains="$("$PY" -c 'import yaml; print(len(yaml.safe_load(open("'"$REPO/puente.yml"'"))["services"]["librechat"]["allowed_registration_domains"] or []))' 2>/dev/null)" || domains="(unknown)"
  conf="no"; [ -f "$OLLAMA_CONF_DST" ] && conf="yes"
  for app in $GPU_APPS; do
    [ "$(docker inspect -f '{{.State.Running}}' "$app" 2>/dev/null)" = "true" ] && down="$down $app"
  done
  banner="installed"
  docker exec puente-librechat-mongo mongosh --quiet LibreChat --eval \
    "print(db.banners.countDocuments({bannerId: '$BANNER_ID'}));" 2>/dev/null | grep -q '^1$' || banner="absent"
  if [ "$model" = "$COURSE_MODEL" ] && [ "$domains" = "0" ] && [ "$conf" = "yes" ] && [ "$banner" = "installed" ]; then
    mode="ON"
  elif [ "$model" = "$STEADY_MODEL" ] && [ "$domains" != "0" ] && [ "$conf" = "no" ] && [ "$banner" = "absent" ]; then
    mode="OFF"
  else
    mode="MIXED — reconcile below"
  fi
  echo "course-mode: $mode"
  echo "  picker model:          $model"
  echo "  registration domains:  restricted to $domains domain(s)"
  echo "  4-slot ollama drop-in: $conf"
  echo "  GPU apps running:      ${down:-none}"
  echo "  login banner:          $banner"
}

case "${1:-}" in
  on)     do_on ;;
  off)    do_off ;;
  status) do_status ;;
  *) echo "Usage: $0 on|off|status" >&2; exit 2 ;;
esac
