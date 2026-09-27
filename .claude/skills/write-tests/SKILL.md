---
name: write-tests
description: How to write backend (pytest) and frontend (Vitest + Testing Library + MSW) tests in this repo, including the required authorization test matrix. Use whenever adding or changing behaviour, fixing a bug, or when coverage is below target.
---

# Writing tests

Every behaviour change ships with tests. A bug fix starts with a failing test that reproduces the bug.

## Backend (pytest)

| Kind | Location | Uses | For |
|---|---|---|---|
| Unit | `tests/unit/` | nothing external | pure functions: security, schemas, config, utils |
| Integration | `tests/integration/` | real PostgreSQL | repositories, services, API endpoints |

Test against real Postgres, not SQLite or mocks: constraints, locking and types behave differently.

### Fixtures (`tests/conftest.py`)

- `db`: a SQLAlchemy session inside a transaction that is rolled back after each test. Services can `commit()` freely.
- `client`: `TestClient` wired to `db`, with an **https** base URL (needed for Secure cookies).
- `make_user(role=..., is_active=..., email=..., password=...)`: create users.
- `login(client, user)`: log in; cookies are stored on the client.
- `csrf(client)`: headers for POST/PUT/PATCH/DELETE: `client.post(url, json=..., headers=csrf(client))`.
- Two browsers: create a second `TestClient(client.app, base_url="https://testserver")` (see `db_client_pair` in `test_users_api.py`).

### Required authorization matrix for every endpoint

| Case | Expected |
|---|---|
| Anonymous | 401 |
| Logged in, wrong role | 403 |
| Another user's record | 404 (not 403: don't reveal existence) |
| Own record / right role | 2xx and correct body |
| Invalid input / unknown fields | 422 |
| Missing CSRF header on writes | 403 (covered centrally; add one if you add exempt paths) |

Plus the business rules: duplicates (409), state rules (422), and side effects (e.g. deactivation ends sessions).

### Style

- Group by endpoint in classes (`class TestCreateOrder:`). Name tests after behaviour: `test_user_cannot_read_others_and_gets_404`.
- Arrange / act / assert, separated by blank lines. One behaviour per test.
- Assert on status **and** body. Assert that secrets are absent from responses.
- No `time.sleep`. For time-based logic, set timestamps directly on the model.

## Frontend (Vitest)

- Tests sit next to the code: `UsersPage.test.tsx`.
- `renderApp(path)` from `src/test/render.tsx` renders the real providers and routes. Prefer it to rendering components in isolation.
- The network is mocked with MSW (`src/test/server.ts`). Unhandled requests **fail** the test. Override per test with `server.use(http.get(...))`. Helpers: `loggedInAs(user)`, `apiError(status, code, message, details)`.
- Query by what users see: `getByRole`, `getByLabelText`, `findByText`. Never by class name or test id unless nothing else works.
- Drive interactions with `userEvent`, and wait with `findBy*` / `vi.waitFor`.
- Test: loading, success, empty, and error states; role-based visibility; form validation; and that the right request payload was sent.

## Coverage

- Backend: `uv run pytest --cov` (fails under 80%).
- Frontend: `npm run test:coverage` (thresholds in `vite.config.ts`).
- Auth, security and service code should be close to 100%. Don't write assertion-free tests to game the number; cover real branches.

## Checklist

- [ ] New endpoint → full authorization matrix
- [ ] New service rule → a test for the allowed and the rejected path
- [ ] New migration → covered automatically (the suite runs upgrade → downgrade → upgrade); add a data test if it transforms data
- [ ] New page → loading / error / success / permission tests
- [ ] Bug fix → regression test that failed before the fix
