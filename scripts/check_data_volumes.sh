#!/usr/bin/env bash
set -euo pipefail

if [ "${YUXI_ALLOW_EMPTY_DATA_INIT:-}" = "true" ]; then
  exit 0
fi

restore_dir="recovery-backups/20260529-restore-old-data"

if [ ! -d "$restore_dir" ]; then
  exit 0
fi

missing=0

check_path() {
  local label="$1"
  local path="$2"

  if [ ! -e "$path" ]; then
    printf 'Error: %s data path is missing: %s\n' "$label" "$path" >&2
    missing=1
  fi
}

check_path "Postgres" "docker/volumes/postgresql/PG_VERSION"
check_path "Neo4j" "docker/volumes/neo4j/data/databases"
check_path "Milvus" "docker/volumes/milvus/milvus"

if [ "$missing" -ne 0 ]; then
  cat >&2 <<'EOF'

Refusing to start with missing database volume data while an old-data recovery
backup exists at recovery-backups/20260529-restore-old-data.

This prevents Docker images from silently initializing empty databases over the
expected bind-mount locations. Restore the volume backup first, or set
YUXI_ALLOW_EMPTY_DATA_INIT=true only when you intentionally want a fresh local
database.
EOF
  exit 1
fi
