---
name: offline-deployment
description: Package, install, upgrade, back up and operate the application on a client's local network with no internet access (air-gapped/LAN), using Docker bundles or a native install on Windows or Linux. Use for any LAN, on-premise, offline or air-gapped client deployment, or questions about TLS certificates, time sync, backups or updates on client servers.
---

# Offline / LAN deployment

Client servers may never see the internet. Everything the app needs must travel in the bundle, and the install must be repeatable by someone following a checklist.

## Pre-flight: gather from the client

| Item | Why |
|---|---|
| Server OS (Windows Server / Linux) and whether Docker is allowed | picks the install path below |
| LAN IP or internal hostname users will type | `SITE_ADDRESS`; the certificate is issued for it |
| Who manages client PCs (can we install a root certificate on them?) | HTTPS trust |
| Internal time source (domain controller / NTP server) | token expiry depends on correct clocks |
| Where backups can be copied (NAS, USB) | backups on the same disk aren't backups |
| Oldest app version currently installed there | migration path to test |

## Path A: Docker (recommended)

### Build the bundle (on a machine with internet)
```bash
deploy/scripts/build-bundle.sh 1.2.0      # → deploy/bundles/app-1.2.0.tar.gz
```
The bundle contains the app images, the Postgres image, compose file, Caddy configs, scripts, and SHA256 checksums.

### Install on the client server
```bash
tar -xzf app-1.2.0.tar.gz && cd app-1.2.0
./scripts/install.sh          # first run creates .env and stops
# edit .env: DEPLOY_MODE=lan, SITE_ADDRESS, POSTGRES_PASSWORD, JWT_SECRET_KEY (generate both randomly)
./scripts/install.sh          # verifies checksums, loads images, migrates, starts
docker compose run --rm backend python -m app.cli create-admin --email admin@client.local --name "Admin"
```

### Upgrade
Build a new bundle, copy it over, run `./scripts/install.sh` from the new folder with the **same `.env`** copied in. It backs up the database before migrating.

## Path B: Native install (no Docker)

Install offline from pre-downloaded installers: PostgreSQL, Python 3.12, uv, Caddy. Vendor Python dependencies on an internet machine:

```bash
cd backend
uv export --no-dev --format requirements-txt > requirements.txt
uv pip download -r requirements.txt -d wheels/  # or: pip download -r requirements.txt -d wheels/ --platform <target>
# on the server:
uv venv && uv pip install --no-index --find-links wheels/ -r requirements.txt
```
Build the frontend (`npm run build`) on the internet machine and copy `frontend/dist/`.

- **Linux**: run the backend with a systemd unit: `ExecStart=/opt/app/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers`, `User=app`, `EnvironmentFile=/opt/app/backend/.env`, `Restart=always`.
- **Windows**: run uvicorn as a service with NSSM (or WinSW), bound to `127.0.0.1:8000`. Run Caddy as a service the same way. Open only ports 80/443 in Windows Firewall.
- Use `deploy/caddy/Caddyfile.lan`, replacing `backend:8000` with `127.0.0.1:8000` and `/srv` with the path to `dist`.
- Run migrations with `uv run alembic upgrade head` (or `.venv` equivalent) before starting a new version.

## HTTPS on the LAN (required)

Session cookies are `Secure`: over plain `http://192.168.x.x` the browser drops them and login silently fails. `Caddyfile.lan` uses `tls internal`: Caddy runs its own certificate authority, fully offline.

**Trust the certificate** on each client PC once:
1. Export the root: `docker compose cp web:/data/caddy/pki/authorities/local/root.crt ./client-root-ca.crt`
2. Windows: double-click → Install Certificate → Local Machine → "Trusted Root Certification Authorities" (or push via Group Policy). macOS: Keychain → System → Always Trust. Linux: copy to `/usr/local/share/ca-certificates/` → `update-ca-certificates`. Firefox may need `security.enterprise_roots.enabled=true`.
3. Back up the `caddy_data` volume (`backup.sh` does). Losing it means re-trusting a new root on every PC.

If the client has its own internal CA, use their certificate instead: `tls /path/cert.pem /path/key.pem` in the Caddyfile.

## Time sync

JWTs expire by clock. A server clock that's minutes off logs users out or accepts stale tokens (30 s leeway is built in).
- Point the server at the client's internal time source (Windows: `w32tm /config /manualpeerlist:<dc> /syncfromflags:manual /update`; Linux: `chrony` with `server <internal-ntp> iburst`).
- Check it during every visit: `w32tm /query /status` or `chronyc tracking`.

## Backups

- Schedule `scripts/backup.sh` daily (cron / Windows Task Scheduler via WSL or Git Bash). It dumps Postgres, archives certificates, verifies the dump, and keeps 14 days.
- Copy `backups/` off the server (NAS/USB) on a schedule the client owns.
- **Test a restore** (`scripts/restore.sh`) on a spare machine at hand-over and after major upgrades. An untested backup is a guess.

## Nothing may call the internet

- No CDN fonts, scripts or analytics in the frontend (the CSP `default-src 'self'` enforces this; don't loosen it).
- No external identity providers, no update checks, no telemetry.
- API docs are disabled in production (`ENABLE_DOCS=false`). Swagger UI loads from a CDN, so it wouldn't work offline anyway.
- The backend and Postgres sit on an internal Docker network with no outbound access.

## Hand-over checklist

- [ ] HTTPS works from a client PC without warnings
- [ ] Admin created; default/demo accounts removed
- [ ] `.env` has unique random secrets, `chmod 600`, and a copy is stored securely by the client
- [ ] Server time synced to the internal source
- [ ] Backup scheduled, copied off-machine, **restore tested**
- [ ] Firewall: only 80/443 open
- [ ] Version, install date, `SITE_ADDRESS` and contacts recorded in the client's runbook
