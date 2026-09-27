---
name: offline-deployment
description: Package, install, upgrade, back up and operate the application on a client's Linux server on a local network with no internet access (air-gapped/LAN), via Docker bundles or a native systemd install. Use for any LAN, on-premise, offline or air-gapped client deployment, or questions about HTTPS certificates, time sync, backups or updates on client servers.
---

# Offline / LAN deployment (Linux servers)

Client servers are Linux and may never see the internet. Everything the app needs must travel with you, and the install must be repeatable by someone following a checklist.

**The step-by-step guide is `deploy/linux/README.md`.** Follow it. Don't improvise a different procedure. When helping with a deployment, work through its sections in order and adapt only the values (addresses, versions, paths).

## Pick the install option

| Option | When | Files |
|---|---|---|
| **A: Docker** (default) | Client allows Docker | `deploy/docker-compose.yml`, `deploy/caddy/Caddyfile.lan`, `deploy/scripts/*.sh` |
| **B: Native systemd** | Docker not allowed | `deploy/linux/app-backend.service`, `deploy/linux/Caddyfile.native` |

## Rules that apply to every client install

1. **HTTPS is mandatory**, even on the LAN. Session cookies are `Secure`; over plain `http://<ip>` login silently fails. Caddy's `tls internal` provides certificates offline; client PCs must trust its root CA once (README → "Trust the HTTPS certificate").
2. **Nothing calls the internet.** No CDN assets, external auth, telemetry or update checks. The SPA's CSP (`default-src 'self'`) enforces this for the frontend. Never loosen it for convenience. API docs are off in production.
3. **Unique random secrets per client** (`JWT_SECRET_KEY`, DB password), stored in a `600`/`640` env file, never committed, and a copy handed to the client securely.
4. **Clock sync** to the client's internal time source (chrony). JWT expiry depends on it.
5. **Backups**: nightly, verified, rotated, copied **off the server**, and a restore **tested** at hand-over. Include Caddy's CA data, or every PC must re-trust a new certificate.
6. **Upgrades back up first**, then migrate (`alembic upgrade head`), then restart. Keep the previous version's files until the new one is verified.
7. **Only 22/80/443 open.** PostgreSQL and the backend listen on localhost / internal Docker network only.

## Preparing a release for an offline client

- Test the database upgrade from the **oldest version any client runs**, not just the previous release (see the `db-migration` skill → expand/contract).
- Docker: `deploy/scripts/build-bundle.sh <version>` produces a checksummed bundle with all images.
- Native: follow README → "Option B → On the build machine". Wheels must be downloaded for the **server's** Python version and platform (`manylinux`, `x86_64` or `aarch64`), not the build machine's.
- Write release notes that say whether the migration changes data and whether rollback needs a restore.

## When something goes wrong on site

| Symptom | Likely cause | Check |
|---|---|---|
| Login "works" but you're immediately logged out | Not HTTPS, or wrong address in `SITE_ADDRESS` | URL starts with `https://`; certificate issued for the typed address |
| Browser certificate warning | Root CA not trusted on that PC | Install `root.crt` (README) |
| Random logouts / "session expired" | Server clock drift | `chronyc tracking` |
| 502 from Caddy | Backend down | `journalctl -u app-backend` / `docker compose logs backend` |
| Backend won't start in production | Weak `JWT_SECRET_KEY` or `COOKIE_SECURE=false` | The startup error names the setting |
| Readiness check 503 | Database unreachable | `systemctl status postgresql` / `docker compose ps db` |

## Hand-over

Complete the hand-over checklist at the end of `deploy/linux/README.md`, and record version, address, install option, backup location and contacts in the client's runbook.
