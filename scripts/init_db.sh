#!/usr/bin/env bash
# ==============================================================================
# Automatic PostgreSQL Entrypoint Seed Script
# ==============================================================================
# Executed automatically by official Postgres image on first-time volume creation.
# Reassembles and restores 272 episodes and 7,588 vector chunks.
# ==============================================================================

set -e

echo "[init_db.sh] Checking for pre-computed seed dump in /data/db_dump..."

if [ -f /data/db_dump/lenny_seed.dump.part_aa ]; then
  echo "[init_db.sh] Reassembling seed dump and restoring into ${POSTGRES_DB}..."
  cat /data/db_dump/lenny_seed.dump.part_* | pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" || true
  echo "[init_db.sh] Automatic seed restore completed successfully!"
else
  echo "[init_db.sh] No seed dump found at /data/db_dump. Skipping auto-restore."
fi
