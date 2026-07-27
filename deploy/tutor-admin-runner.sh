#!/usr/bin/env bash
# tutor-admin-runner — the privileged half of the tutor admin tool.
#
# WHY THIS IS A SEPARATE PROCESS.
# Creating an account or sending an invite means running LibreChat's own npm
# scripts inside its container: they hash passwords and mint invite tokens with
# LibreChat's internals, and a reimplementation would drift the moment upstream
# changes either. Reaching them needs `docker exec`, which needs the Docker
# socket, and a writable Docker socket is root on the host.
#
# The web app is exposed to the internet. Giving it a socket would mean one bug
# there escalates to the whole machine — the Anthropic key, every other service,
# everything. So the web app gets NO socket. It writes a JSON request into a
# spool directory; this script owns the socket, validates the request, and runs
# the script. The privileged half is this file: two verbs, no network, no
# request body reaching a shell unquoted.
#
# The worst a compromised web app can do is queue account creations — which it
# could already make legitimately through its own UI.
#
# Usage: tutor-admin-runner.sh [--once]     (systemd timer passes --once)
set -euo pipefail

SPOOL="${TUTOR_ADMIN_SPOOL:-$HOME/.puente/tutor-admin/spool}"
APP="${LIBRECHAT_CONTAINER:-puente-librechat}"
LOG="${TUTOR_ADMIN_LOG:-$HOME/.puente/tutor-admin/runner.log}"

mkdir -p "$SPOOL" "$(dirname "$LOG")"

log() { printf '%s %s\n' "$(date -Is)" "$*" >> "$LOG"; }

# Answer a request with a result file the web app is polling for. Written to
# .tmp then renamed so the reader never catches it half-written.
reply() {
  local id="$1" ok="$2" detail="$3"
  local out="$SPOOL/$id.result"
  jq -n --argjson ok "$ok" --arg detail "$detail" '{ok:$ok,detail:$detail}' \
    > "$out.tmp" 2>/dev/null || printf '{"ok":%s,"detail":"(jq missing)"}' "$ok" > "$out.tmp"
  mv "$out.tmp" "$out"
}

# Domains are re-checked HERE as well as in the web app. The web app's check is
# a usability nicety; this one is the control. A request arriving in the spool
# is untrusted input regardless of what wrote it.
ALLOWED="${TUTOR_ADMIN_DOMAINS:-curtin.edu.au,student.curtin.edu.au,postgrad.curtin.edu.au}"

domain_ok() {
  local domain="${1##*@}"
  local d
  IFS=, read -ra list <<< "$ALLOWED"
  for d in "${list[@]}"; do
    [ "${domain,,}" = "${d// /}" ] && return 0
  done
  return 1
}

process_one() {
  local file="$1"
  local id verb email name username password
  id=$(jq -r '.id // empty' < "$file")
  verb=$(jq -r '.verb // empty' < "$file")
  email=$(jq -r '.email // empty' < "$file")

  # A request whose id we cannot read cannot be answered; just bin it.
  if [ -z "$id" ]; then log "malformed request, no id: $file"; rm -f "$file"; return; fi

  # Validate before doing anything. Note every value below is passed to docker
  # as a separate argv element, never interpolated into a shell string.
  if ! printf '%s' "$email" | grep -qE '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'; then
    reply "$id" false "invalid email address"; log "reject $id: bad email"; rm -f "$file"; return
  fi
  if ! domain_ok "$email"; then
    reply "$id" false "domain not permitted"; log "reject $id: domain $email"; rm -f "$file"; return
  fi

  local out rc=0
  case "$verb" in
    invite)
      # No -i: the email is supplied as an argument, so it never prompts. An
      # open stdin here would just be another way to hang.
      out=$(docker exec "$APP" npm run invite-user "$email" 2>&1) || rc=$?
      ;;
    create)
      name=$(jq -r '.name // empty' < "$file")
      username=$(jq -r '.username // empty' < "$file")
      password=$(jq -r '.password // empty' < "$file")
      if [ -z "$name" ] || [ -z "$username" ] || [ ${#password} -lt 8 ]; then
        reply "$id" false "name, username and an 8+ character password are required"
        log "reject $id: incomplete create"; rm -f "$file"; return
      fi
      # Pass the password as the 4th argument and set --email-verified
      # explicitly, so create-user asks NOTHING and needs no stdin at all.
      #
      # Feeding answers to its prompts instead does not work: it asks for the
      # password ONCE (not twice, despite the confirm-style wording) and then
      # asks whether the email is verified, so a fixed here-string desynchronises
      # and `docker exec -i` hangs forever holding the queue. Upstream warns
      # that an argv password is visible in the process list; that is acceptable
      # here because this runs on the operator's own host for a few seconds,
      # and the alternative is an unattended process that deadlocks mid-class.
      out=$(docker exec "$APP" npm run create-user -- \
              "$email" "$name" "$username" "$password" --email-verified=true 2>&1) || rc=$?
      ;;
    *)
      reply "$id" false "unknown verb"; log "reject $id: verb '$verb'"; rm -f "$file"; return
      ;;
  esac

  # The request file holds a plaintext password — remove it before anything else
  # can read it, and never let it reach the log.
  rm -f "$file"

  # npm exits 0 on some upstream failures ("A user with that email already
  # exists!" is printed, then silentExit(1)) so check the text too.
  # create-user echoes the whole resolved librechat.yaml before it does anything,
  # so the raw output is kilobytes of ANSI-coloured config. Keep only lines that
  # say what happened, and strip escape codes — this text is stored in the audit
  # log and shown to a tutor.
  local summary
  summary=$(printf '%s' "$out" \
    | sed 's/\x1b\[[0-9;]*m//g' \
    | grep -iE 'success|created|invit|error|already exists|not enabled|Email verified' \
    | tail -5)
  [ -z "$summary" ] && summary=$(printf '%s' "$out" | sed 's/\x1b\[[0-9;]*m//g' | tail -c 400)

  if [ "$rc" -eq 0 ] && ! printf '%s' "$summary" | grep -qiE '^error|Error:'; then
    reply "$id" true "$summary"
    log "ok $verb $email"
  else
    reply "$id" false "$summary"
    log "FAIL $verb $email (rc=$rc)"
  fi
}

run_pass() {
  shopt -s nullglob
  for f in "$SPOOL"/*.json; do
    process_one "$f"
  done
}

if [ "${1:-}" = "--once" ]; then
  run_pass
else
  # Foreground mode for `systemd` Type=simple or manual debugging.
  while true; do run_pass; sleep 2; done
fi
