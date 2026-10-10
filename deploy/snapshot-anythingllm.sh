#!/usr/bin/env bash
# Snapshot AnythingLLM: workspaces, documents, embeddings, vector store.
#
# Why this is not just `tar -czf`: the SQLite database is LIVE while the service
# runs. A plain tar of a database being written produces an archive that restores
# fine and is subtly corrupt — the failure surfaces weeks later as a workspace
# that exists but has no threads in it. `sqlite3 .backup` takes a consistent
# online snapshot without stopping the service or writing to it.
#
# Usage:
#   deploy/snapshot-anythingllm.sh                 # to the default destination
#   DEST=/mnt/data/backups deploy/snapshot-anythingllm.sh
#   KEEP=10 deploy/snapshot-anythingllm.sh         # prune older snapshots
#
# Restore (anythingllm must be stopped first):
#   sudo docker stop puente-anythingllm
#   sudo rm -rf ~/.puente/anythingllm
#   sudo tar -xzf <snapshot>.tar.gz -C ~/.puente
#   sudo chown -R $(id -u):$(id -g) ~/.puente/anythingllm
#   sudo docker start puente-anythingllm
#   # then set jwt_secret back in puente.yml, or sessions stop working

set -euo pipefail

SRC="${SRC:-$HOME/.puente/anythingllm}"
DEST="${DEST:-/mnt/data/backups}"
KEEP="${KEEP:-10}"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [[ ! -d "$SRC" ]]; then
  echo "nothing to snapshot: $SRC does not exist" >&2
  exit 1
fi

mkdir -p "$DEST"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "snapshotting $SRC -> $DEST"

# 1. Consistent copy of the live database. -cmd ".backup" is the online backup
#    API: it takes a read lock per page and copies into a fresh file, so the
#    result is valid even though the service is writing throughout.
DB="$SRC/anythingllm.db"
if [[ -f "$DB" ]]; then
  echo "  database: online sqlite backup"
  sqlite3 "$DB" ".backup '$WORK/anythingllm.db'"
  # Verify it, because an unverified backup is a hope, not a backup.
  if sqlite3 "$WORK/anythingllm.db" "pragma integrity_check;" | grep -q '^ok$'; then
    echo "  database: integrity check ok"
  else
    echo "  database: INTEGRITY CHECK FAILED — do not trust this archive" >&2
    exit 1
  fi
else
  echo "  database: absent, snapshotting the rest only"
fi

# 2. Everything else. --exclude so the throwaway copies we just made do not end
#    up inside the archive alongside the originals.
echo "  files:"
tar -czf "$WORK/anythingllm-files.tar.gz" \
  -C "$SRC" \
  --exclude=./anythingllm.db \
  --exclude=./tmp \
  . 2>/dev/null || true

# 3. One archive. The database is added first so a restore extracts it before
#    anything that might reference it.
ARCHIVE="$DEST/anythingllm-$STAMP.tar.gz"
tar -czf "$ARCHIVE" -C "$WORK" anythingllm.db anythingllm-files.tar.gz

SIZE="$(du -h "$ARCHIVE" | cut -f1)"
echo "wrote $ARCHIVE ($SIZE)"

# 4. Prune. Only after the new archive exists, so a failed snapshot never
#    deletes the previous good one.
if (( KEEP > 0 )); then
  mapfile -t OLD < <(ls -1t "$DEST"/anythingllm-*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)))
  for f in "${OLD[@]:-}"; do
    [[ -n "$f" ]] || continue
    echo "  pruning $(basename "$f")"
    rm -f "$f"
  done
fi

echo "done."