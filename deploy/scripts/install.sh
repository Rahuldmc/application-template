#!/usr/bin/env bash
# Install or upgrade from an offline bundle. Run inside the extracted bundle:
#
#   tar -xzf app-1.2.0.tar.gz && cd app-1.2.0 && ./scripts/install.sh
#
# First install: creates .env from .env.example and stops so you can fill it in.
# Upgrade: backs up the database, loads new images, migrates, restarts.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Verifying bundle integrity"
sha256sum --quiet -c SHA256SUMS

if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created .env. Fill in SITE_ADDRESS, POSTGRES_PASSWORD and JWT_SECRET_KEY, then re-run."
  exit 1
fi

VERSION="$(cat VERSION)"
sed -i "s/^APP_VERSION=.*/APP_VERSION=$VERSION/" .env

echo "==> Loading images"
for image in images/*.tar.gz; do
  gunzip -c "$image" | docker load
done

if docker compose ps --status running db 2>/dev/null | grep -q db; then
  echo "==> Existing install found: backing up before upgrade"
  ./scripts/backup.sh
fi

echo "==> Starting database"
docker compose up -d --no-build db
docker compose up -d --no-build --wait db

echo "==> Running migrations"
docker compose run --rm --no-deps backend alembic upgrade head

echo "==> Starting application"
docker compose up -d --no-build --wait

echo "==> Installed version $VERSION"
echo "    Create the first admin (first install only):"
echo "    docker compose run --rm backend python -m app.cli create-admin --email <email> --name <name>"
