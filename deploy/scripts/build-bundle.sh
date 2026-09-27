#!/usr/bin/env bash
# Build an offline install bundle on a machine WITH internet access.
# Copy the resulting .tar.gz to the client's server (USB, internal share) and
# run install.sh there. The client server needs Docker, but no internet.
#
#   deploy/scripts/build-bundle.sh 1.2.0
set -euo pipefail

VERSION="${1:?usage: build-bundle.sh <version>}"
APP_NAME="${APP_NAME:-app}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/deploy/bundles/$APP_NAME-$VERSION"

echo "==> Building images for $APP_NAME $VERSION"
docker build -t "$APP_NAME-backend:$VERSION" "$ROOT/backend"
docker build -t "$APP_NAME-web:$VERSION" -f "$ROOT/deploy/web.Dockerfile" "$ROOT"
docker pull postgres:17

echo "==> Exporting images"
rm -rf "$OUT" && mkdir -p "$OUT/images"
docker save "$APP_NAME-backend:$VERSION" | gzip > "$OUT/images/backend.tar.gz"
docker save "$APP_NAME-web:$VERSION" | gzip > "$OUT/images/web.tar.gz"
docker save postgres:17 | gzip > "$OUT/images/postgres.tar.gz"

echo "==> Copying deployment files"
cp "$ROOT/deploy/docker-compose.yml" "$ROOT/deploy/.env.example" "$OUT/"
cp -r "$ROOT/deploy/caddy" "$ROOT/deploy/scripts" "$OUT/"
echo "$VERSION" > "$OUT/VERSION"

echo "==> Writing checksums"
(cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)

tar -C "$(dirname "$OUT")" -czf "$OUT.tar.gz" "$(basename "$OUT")"
rm -rf "$OUT"
echo "==> Bundle ready: $OUT.tar.gz"
