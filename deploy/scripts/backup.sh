#!/usr/bin/env bash
# Back up the database (and Caddy's certificates) with rotation.
# Schedule it daily, e.g. crontab:  0 2 * * * /opt/app/scripts/backup.sh
#
# Copy backups OFF this machine regularly (USB, NAS): a backup on the same
# disk doesn't survive a disk failure.
set -euo pipefail
cd "$(dirname "$0")/.."

KEEP_DAYS="${KEEP_DAYS:-14}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "==> Dumping database"
docker compose exec -T db pg_dump -U app -d app --format=custom > "$BACKUP_DIR/db-$STAMP.dump"

echo "==> Archiving certificates"
docker compose run --rm --no-deps -v "$(realpath "$BACKUP_DIR"):/backup" --entrypoint tar web \
  -czf "/backup/caddy-$STAMP.tar.gz" -C /data .

# A backup you haven't checked is a guess: make sure the dump is readable.
docker compose exec -T db pg_restore --list < "$BACKUP_DIR/db-$STAMP.dump" > /dev/null

find "$BACKUP_DIR" -name 'db-*.dump' -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR" -name 'caddy-*.tar.gz' -mtime +"$KEEP_DAYS" -delete
echo "==> Backup written: $BACKUP_DIR/db-$STAMP.dump"
