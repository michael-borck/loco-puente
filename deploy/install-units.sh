#!/usr/bin/env bash
# Render the puente systemd units for THIS host and install them.
#
# The units in deploy/ are templates with two placeholders that differ per host:
#
#   @PUENTE_HOME@  absolute path to the checkout (the dir holding puente.yml)
#   @PUENTE_USER@  the account that runs the units
#
# `%h` is deliberately NOT used for the home directory: the units must run the
# *checkout*, not $HOME, and the checkout is not always in $HOME.
#
# Every unit gets PUENTE_CONFIG set, so none of them depend on WorkingDirectory
# to find puente.yml. That removes the reason this box carried a `cd` in every
# unit and in chat-window.sh.

set -euo pipefail

# -- resolve the stack ---------------------------------------------------------

PUENTE_HOME="${PUENTE_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PUENTE_USER="${PUENTE_USER:-${SUDO_USER:-${USER:-$(id -un)}}}"
PUENTE_CONFIG="${PUENTE_CONFIG:-${PUENTE_HOME}/puente.yml}"
RENDER_DIR="${RENDER_DIR:-$(mktemp -d)}"

if [[ ! -f "${PUENTE_CONFIG}" ]]; then
  echo "error: no puente.yml at ${PUENTE_CONFIG}" >&2
  echo "       set PUENTE_CONFIG=/path/to/puente.yml, or PUENTE_HOME=/path/to/checkout" >&2
  exit 1
fi

# Prefer the checkout's venv so the units run the same puente the operator tests.
PUENTE_BIN="${PUENTE_BIN:-}"
if [[ -z "${PUENTE_BIN}" ]]; then
  if [[ -x "${PUENTE_HOME}/.venv/bin/puente" ]]; then
    PUENTE_BIN="${PUENTE_HOME}/.venv/bin/puente"
  elif command -v puente >/dev/null 2>&1; then
    PUENTE_BIN="$(command -v puente)"
  else
    echo "error: no puente executable found (looked in ${PUENTE_HOME}/.venv/bin and PATH)" >&2
    exit 1
  fi
fi

UNIT_DIR="${UNIT_DIR:-/etc/systemd/system}"

# -- render --------------------------------------------------------------------

# Units whose only job is a timer-driven maintenance task. Not all are wanted on
# every deployment: a single-GPU box has no swarmui, so its watchdog is dead
# weight that logs a confusing failure every ten minutes.
ALL_UNITS=(
  puente-boot.service
  ollama-warm.service
  comfyui-idle-unload.service
  comfyui-idle-unload.timer
  swarmui-watchdog.service
  swarmui-watchdog.timer
  imagegen-weekly-restart.service
  imagegen-weekly-restart.timer
  tutor-admin-runner.service
)

# Enable by default. Pass a service name to install only that one; pass --list to
# see the mapping.
declare -A WANTED_BY_SERVICE=(
  [puente-boot.service]="swarmui"
  [ollama-warm.service]="ollama"
  [comfyui-idle-unload.service]="comfyui"
  [comfyui-idle-unload.timer]="comfyui"
  [swarmui-watchdog.service]="swarmui"
  [swarmui-watchdog.timer]="swarmui"
  [imagegen-weekly-restart.service]="comfyui"
  [imagegen-weekly-restart.timer]="comfyui"
  [tutor-admin-runner.service]="tutor_admin"
)

list_units() {
  echo "units, and the service each depends on:"
  for u in "${ALL_UNITS[@]}"; do
    printf '  %-34s needs: %s\n' "${u}" "${WANTED_BY_SERVICE[${u}]:-—}"
  done
}

enable_units=("${ALL_UNITS[@]}")
if [[ $# -gt 0 && "${1}" != "--list" ]]; then
  enable_units=("$@")
fi

if [[ "${1:-}" == "--list" ]]; then
  list_units
  exit 0
fi

# Only create the render dir when it isn't a caller-supplied path that should
# already exist; mkdir -p is harmless either way but hides a typo'd RENDER_DIR.
mkdir -p "${RENDER_DIR}" "${UNIT_DIR}"

echo "PUENTE_HOME=${PUENTE_HOME}"
echo "PUENTE_CONFIG=${PUENTE_CONFIG}"
echo "PUENTE_USER=${PUENTE_USER}"
echo "PUENTE_BIN=${PUENTE_BIN}"
echo "installing to ${UNIT_DIR}"
echo

for unit in "${enable_units[@]}"; do
  src="${PUENTE_HOME}/deploy/${unit}"
  if [[ ! -f "${src}" ]]; then
    echo "  skip ${unit} (not found in deploy/)"
    continue
  fi

  # Warn rather than silently install a unit for a service this stack doesn't
  # have — a watchdog for a container that never starts is a recurring red mark
  # in the journal that hides real failures.
  needed="${WANTED_BY_SERVICE[${unit}]:-}"
  if [[ -n "${needed}" ]] && ! grep -qE "^  ${needed}:" "${PUENTE_CONFIG}" 2>/dev/null; then
    if grep -A2 "^  ${needed}:" "${PUENTE_CONFIG}" 2>/dev/null | grep -q "enabled: true"; then
      :
    else
      echo "  skip ${unit} (needs '${needed}', which is not enabled in puente.yml)"
      continue
    fi
  fi

  sed -e "s|@PUENTE_HOME@|${PUENTE_HOME}|g" \
      -e "s|@PUENTE_USER@|${PUENTE_USER}|g" \
      -e "s|@PUENTE_CONFIG@|${PUENTE_CONFIG}|g" \
      -e "s|@PUENTE_BIN@|${PUENTE_BIN}|g" \
      "${src}" > "${RENDER_DIR}/${unit}"

  # Inject PUENTE_CONFIG right after [Service] so no unit depends on cwd to find
  # puente.yml. A separate sed pass because the replacement contains slashes,
  # which need a different delimiter than the placeholder substitutions use.
  if ! grep -q "^Environment=PUENTE_CONFIG=" "${RENDER_DIR}/${unit}"; then
    sed -i -e "0,/^\[Service\]/s##[Service]\nEnvironment=PUENTE_CONFIG=${PUENTE_CONFIG}#" \
      "${RENDER_DIR}/${unit}"
  fi

  echo "  ${unit}"
done

echo
if [[ "${DRY_RUN:-1}" == "1" ]]; then
  echo "DRY RUN — rendered units are in ${RENDER_DIR}, nothing installed."
  echo "Inspect them, then re-run with DRY_RUN=0 to install."
  echo
  for f in "${RENDER_DIR}"/*; do
    echo "--- ${f##*/} ---"
    grep -E "User=|Environment=PUENTE_CONFIG|WorkingDirectory|ExecStart" "${f}" || true
    echo
  done
  exit 0
fi

echo "installing..."
install -m 644 -o root -g root "${RENDER_DIR}"/* "${UNIT_DIR}/"
systemctl daemon-reload
echo "done. enable with: systemctl enable --now <unit>"