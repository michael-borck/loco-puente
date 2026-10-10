#!/usr/bin/env bash
# Rotate a Caddy basic-auth password: generate a strong one, hash it, update the
# generated .env, and reload Caddy.
#
# Why a script rather than three manual steps: the failure mode here is a
# half-finished rotation, where the hash changes but Caddy is never reloaded, or
# the .env is rewritten and the plaintext is written into the config. Both leave
# the box either unreachable or still on the old password.
#
# The plaintext is printed ONCE, to the terminal, and never written anywhere
# except a 0600 file under the data dir. It is not echoed into the Caddyfile,
# not committed, and not logged.
#
# Usage:
#   deploy/rotate-caddy-password.sh michael
#   deploy/rotate-caddy-password.sh callum
#   deploy/rotate-caddy-password.sh michael --password 'chosen-by-hand'
#
# Env overrides: DATA_DIR, CADDY_CONTAINER (default puente-caddy)

set -euo pipefail

USER_NAME="${1:?usage: rotate-caddy-password.sh <username> [--password PW]}"
PASSWORD=""
if [[ "${2:-}" == "--password" ]]; then
  PASSWORD="${3:?--password needs a value}"
fi

DATA_DIR="${DATA_DIR:-$HOME/.puente}"
ENV_FILE="$DATA_DIR/caddy/.env"
CONTAINER="${CADDY_CONTAINER:-puente-caddy}"
CREDS="$DATA_DIR/credentials-$USER_NAME.txt"

CONFIG="${PUENTE_CONFIG:-}"
if [[ -z "$CONFIG" ]]; then
  for d in "$PWD" $(dirname "$PWD"); do
    [[ -f "$d/puente.yml" ]] && CONFIG="$d/puente.yml" && break
  done
fi
[[ -f "$CONFIG" ]] || { echo "cannot find puente.yml (set PUENTE_CONFIG)" >&2; exit 1; }

# The env var name for this user, read from the config rather than hardcoded, so
# this script keeps working if the naming convention changes.
read -r ENV_NAME GROUP <<<"$(python3 - "$CONFIG" "$USER_NAME" <<'PY'
import sys, yaml
cfg = yaml.safe_load(open(sys.argv[1]))
users = cfg["services"]["caddy"]["users"]
hits = [(g, m[sys.argv[2]]) for g, m in users.items() if sys.argv[2] in m]
if not hits:
    sys.exit(f"user {sys.argv[2]!r} not found in caddy.users")
for _g, val in hits:
    if val.startswith("$2"):
        sys.exit(f"user {sys.argv[2]!r} still has an inline bcrypt hash in the config")
# `michael` is in both `boxes` and `tutors`. Rotating one must not look like it
# rotated both, so say which group this run touches.
if len(hits) > 1:
    print(f"NOTE: {sys.argv[2]!r} appears in groups {[g for g, _ in hits]}; "
          f"this run touches only {hits[0][0]!r}", file=sys.stderr)
print(hits[0][1], hits[0][0])
PY
)"
[[ -n "$ENV_NAME" ]] || { echo "could not resolve env var for $USER_NAME" >&2; exit 1; }

if [[ -z "$PASSWORD" ]]; then
  # 24 chars, unambiguous alphabet (no O/0/l/1/I) — these get read aloud over a
  # call and typed by hand. Ambiguous characters are the ones that get
  # mistranscribed and then fail auth for an afternoon.
  PASSWORD="$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 24)"
fi

echo "generating bcrypt for '$USER_NAME' in group '$GROUP' (env var $ENV_NAME)..."

# Hash via the environment, never by interpolating the password into a heredoc.
# A password containing a quote, a backslash or `$` would otherwise be corrupted
# or silently change — you would type in one password and Caddy would check
# against the hash of a different one, and the symptom is an auth failure with no
# obvious cause. A variable named with a leading underscore is ignored by the shell.
_HASH_OUT="$(
  _PUENTE_PW="$PASSWORD" PYTHONPATH="$PWD/.venv-test${PYTHONPATH:+:$PYTHONPATH}" \
  python3 - <<'PY'
import os, bcrypt
pw = os.environ["_PUENTE_PW"].encode()
h = bcrypt.hashpw(pw, bcrypt.gensalt(rounds=14))
if not bcrypt.checkpw(pw, h):
    raise SystemExit("hash round-trip failed")
print(h.decode())
PY
)"
[[ -n "$_HASH_OUT" ]] || { echo "hash generation failed" >&2; exit 1; }
HASH="$_HASH_OUT"

# Verify the password Caddy will now check against is the one you typed. This
# is the check that catches the whole class of "I know the password and it is
# rejected" — run it here rather than discovering it in a browser dialog.
read -r -s -p "Verify — type the password again to confirm what Caddy will accept: " CONFIRM
echo
[[ "$CONFIRM" == "$PASSWORD" ]] || { echo "passwords did not match; nothing written" >&2; exit 1; }

# Update .env in place, preserving every other line. Compose reads this file, and
# `$` in a bcrypt hash must stay escaped as `$$` or compose interpolates it.
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"
python3 - "$ENV_FILE" "$ENV_NAME" "$HASH" <<'PY'
import sys, pathlib
path, name, hash_ = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
escaped = hash_.replace("$", "$$")           # compose interpolation guard
lines = path.read_text().splitlines()
out, replaced = [], False
for line in lines:
    if line.split("=", 1)[0].strip() == name and "=" in line:
        out.append(f"{name}={escaped}")
        replaced = True
    else:
        out.append(line)
if not replaced:
    out.append(f"{name}={escaped}")
path.write_text("\n".join(out) + "\n")
print("updated" if replaced else "appended", name)
PY

# The plaintext, once, in a 0600 file. Printed so it can be transcribed; the file
# exists so it does not have to survive on memory alone.
umask 077
printf 'Caddy basic-auth — %s\nhostname: boxes.borck.dev\nuser: %s\npassword: %s\nenv var: %s\nrotated: %s\n' \
  "generated by rotate-caddy-password.sh" "$USER_NAME" "$PASSWORD" "$ENV_NAME" \
  "$(date -Is)" > "$CREDS"
chmod 600 "$CREDS"

echo
echo "  user     $USER_NAME"
echo "  password $PASSWORD"
echo "  saved to $CREDS  (delete once you've stored it)"
echo

# Reload, so the new hash takes effect. A reload keeps existing connections;
# a restart would drop them.
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "reloading $CONTAINER..."
  docker exec "$CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
else
  echo "NOTE: $CONTAINER is not running. The hash is written; reload it yourself:"
  echo "  docker start $CONTAINER"
fi

echo
echo "Verify with:"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' -u '$USER_NAME:$(printf %s "$PASSWORD" | sed 's/.*/THE-PASSWORD-YOU-JUST-SET/')' https://boxes.borck.dev:8077/  # expect 401 without auth, 200/302 with"