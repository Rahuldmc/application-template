---
name: client-setup
description: Turn a fresh copy of this template into a specific client project - interview for client details, rename the app, choose cloud or LAN deployment, generate local config, and verify everything runs. Use at the very start of a new client project or when someone says they've just created a repo from this template.
---

# New client project setup

Run this once, right after creating a repo from the template.

## 1. Interview (ask, don't assume)

Ask the user for:

1. **Client / project name** and a short machine name (lowercase, hyphens), e.g. `acme-inventory`
2. **Deployment mode**: `cloud` (public domain, Let's Encrypt) or `lan` (offline, internal CA). If LAN: the Linux distro, version and CPU architecture, and whether Docker is allowed.
3. **Address users will type**: domain (cloud) or LAN IP / internal hostname (lan)
4. **Roles needed** beyond `admin` / `user`
5. **Does the frontend live on the same origin as the API?** (default yes; if not, the allowed origins)
6. Anything regulatory: data retention, audit logging, data residency

## 2. Apply

| What | Where |
|---|---|
| App name | `backend/app/core/config.py` (`app_name` default), `backend/pyproject.toml` (`description`), `frontend/index.html` `<title>`, `README.md` title and intro |
| JWT issuer/audience | `JWT_ISSUER` / `JWT_AUDIENCE` in `backend/.env.example` → the short machine name |
| Deploy defaults | `deploy/.env.example`: `APP_NAME`, `DEPLOY_MODE`, example `SITE_ADDRESS` |
| Extra roles | `Role` enum in `backend/app/models/user.py` (strings, so no migration needed for new values), `Role` type regenerates via `npm run gen:api` |
| Cross-origin frontend | `CORS_ORIGINS` in `backend/.env.example`; set `COOKIE_SAMESITE` appropriately |
| LICENSE | Confirm with the user: client work is often proprietary, so the MIT license from the template may need replacing |

## 3. Local environment

```bash
cp backend/.env.example backend/.env
python -c "import secrets; print(secrets.token_urlsafe(64))"   # paste into JWT_SECRET_KEY in backend/.env
cp frontend/.env.example frontend/.env.local
```
The `.env` files are blocked for Claude edits by a hook. Tell the user which values to set, and let them edit the files.

Database: `docker compose up -d` (Docker) or create `app` and `app_test` databases in a native PostgreSQL.

## 4. Verify

```bash
cd backend && uv sync && uv run alembic upgrade head && uv run pytest
uv run python -m app.cli create-admin --email <email> --name "<name>"
cd ../frontend && npm install && npm test && npm run build
```
Then start both dev servers and log in at http://localhost:5173.

## 5. Record

Add a "Client" section to `README.md`: deployment mode, address, server OS, contacts, and where the runbook lives. For LAN clients, walk through the pre-flight table in the `offline-deployment` skill now. It's much easier before the install visit.
