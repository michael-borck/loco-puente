#!/usr/bin/env bash
# chat-window — swap LibreChat's Anthropic key in/out around lab sessions.
#
# LibreChat now stays UP 24/7. Only the Anthropic endpoint is scheduled.
# Students can register and use the local Ollama models at any hour; the Claude
# models appear in the picker at lab open and vanish at close.
#
# Previously this stopped the container outright, purely to keep the Anthropic
# key unreachable — but that also took registration offline, which forced 40
# students to sign up in the first minutes of a lab from one NATed IP and
# tripped LibreChat's per-IP register limiter (see puente.yml).
#
# HOW THE SWAP WORKS — this is a container RECREATE, not a restart.
# ANTHROPIC_API_KEY is baked into the container environment at creation time, so
# it cannot be changed by `docker restart`. `puente up librechat` rebuilds the
# container from puente.yml with the key present (open) or empty (close).
# LibreChat only exposes the Anthropic endpoint when the key is non-empty.
# Cost: ~10s of downtime at each boundary, and in-flight chats drop. Chat
# history lives in Mongo (separate container, always up) so nothing is lost.
#
# THE KEY COMES FROM A FILE, NOT THE ENVIRONMENT.
# Reading it from the ambient env would work interactively and fail silently
# under cron/systemd, where the environment is nearly empty — the same trap that
# produced empty SMTP credentials and unauthenticated 530s from Resend. `open`
# therefore reads ~/.puente/anthropic.key and ABORTS if it is missing or empty,
# rather than quietly opening a lab with no Claude models in the picker.
#
# Usage: chat-window.sh open|close|status|warm
# Cron:  0 14 * * 1 /path/to/loco-puente/deploy/chat-window.sh open
set -euo pipefail

APP=puente-librechat
DB=puente-librechat-mongo

# Host-specific paths, all overridable so this script works on another machine.
# `$HOME` rather than a hardcoded /home/<user>: cron runs with a real HOME, so
# %h-equivalent expansion is reliable here (unlike in the systemd units, where
# the checkout is not necessarily inside $HOME).
PUENTE_HOME="${PUENTE_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PUENTE_DATA_DIR="${PUENTE_DATA_DIR:-${HOME}/.puente}"
LOG="${PUENTE_DATA_DIR}/chat-window.log"
KEY_FILE="${PUENTE_DATA_DIR}/anthropic.key"
# Same cron-safety argument as the Anthropic key. puente's pre_start rewrites
# LibreChat's SMTP env_file on EVERY `up`, resolving this from the ambient
# environment — so if it is unset here, a scheduled open/close would silently
# blank the Resend password and kill verification email and password reset.
RESEND_KEY_FILE="${PUENTE_DATA_DIR}/resend.key"
# Absolute paths: cron runs with a minimal PATH and an arbitrary cwd, and
# `puente` lives in the project venv rather than on the system PATH.
REPO="${PUENTE_HOME}"
PUENTE="${PUENTE_BIN:-$REPO/.venv/bin/puente}"

# PUENTE_CONFIG is exported rather than relying on the `cd` below. Discovery now
# searches upward from the cwd, so the cd is no longer strictly required — but
# the export is the explicit, self-documenting form, and it keeps working if
# discovery ever changes again.
#
# This was a real production failure: `puente up` from cron (cwd = $HOME, no
# puente.yml) exited 1, and because the message went to stdout while the `up`
# calls below sent stdout to /dev/null, `set -e` aborted the script before its
# first log() line. Silent no-op, empty log, lab with no Claude models in the
# picker — from the 2026-07-25 reboot until 2026-07-30.
export PUENTE_CONFIG="${PUENTE_CONFIG:-$REPO/puente.yml}"
cd "$REPO"

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$1" | tee -a "$LOG"; }

# Load the Resend key for any `puente up`, open or close. Not fatal if absent —
# unlike the Anthropic key it does not gate the lab, and failing the close would
# leave the Anthropic key live, which is the opposite of what close is for.
load_resend_key() {
  if [ -r "$RESEND_KEY_FILE" ]; then
    RESEND_API_KEY="$(tr -d '[:space:]' < "$RESEND_KEY_FILE")"
    export RESEND_API_KEY
  elif [ -n "${RESEND_API_KEY:-}" ]; then
    export RESEND_API_KEY  # inherited from an interactive shell
  else
    log "  WARN $RESEND_KEY_FILE missing and RESEND_API_KEY unset — verification email will break on this up"
  fi
}

# Preload the classroom model.
#
# The picker offers ONE local model — whichever puente.yml pins (warm_models
# reads it from there). Thinking is forced off on it (reasoning_effort: none —
# see disable_thinking in puente.yml). qwen3.5:9b as of 2026-10-27 for the
# exec-ed lab, swapped in for gemma4:12b (text+vision+audio in one model);
# deploy/course-mode.sh on|off makes that swap. It fits the 3090 alone, so the old two-GPU load
# ORDER no longer matters: there is no second resident model to split or evict.
# (History: the previous pair, qwen2.5vl:7b-16k + qwen3.5:9b, only co-fit by
# loading the vision model first to force a split onto the 2060S — see the git
# log and deploy/ollama-classroom/10-classroom.conf if that pair ever returns.)
#
# The warm request itself must NOT force thinking on the model, or the keep_alive
# probe pays the thinking cost. reasoning_effort is a /v1 concept; this hits the
# native /api/generate, which does not think unless asked — so a plain prompt is
# already thinking-free here.
warm_models() {
  local ollama="${OLLAMA_URL:-http://localhost:11434}"
  # Warm whatever the LibreChat picker actually offers — the first entry of
  # services.librechat.models in puente.yml — so the preload can never drift
  # from what is served when course-mode swaps the model. puente's own venv
  # has pyyaml; if either is missing, warming is skipped with a warning (the
  # model still loads on first student use, just slowly).
  local m models
  models="$("$PUENTE_HOME/.venv/bin/python" -c 'import sys,yaml; print("\n".join(yaml.safe_load(open(sys.argv[1]))["services"]["librechat"]["models"] or []))' "$REPO/puente.yml" 2>/dev/null)" || models=""
  if [ -z "$models" ]; then
    log "  WARN no models pinned in puente.yml (or venv missing) — nothing to warm"
    return 0
  fi
  for m in $models; do
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
    # Fail before touching the running container: a lab with the chat up but no
    # Claude models is worse than a loud failure here, because it surfaces as
    # confused students mid-session rather than as a cron error.
    if [ ! -r "$KEY_FILE" ]; then
      log "OPEN ABORTED — $KEY_FILE missing or unreadable; refusing to open without the Anthropic key"
      exit 1
    fi
    ANTHROPIC_API_KEY="$(tr -d '[:space:]' < "$KEY_FILE")"
    if [ -z "$ANTHROPIC_API_KEY" ]; then
      log "OPEN ABORTED — $KEY_FILE is empty; refusing to open without the Anthropic key"
      exit 1
    fi
    export ANTHROPIC_API_KEY
    load_resend_key
    # Mongo first — the app exits at boot if it can't reach the DB.
    docker start "$DB" >/dev/null 2>&1 || true
    # Recreates the container with the key baked in. RESEND_API_KEY is passed
    # through too: pre_start rewrites the SMTP env_file on every up, and an
    # unset value there would silently disable verification email.
    # Output goes to $LOG, not /dev/null: puente reports fatal errors (a missing
    # puente.yml, an unreachable Docker socket) on stdout, and discarding them is
    # what made the cwd bug above invisible for five days.
    "$PUENTE" up librechat >>"$LOG" 2>&1
    # Don't report success until it actually serves; boot takes ~20-30s.
    for _ in $(seq 1 30); do
      if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:3080/ 2>/dev/null)" = "200" ]; then
        # Verify the key actually made it in, so a botched open is caught here
        # and not by a student wondering where the Claude models went.
        if docker inspect "$APP" --format '{{range .Config.Env}}{{println .}}{{end}}' \
             2>/dev/null | grep -q '^ANTHROPIC_API_KEY=..*'; then
          log "OPEN — LibreChat serving on 3080 with the Anthropic endpoint live"
        else
          log "OPEN DEGRADED — serving on 3080 but the Anthropic key did NOT reach the container (Ollama models only)"
          warm_models
          exit 1
        fi
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
    # instead would expose the Anthropic key at any hour.
    log "WARM — preloading classroom models"
    warm_models
    ;;
  close)
    # Empty (not unset): puente only emits the ANTHROPIC_API_KEY placeholder
    # when anthropic_key_env is configured, and LibreChat only shows the
    # endpoint when the resulting value is non-empty. Recreating with an empty
    # value is what removes the Claude models from the picker.
    export ANTHROPIC_API_KEY=""
    load_resend_key
    # See the `open` branch: logged rather than discarded so a failed close, which
    # would leave the paid key live, cannot pass silently.
    "$PUENTE" up librechat >>"$LOG" 2>&1
    # Confirm the key is actually gone rather than assuming the recreate worked.
    if docker inspect "$APP" --format '{{range .Config.Env}}{{println .}}{{end}}' \
         2>/dev/null | grep -q '^ANTHROPIC_API_KEY=..*'; then
      log "CLOSE FAILED — Anthropic key still present in $APP; investigate before the next lab"
      exit 1
    fi
    log "CLOSED — Anthropic endpoint removed; LibreChat still serving (registration + Ollama models stay up)"
    ;;
  status)
    if [ "$(docker inspect -f '{{.State.Running}}' "$APP" 2>/dev/null)" != "true" ]; then
      echo "DOWN   — $APP not running"
      exit 0
    fi
    if docker inspect "$APP" --format '{{range .Config.Env}}{{println .}}{{end}}' \
         2>/dev/null | grep -q '^ANTHROPIC_API_KEY=..*'; then
      echo "OPEN   — $APP running WITH the Anthropic key (Claude models live)"
    else
      echo "CLOSED — $APP running WITHOUT the Anthropic key (Ollama only)"
    fi
    ;;
  *)
    echo "Usage: $0 open|close|status|warm" >&2
    exit 2
    ;;
esac
