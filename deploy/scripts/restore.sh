#!/usr/bin/env bash
# Restore the database from a backup made by backup.sh. DESTROYS current data.
#
#   ./scripts/restore.sh backups/db-20260927-020000.dump
set -euo pipefail
cd "$(dirname "$0")/.."

DUMP="${1:?usage: restore.sh <path-to-db-*.dump>}"
[[ -f "$DUMP" ]] || { echo "No such file: $DUMP"; exit 1; }

read -r -p "This replaces ALL current data with $DUMP. Type 'restore' to continue: " answer
[[ "$answer" == "restore" ]] || { echo "Aborted."; exit 1; }

echo "==> Stopping the application"
docker compose stop backend web

echo "==> Restoring"
docker compose exec -T db pg_restore -U app -d app --clean --if-exists --no-owner < "$DUMP"

echo "==> Applying any newer migrations"
docker compose run --rm --no-deps backend alembic upgrade head

docker compose up -d --no-build --wait
echo "==> Restore complete"
