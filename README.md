# application-template

A production-ready starting point for web applications: **FastAPI + PostgreSQL** backend, **React + TypeScript** frontend, secure cookie-based authentication, and **Claude Code skills** that guide building, testing, reviewing and deploying features the same way every time.

Use it for cloud deployments and for **offline / LAN installs** at client sites.

## What you get

- **Auth that's done right.** Short-lived JWT access tokens and rotating refresh tokens in httpOnly cookies, CSRF protection, refresh-token reuse detection, account lockout, and "log out everywhere" on password or role change.
- **Role-based authorization** with ownership checks in the service layer.
- **Clean backend layers**: routers → services → repositories, typed errors, and a generic repository with CRUD and pagination.
- **Alembic migrations**, tested up → down → up on every test run.
- **A typed frontend API client** generated from the backend's OpenAPI schema, with automatic token refresh.
- **Tests**: pytest against real PostgreSQL and Vitest + Testing Library + MSW, with a coverage gate of 80%.
- **CI**: lint, type checks, tests, migration drift check, dependency audits, secret scanning.
- **Deployment**: Docker + Caddy with automatic HTTPS (public or internal CA), offline install bundles, and backup/restore scripts.
- **Claude Code setup**: `CLAUDE.md`, 9 skills, and hooks for formatting and guardrails.

## Repository layout

```
backend/
  app/
    main.py            FastAPI app factory
    core/              config, security, cookies, auth dependencies, middleware, errors, logging
    database/          engine/session, Base + mixins, generic BaseRepository
    models/            SQLAlchemy models
    schemas/           Pydantic request/response models
    repositories/      queries per model
    services/          business logic + authorization (one file per feature)
    routers/           HTTP endpoints (one file per feature)
    utils/             small shared helpers
    cli.py             admin commands (create-admin)
  migrations/          Alembic
  tests/               unit/ and integration/
frontend/
  src/
    app/               router, providers
    api/               HTTP client, errors, generated types
    features/          one folder per feature (auth, users, ...)
    components/        shared UI and layout
    routes/            route guards, generic pages
    lib/, config/      helpers, env access
deploy/                Docker Compose, Caddy (cloud + lan), offline bundle/backup scripts
.claude/               skills, hooks, shared settings
```

## Getting started

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 24 LTS (see `.nvmrc`), and PostgreSQL 15+. Docker is optional.

### 1. Database

Pick one:
- **With Docker:** `docker compose up -d` creates `app` and `app_test` databases on localhost.
- **Native PostgreSQL:** create a user and two databases:
  ```sql
  CREATE USER app WITH PASSWORD 'app';
  CREATE DATABASE app OWNER app;
  CREATE DATABASE app_test OWNER app;
  ```

### 2. Backend

```bash
cd backend
cp .env.example .env           # set JWT_SECRET_KEY (instructions inside)
uv sync
uv run alembic upgrade head
uv run python -m app.cli create-admin --email you@example.com --name "Your Name"
uv run uvicorn app.main:app --reload     # http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

Vite proxies `/api` to the backend, so the browser sees a single origin. Cookies work with no CORS setup.

### 4. Tests

```bash
cd backend && uv run pytest --cov
cd frontend && npm test
```

## Everyday commands

| Task | Command |
|---|---|
| New migration | `cd backend && uv run alembic revision --autogenerate -m "add orders"` (then review it) |
| Apply migrations | `uv run alembic upgrade head` |
| Regenerate frontend API types | `cd frontend && npm run gen:api` |
| Lint + types (backend) | `uv run ruff check . && uv run mypy app tests` |
| Lint + types (frontend) | `npm run lint && npm run typecheck` |
| Pre-commit hooks (once per clone) | `uv tool install pre-commit && pre-commit install` |

## Working with Claude Code

Open the repo in Claude Code. `CLAUDE.md` loads automatically. Skills in `.claude/skills/`:

| Skill | Purpose |
|---|---|
| `engineering-standards` | Structure, conventions, definition of done |
| `write-tests` / `run-tests` | Test patterns (including the authorization matrix) and running/diagnosing suites |
| `db-migration` | Safe Alembic workflow and review checklist |
| `review-and-fix` | `/code-review` → triage → fix → verify → re-review |
| `security-audit` | `/security-review` + scanners + a full checklist |
| `ship-feature` | The whole pipeline for a new feature |
| `offline-deployment` | LAN/air-gapped packaging, HTTPS trust, time sync, backups |
| `client-setup` | Turn the template into a client project |

Example prompts:
- "Use ship-feature to add an orders module where users manage their own orders and admins see all."
- "Run review-and-fix on my changes."
- "Run a security-audit before the release."

## Deployment

See `deploy/`, the **[Linux deployment guide](deploy/linux/README.md)**, and the `offline-deployment` skill.

- **Cloud:** `DEPLOY_MODE=cloud`, `SITE_ADDRESS=app.example.com`. Caddy obtains a public certificate automatically.
- **LAN / offline:** `DEPLOY_MODE=lan`, `SITE_ADDRESS=<lan ip or hostname>`. Caddy issues certificates from its own internal CA. Install with Docker (`deploy/scripts/build-bundle.sh <version>`, then `scripts/install.sh` on the server) or natively with systemd. Both are covered step by step in `deploy/linux/README.md`.

## Security model (summary)

| Concern | Implementation |
|---|---|
| Passwords | argon2id; 12–128 chars; lockout after repeated failures |
| Access token | JWT, 15 min, httpOnly cookie; algorithm/issuer/audience pinned; checked against the user's `token_version` on every request |
| Refresh token | Random, stored as SHA-256, rotated on each use, reuse revokes the whole session family, path-scoped cookie |
| CSRF | Double-submit token on every state-changing API call |
| Authorization | Role dependencies + per-record checks in services; hidden records return 404 |
| Headers | Strict CSP, `nosniff`, `X-Frame-Options: DENY`, HSTS (cloud) |
| Secrets | Env only; production refuses weak keys; gitleaks in pre-commit and CI |

## License

[MIT](LICENSE)
