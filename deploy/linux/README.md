# Deploying on a Linux server (LAN / offline)

Step-by-step install for a client's Linux server with **no internet access**. Commands assume Ubuntu 24.04 LTS or Debian 12/13 on x86_64; notes cover RHEL-family differences.

You prepare everything on a **build machine** with internet access, carry it over (USB drive or internal file share), and install on the **server**.

Choose one option:

- **Option A: Docker (recommended).** Everything ships as images. Upgrades are "load new images, restart", and every client runs an identical stack.
- **Option B: Native.** No Docker: PostgreSQL, Python and Caddy installed directly, with the backend run by systemd. Use this when the client doesn't allow Docker.

Both options end with the same steps: trust the certificate, time sync, backups, hand-over.

---

## Before you go: collect from the client

| Item | Example | Used for |
|---|---|---|
| Server distro and version, CPU arch | Ubuntu 24.04, x86_64 | picking the right packages |
| LAN IP or hostname users will type | `192.168.1.50` / `app.client.local` | `SITE_ADDRESS`; the certificate is issued for it |
| Internal time server | domain controller / `ntp.client.local` | token expiry needs correct clocks |
| Backup destination off the server | NAS share, USB drive | real backups |
| Who can install a root certificate on client PCs | IT admin / Group Policy | HTTPS trust |
| Sudo access on the server | | install |

---

## Option A: Docker

### On the build machine

```bash
deploy/scripts/build-bundle.sh 1.0.0        # → deploy/bundles/app-1.0.0.tar.gz
```

If Docker isn't installed on the server yet, also download the Docker Engine packages for the server's exact distro version from `https://download.docker.com/linux/<ubuntu|debian>/dists/<codename>/pool/stable/amd64/`:
`containerd.io`, `docker-ce`, `docker-ce-cli`, `docker-buildx-plugin`, `docker-compose-plugin` (`.deb` files).

### On the server

```bash
# 1. Docker (skip if already installed)
sudo dpkg -i ./containerd.io_*.deb ./docker-ce-cli_*.deb ./docker-ce_*.deb \
             ./docker-buildx-plugin_*.deb ./docker-compose-plugin_*.deb
sudo systemctl enable --now docker

# 2. Unpack the bundle
sudo mkdir -p /opt/app && sudo tar -xzf app-1.0.0.tar.gz -C /opt/app
cd /opt/app/app-1.0.0

# 3. First run creates .env and stops
sudo ./scripts/install.sh
sudo nano .env        # DEPLOY_MODE=lan, SITE_ADDRESS, POSTGRES_PASSWORD, JWT_SECRET_KEY
#   generate secrets:  python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 4. Install: checksums, load images, migrate, start
sudo ./scripts/install.sh

# 5. First admin
sudo docker compose run --rm backend python -m app.cli create-admin --email admin@client.local --name "Admin"
```

Containers restart automatically on reboot (`restart: unless-stopped` + the Docker service).

### Upgrade (Docker)

```bash
sudo tar -xzf app-1.1.0.tar.gz -C /opt/app
sudo cp /opt/app/app-1.0.0/.env /opt/app/app-1.1.0/.env
cd /opt/app/app-1.1.0 && sudo ./scripts/install.sh     # backs up, then migrates and restarts
```

Keep the previous folder until the new version is verified: rolling back means running its `install.sh` and restoring the pre-upgrade backup if the schema changed.

---

## Option B: Native (systemd)

Layout on the server:

```
/opt/app/backend/     application code (app/, migrations/, alembic.ini)
/opt/app/venv/        Python virtualenv
/opt/app/web/         built frontend (index.html, assets/)
/etc/app/app.env      secrets and settings (mode 600)
/etc/caddy/Caddyfile  from deploy/linux/Caddyfile.native
/var/backups/app/     database dumps
```

### On the build machine

```bash
VERSION=1.0.0
mkdir -p dist/app-$VERSION

# Backend code
cp -r backend/app backend/migrations backend/alembic.ini dist/app-$VERSION/

# Python wheels for the SERVER's platform (works from Windows/macOS too).
# Match --python-version to the server's python3 (Ubuntu 24.04 = 3.12).
cd backend
uv export --no-dev --no-hashes --format requirements-txt > ../dist/app-$VERSION/requirements.txt
cd ..
pip download -r dist/app-$VERSION/requirements.txt -d dist/app-$VERSION/wheels \
  --only-binary=:all: --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 \
  --python-version 3.12 --implementation cp

# Frontend
(cd frontend && npm ci && npm run build) && cp -r frontend/dist dist/app-$VERSION/web

# Deployment files
cp deploy/linux/app-backend.service deploy/linux/Caddyfile.native dist/app-$VERSION/

tar -czf app-$VERSION-native.tar.gz -C dist app-$VERSION
```

Also bring, for the server's exact distro version:
- **PostgreSQL** packages (`.deb`/`.rpm`), from the client's internal mirror, or downloaded on a machine with the same distro via `apt-get download postgresql postgresql-16 postgresql-client-16 postgresql-common postgresql-client-common libpq5 ssl-cert` (the list can vary; check with `apt-get install --print-uris`).
- **Caddy**: the static binary from `https://github.com/caddyserver/caddy/releases` (`caddy_<ver>_linux_amd64.tar.gz`).
- **python3.12-venv** if missing (Ubuntu doesn't install it by default).

### On the server

**1. System user and folders**

```bash
sudo useradd --system --home /opt/app --shell /usr/sbin/nologin app
sudo mkdir -p /opt/app /etc/app /var/backups/app
sudo tar -xzf app-1.0.0-native.tar.gz -C /tmp
```

**2. PostgreSQL**

```bash
sudo dpkg -i /path/to/postgres-debs/*.deb
sudo systemctl enable --now postgresql
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
sudo -u postgres psql -c "CREATE ROLE app LOGIN PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE app OWNER app;"
echo "$DB_PASSWORD"   # needed for app.env below
```

PostgreSQL listens on localhost only by default (`listen_addresses = 'localhost'`). Keep it that way.

**3. Configuration**

```bash
sudo tee /etc/app/app.env > /dev/null <<EOF
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://app:<DB_PASSWORD>@127.0.0.1:5432/app
JWT_SECRET_KEY=<python3 -c "import secrets; print(secrets.token_urlsafe(64))">
COOKIE_SECURE=true
ENABLE_DOCS=false
LOG_LEVEL=INFO
EOF
sudo chown root:app /etc/app/app.env && sudo chmod 640 /etc/app/app.env
```

Replace the `<...>` placeholders with real values. The app refuses to start in production with a weak `JWT_SECRET_KEY`.

**4. Backend**

```bash
sudo mkdir -p /opt/app/backend
sudo cp -r /tmp/app-1.0.0/{app,migrations,alembic.ini} /opt/app/backend/
sudo python3 -m venv /opt/app/venv
sudo /opt/app/venv/bin/pip install --no-index --find-links /tmp/app-1.0.0/wheels \
  -r /tmp/app-1.0.0/requirements.txt
sudo chown -R root:app /opt/app && sudo chmod -R o-rwx /opt/app

# Migrate and create the first admin
cd /opt/app/backend
sudo -u app bash -c 'set -a; . /etc/app/app.env; /opt/app/venv/bin/alembic upgrade head'
sudo -u app bash -c 'set -a; . /etc/app/app.env; /opt/app/venv/bin/python -m app.cli create-admin --email admin@client.local --name "Admin"'
```

**5. Backend service**

```bash
sudo cp /tmp/app-1.0.0/app-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now app-backend
curl -s http://127.0.0.1:8000/api/v1/health/ready      # {"status":"ok"}
```

**6. Frontend + Caddy (HTTPS)**

```bash
sudo mkdir -p /opt/app/web && sudo cp -r /tmp/app-1.0.0/web/. /opt/app/web/
sudo tar -xzf caddy_*_linux_amd64.tar.gz -C /usr/local/bin caddy
sudo useradd --system --home /var/lib/caddy --create-home --shell /usr/sbin/nologin caddy
sudo mkdir -p /etc/caddy && sudo cp /tmp/app-1.0.0/Caddyfile.native /etc/caddy/Caddyfile
sudo sed -i 's/{$SITE_ADDRESS}/192.168.1.50/g' /etc/caddy/Caddyfile       # your address
```

Install Caddy's standard systemd unit (`/etc/systemd/system/caddy.service`):

```ini
[Unit]
Description=Caddy
After=network-online.target
Wants=network-online.target

[Service]
User=caddy
Group=caddy
ExecStart=/usr/local/bin/caddy run --environ --config /etc/caddy/Caddyfile
ExecReload=/usr/local/bin/caddy reload --config /etc/caddy/Caddyfile --force
AmbientCapabilities=CAP_NET_BIND_SERVICE
Restart=on-failure
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now caddy
```

**7. Firewall**: only HTTPS/HTTP from the LAN.

```bash
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw enable
# RHEL family: firewall-cmd --permanent --add-service={http,https} && firewall-cmd --reload
```

### Upgrade (native)

```bash
sudo /usr/local/sbin/app-backup                 # see Backups below
sudo systemctl stop app-backend
sudo rm -rf /opt/app/backend/app /opt/app/backend/migrations
sudo cp -r /tmp/app-1.1.0/{app,migrations,alembic.ini} /opt/app/backend/
sudo /opt/app/venv/bin/pip install --no-index --find-links /tmp/app-1.1.0/wheels -r /tmp/app-1.1.0/requirements.txt
cd /opt/app/backend && sudo -u app bash -c 'set -a; . /etc/app/app.env; /opt/app/venv/bin/alembic upgrade head'
sudo rm -rf /opt/app/web && sudo cp -r /tmp/app-1.1.0/web /opt/app/web
sudo chown -R root:app /opt/app
sudo systemctl start app-backend && sudo systemctl reload caddy
```

---

## Trust the HTTPS certificate on client PCs

The app requires HTTPS: session cookies are `Secure`, so login fails over plain HTTP. Caddy issues certificates from its own offline CA. Each client PC must trust that CA's root once.

Get the root certificate:
- Docker: `sudo docker compose cp web:/data/caddy/pki/authorities/local/root.crt ./client-root-ca.crt`
- Native: `sudo cp /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt ./client-root-ca.crt`

Install it:
- **Windows PCs:** double-click → Install Certificate → Local Machine → Trusted Root Certification Authorities. For many PCs, the client's IT can push it via Group Policy.
- **Linux PCs:** `sudo cp client-root-ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates`
- **macOS:** Keychain Access → System → import → set "Always Trust".
- **Firefox** uses its own store: set `security.enterprise_roots.enabled = true` in `about:config`, or import the certificate in its settings.

**Back up the CA** (the Docker `backup.sh` does this; for native, back up `/var/lib/caddy/.local/share/caddy`). If it's lost, every PC must trust a new root.

If the client has its own internal CA, use their certificate instead: replace `tls internal` with `tls /etc/caddy/cert.pem /etc/caddy/key.pem`.

---

## Time sync

Login sessions depend on the server clock (30 seconds of drift is tolerated).

```bash
sudo apt install chrony        # from local packages if offline
echo "server ntp.client.local iburst" | sudo tee /etc/chrony/conf.d/client.conf
sudo systemctl restart chrony && chronyc tracking      # "System time" should be near 0
```

---

## Backups

**Docker:** `deploy/scripts/backup.sh` (database + certificates, verified, 14-day rotation):

```bash
sudo crontab -e
0 2 * * * cd /opt/app/app-1.0.0 && ./scripts/backup.sh >> /var/log/app-backup.log 2>&1
```

**Native:** create `/usr/local/sbin/app-backup`:

```bash
#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date +%Y%m%d-%H%M%S); DIR=/var/backups/app
sudo -u postgres pg_dump -d app --format=custom > "$DIR/db-$STAMP.dump"
pg_restore --list "$DIR/db-$STAMP.dump" > /dev/null                  # verify it's readable
tar -czf "$DIR/caddy-$STAMP.tar.gz" -C /var/lib/caddy/.local/share caddy
find "$DIR" -name 'db-*.dump' -mtime +14 -delete
find "$DIR" -name 'caddy-*.tar.gz' -mtime +14 -delete
```

```bash
sudo chmod 700 /usr/local/sbin/app-backup
echo "0 2 * * * root /usr/local/sbin/app-backup >> /var/log/app-backup.log 2>&1" | sudo tee /etc/cron.d/app-backup
```

Restore (native), which **replaces all data**:

```bash
sudo systemctl stop app-backend
sudo -u postgres pg_restore -d app --clean --if-exists --no-owner --role=app /var/backups/app/db-<stamp>.dump
cd /opt/app/backend && sudo -u app bash -c 'set -a; . /etc/app/app.env; /opt/app/venv/bin/alembic upgrade head'
sudo systemctl start app-backend
```

**Copy backups off the server** on a schedule (NAS mount + `rsync`, or USB rotation), and **test a restore** on a spare machine at hand-over.

---

## Operating

| Task | Docker | Native |
|---|---|---|
| Status | `docker compose ps` | `systemctl status app-backend caddy postgresql` |
| Logs | `docker compose logs -f backend` | `journalctl -u app-backend -f` |
| Restart | `docker compose restart backend` | `sudo systemctl restart app-backend` |
| Health | `curl -k https://<SITE_ADDRESS>/api/v1/health/ready` | same |
| DB shell | `docker compose exec db psql -U app` | `sudo -u postgres psql app` |

---

## Hand-over checklist

- [ ] `https://<SITE_ADDRESS>` opens from a client PC with **no certificate warning**
- [ ] Admin account created; no test/demo accounts left
- [ ] Secrets are random and unique to this client; env file is `600`/`640`; a copy is stored securely with the client
- [ ] Only ports 22/80/443 open; PostgreSQL not reachable from the LAN
- [ ] Server clock synced to the internal time source
- [ ] Nightly backup runs, is copied off the server, and **a restore was tested**
- [ ] Reboot test: the app comes back on its own
- [ ] Runbook written for the client: version, `SITE_ADDRESS`, install path, backup location, contacts
