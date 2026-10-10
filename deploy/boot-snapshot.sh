#!/usr/bin/env bash
# Capture host state in a form that can be diffed across a reboot.
#
# WHY: a cold boot is the one time this stack's startup ordering gets tested, and
# it is hard to observe in the moment. ADR0008 records two outages that were
# invisible until much later — a SwarmUI backend that latched `errored` for six
# days, and stale in-container CUDA after ~7 days. Both looked healthy from
# outside. Diffing a snapshot taken before the reboot against one taken after
# turns "is it up?" into "did anything fail to come back?".
#
# Usage:
#   ./deploy/boot-snapshot.sh pre        > /tmp/boot-pre.txt
#   sudo reboot
#   ./deploy/boot-snapshot.sh post       > /tmp/boot-post.txt
#   diff -u /tmp/boot-pre.txt /tmp/boot-post.txt
#
# Read-only: reads state, starts and stops nothing.

set -uo pipefail

PHASE="${1:-post}"
PUENTE_HOME="${PUENTE_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PUENTE_CONFIG="${PUENTE_CONFIG:-${PUENTE_HOME}/puente.yml}"
OUT="${OUT:-/tmp/boot-${PHASE}.txt}"

section() { printf '\n===== %s =====\n' "$1"; }
# Never let a probe failure abort the snapshot — a broken thing is exactly what
# we are trying to record.
probe() { "$@" 2>&1 || printf '(command failed: %s)\n' "$*"; }

exec > >(tee "$OUT")

printf 'puente boot snapshot — phase=%s\n' "$PHASE"
printf 'generated: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
printf 'host: %s\n' "$(hostname)"

section "uptime and boot"
probe uptime
printf 'boot time: %s\n' "$(uptime -s 2>/dev/null || who -b 2>/dev/null)"

section "GPU / driver"
# The single most important line for a cold boot. On the 2026-10-10 boot the
# driver was upgraded without a reboot, so this records the mismatch that took
# every GPU service down.
probe nvidia-smi --query-gpu=index,uuid,name,memory.total,driver_version \
  --format=csv,noheader

section "docker containers (running)"
probe docker ps --format '{{.Names}}\t{{.Status}}\t{{.Image}}'

section "docker containers (puente project, all states)"
# Includes Exited/Created, which is where a failed-to-start service shows up.
probe docker compose -f "${PUENTE_DATA_DIR:-$HOME/.puente}/docker-compose.yml" ps -a

section "containers expected but NOT running"
# Diff "enabled in puente.yml" against "running", so a service that silently
# failed to come back is named explicitly rather than inferred from a list.
if command -v python3 >/dev/null && [ -f "$PUENTE_CONFIG" ]; then
  python3 - "$PUENTE_CONFIG" <<'PY'
import subprocess, sys, yaml
try:
    cfg = yaml.safe_load(open(sys.argv[1])) or {}
except Exception as e:
    print(f"(could not parse config: {e})"); sys.exit()
svc = (cfg.get("services") or {})
running = set()
try:
    out = subprocess.run(["docker", "ps", "--format", "{{.Names}}"],
                         capture_output=True, text=True, timeout=20).stdout
    running = {n.strip() for n in out.splitlines() if n.strip()}
except Exception as e:
    print(f"(docker ps failed: {e})")
missing = []
for name, block in svc.items():
    if not isinstance(block, dict) or not block.get("enabled"):
        continue
    container = "puente-" + name.replace("_", "-")
    if container not in running:
        missing.append((name, container))
if missing:
    print("ENABLED IN CONFIG BUT NOT RUNNING:")
    for name, container in sorted(missing):
        print(f"  {name:20} expected container {container}")
else:
    print("(every enabled service is running)")
PY
fi

section "systemd: puente units"
for u in puente-boot ollama-warm ollama-preload tutor-admin-runner \
         comfyui-idle-unload.timer swarmui-watchdog.timer \
         imagegen-weekly-restart.timer ollama; do
  enabled=$(systemctl is-enabled "$u" 2>&1 | head -1)
  active=$(systemctl is-active "$u" 2>&1 | head -1)
  printf '  %-30s enabled=%-12s active=%s\n' "$u" "$enabled" "$active"
done

section "systemd: failed units (whole host)"
# Catches a dependency failure that took something down with it — the usual
# signature of a boot ordering problem.
probe systemctl --failed --no-pager --no-legend

section "systemd: journal errors since boot"
# GPU/driver/cuda/docker complaints during startup, which is where a race shows.
probe journalctl -b -p err --no-pager -n 60

section "crontab (the lab windows live here — not in git)"
probe crontab -l

section "ollama"
printf 'systemd: %s\n' "$(systemctl is-active ollama 2>&1 | head -1)"
printf 'enabled: %s\n' "$(systemctl is-enabled ollama 2>&1 | head -1)"
probe systemctl cat ollama
# Loaded models: proves the keep-alive / preload tuning actually took effect,
# and shows which GPU a model landed on.
probe curl -s --max-time 5 http://127.0.0.1:11434/api/ps

section "listening ports (puente services)"
probe ss -tlnp

section "proxy routes reachable locally (bypasses DNS/TLS)"
# Each is the internal path Caddy fronts. If one of these 502s, the backend is
# down even though Caddy itself answers.
for hp in chat:3080 librechat:3080 speech:8000 image:8188 voice:17493 \
          status:3002; do
  host="${hp%%:*}"; port="${hp##*:}"
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 \
         "http://127.0.0.1:${port}/" 2>/dev/null)
  printf '  %-12s :%-6s -> %s\n' "$host" "$port" "${code:-timeout}"
done

section "persistent data present (not recreatable)"
for p in "$HOME/.puente/librechat" "$HOME/.puente/anythingllm" \
         "$HOME/.puente/comfyui-basedir" "$HOME/.puente/swarmui" \
         "$HOME/.puente/tutor-admin/audit.log"; do
  if [ -e "$p" ]; then printf '  present  %s\n' "$p"
  else printf '  MISSING  %s\n' "$p"; fi
done
probe docker volume ls --filter name=librechat-mongo

section "puente doctor"
if [ -x "${PUENTE_HOME}/.venv/bin/puente" ]; then
  probe "${PUENTE_HOME}/.venv/bin/puente" doctor
elif command -v puente >/dev/null 2>&1; then
  probe puente doctor
fi

printf '\nsnapshot complete: %s\n' "$OUT"