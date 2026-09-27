# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## Stack

- **Backend**: FastAPI · SQLAlchemy 2.1 (sync) · psycopg 3 · Alembic · PostgreSQL · uv
- **Frontend**: React 19 · TypeScript (strict) · Vite · React Router · TanStack Query · zod
- **Auth**: JWT access token (15 min) + rotating refresh token, both in httpOnly cookies, CSRF double-submit

## Reference module: copy it, don't invent new patterns

Before building any feature, read the **users** module end to end and follow the same shape:

| Layer | Backend reference | Frontend reference |
|---|---|---|
| Model | `backend/app/models/user.py` | |
| Schema (API contract) | `backend/app/schemas/user.py` | `frontend/src/api/types.ts` (generated) |
| Repository (queries) | `backend/app/repositories/users.py` | |
| Service (business rules, authz) | `backend/app/services/users.py` | |
| Router (HTTP) | `backend/app/routers/users.py` | |
| API calls + hooks | | `frontend/src/features/users/api.ts` |
| UI | | `frontend/src/features/users/UsersPage.tsx` |
| Tests | `backend/tests/integration/test_users_api.py` | `frontend/src/features/users/UsersPage.test.tsx` |

## Non-negotiable rules

1. **Layering.** Routers call services; services call repositories; repositories touch the DB. Routers contain no queries and no business rules. Services never import FastAPI. Only services `commit()`.
2. **Authorization lives in the service.** Every service method that reads or changes a record takes the acting user and checks ownership/role. Router-level `AdminUser`/`CurrentUser` is only the first gate. Records a user may not see return **404**, not 403.
3. **Errors.** Raise the typed errors in `app/core/exceptions.py`. Never raise `HTTPException` from services, and never return internal details to clients.
4. **Schemas.** Request schemas use `extra="forbid"`. Response schemas list fields explicitly: never return ORM objects or secrets (`password_hash`, tokens).
5. **Database changes go through Alembic.** Never edit a migration that has been committed; add a new one. Use the `db-migration` skill.
6. **Config comes from `app/core/config.py`** (backend) and `src/config/env.ts` (frontend). No `os.environ` / `import.meta.env` elsewhere. No secrets in code, in `VITE_*` variables, or in commits.
7. **Frontend API calls go through `src/api/client.ts`** via feature hooks. Never store tokens or sensitive data in `localStorage`/`sessionStorage`. Never use `dangerouslySetInnerHTML`.
8. **Every change ships with tests**: see the `write-tests` skill. Keep coverage ≥ 80% (auth and services close to 100%).
9. **Time is UTC and timezone-aware** (`app.utils.time.utcnow`).
10. **Logs** carry context (ids), never passwords, tokens, cookies or full request bodies.

## Commands

```bash
# Backend (run from backend/)
uv sync                                   # install
uv run uvicorn app.main:app --reload      # dev server on :8000
uv run pytest                             # tests (integration tests need TEST_DATABASE_URL)
uv run ruff check . && uv run ruff format --check . && uv run mypy app tests
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
uv run python -m app.cli create-admin --email you@example.com --name "You"

# Frontend (run from frontend/)
npm install
npm run dev                               # :5173, proxies /api to :8000
npm test                                  # vitest
npm run lint && npm run typecheck
npm run gen:api                           # regenerate API types after backend schema changes
```

## Skills in this repo (`.claude/skills/`)

| Skill | Use when |
|---|---|
| `engineering-standards` | Before writing any code: structure, conventions, definition of done |
| `write-tests` | Adding or changing behaviour |
| `run-tests` | Running and diagnosing the test suites |
| `db-migration` | Any model/schema change |
| `review-and-fix` | After a significant change: runs `/code-review` and fixes findings |
| `security-audit` | Before a release or after touching auth, input handling or dependencies |
| `ship-feature` | End-to-end: build → test → migrate → review → security check |
| `offline-deployment` | Packaging and installing for LAN/offline clients |
| `client-setup` | Starting a new client project from this template |

## Hooks

`.claude/settings.json` runs formatters after every edit and blocks edits to `.env` files and to
already-committed migrations. If a hook blocks you, fix the cause; don't work around it.
