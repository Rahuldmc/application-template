---
name: run-tests
description: Run the backend and frontend test suites, lint and type checks, and diagnose failures. Use after any code change, before committing, or when asked to run or fix tests.
---

# Running tests

## Full check (what CI runs)

```bash
# backend/
uv run ruff check . && uv run ruff format --check .
uv run mypy app tests
uv run pytest --cov

# frontend/
npm run lint && npm run format:check && npm run typecheck
npm run test:coverage
npm run build
```

Report results honestly: pass counts, failures with the relevant output, and anything skipped.

## Backend database for tests

Integration tests need `TEST_DATABASE_URL` pointing to a PostgreSQL database whose name ends in `_test` (the suite **wipes** it). Set it in `backend/.env` or the environment:

```
TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/app_test
```

If it's not set, integration tests are **skipped**, not passed. Say so explicitly when reporting. Never report "all tests pass" when integration tests were skipped.

No local Postgres? Either `docker compose up -d` at the repo root, or install PostgreSQL natively and create the `app` and `app_test` databases.

## Faster loops

```bash
uv run pytest tests/unit                      # no database needed
uv run pytest tests/integration/test_users_api.py -k "admin"
uv run pytest -x --lf                         # stop at first failure, rerun last failures
npx vitest run src/features/users             # one feature
npx vitest                                    # watch mode
```

## Diagnosing failures

1. Read the **first** failure fully; later ones are often consequences.
2. Decide whether the code or the test is wrong. Never weaken an assertion just to make it pass. If the test encoded a wrong expectation, explain why when you change it.
3. Common causes in this repo:
   - `401` where 200 was expected → the test didn't `login(...)`, or the client lost cookies (a failed refresh clears them).
   - `403 csrf_failed` → missing `headers=csrf(client)` on a write.
   - `422` → request body doesn't match the schema (`extra="forbid"` rejects unknown fields).
   - Frontend "unhandled request" → add an MSW handler for that endpoint.
   - Frontend element not found → the query is still loading; use `findBy*`.
   - `alembic check` fails → a model changed without a migration (see `db-migration`).
4. Fix, rerun the failing test, then rerun the full suite.

## Rules

- Don't skip, `xfail` or delete tests to get green. If a test is truly obsolete, say so and explain.
- Flaky test? Find the cause (ordering, time, shared state). Don't add retries.
