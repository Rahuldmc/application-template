---
name: engineering-standards
description: Project structure, coding conventions, security rules and definition of done for this FastAPI + React template. Use before writing or changing any backend or frontend code, and when adding a new feature module.
---

# Engineering standards

Read `CLAUDE.md` first. This skill expands it with the how and the why.

## Backend layers

```
routers/    HTTP only: declare inputs/outputs, attach auth dependencies, call a service
services/   business rules + authorization; owns the transaction (commit)
repositories/  queries for one model, built on database/repository.py BaseRepository
models/     SQLAlchemy tables
schemas/    Pydantic request/response models (the API contract)
core/       config, security, cookies, dependencies, middleware, exceptions, logging
database/   engine/session, declarative Base + mixins, BaseRepository
utils/      small pure helpers with no HTTP or business knowledge
```

Dependency direction is one way: `routers → services → repositories → models`. A lower layer never imports a higher one.

**Why:** routers stay trivially reviewable, services are testable without HTTP, and authorization has one obvious home.

## Adding a feature module (e.g. "orders")

Create these, copying the users module's shape:

1. `app/models/order.py`: inherit `UUIDPrimaryKeyMixin, TimestampMixin, Base`. Register it in `app/models/__init__.py` (Alembic only sees imported models).
2. `app/schemas/order.py`: `OrderCreate`/`OrderUpdate` with `model_config = ConfigDict(extra="forbid")`; `OrderRead` with `from_attributes=True` and explicit fields.
3. `app/repositories/orders.py`: `class OrderRepository(BaseRepository[Order])`, plus model-specific queries. Scope queries by owner where relevant (e.g. `where(Order.user_id == actor.id)`).
4. `app/services/orders.py`: `OrderService(db)`; each method takes `actor: User`; checks ownership/role; raises typed errors; calls `self.db.commit()` once at the end of a write.
5. `app/routers/orders.py`: thin endpoints using `DbSession`, `CurrentUser`/`AdminUser`. Register in `app/routers/__init__.py`.
6. Migration: follow the `db-migration` skill.
7. Tests: `tests/integration/test_orders_api.py` with the authorization matrix (see `write-tests`).
8. Frontend: run `npm run gen:api`, add aliases in `src/api/types.ts`, create `src/features/orders/{api.ts,OrdersPage.tsx,OrdersPage.test.tsx}`, add the route in `src/app/router.tsx`.

## Backend conventions

- Type hints everywhere; `mypy --strict` must pass.
- Sync endpoints (`def`, not `async def`). FastAPI runs them in a threadpool. Never call blocking code inside `async def`.
- Errors: raise `NotFoundError`, `ConflictError`, `PermissionDeniedError`, `AuthenticationError`, `BusinessRuleError` (or a new subclass of `AppError`). The global handler shapes the response.
- Pagination: `offset`/`limit` query params with `le=100`; return `Page[T]`.
- Never build SQL with f-strings or `%`. Use SQLAlchemy expressions; if raw SQL is unavoidable, `text()` with bound parameters.
- Passwords: `hash_password`/`verify_password` only. Never log or return them.
- New settings go in `Settings` (typed, with a safe default) **and** in `backend/.env.example` with a comment.

## Frontend structure

```
src/app/          router, providers, query client
src/api/          client.ts (the only fetch), errors.ts, generated/ + types.ts
src/features/<x>/ api.ts (calls + React Query hooks), pages/components, tests
src/components/   shared UI (ui/) and layout (layout/)
src/routes/       route guards and generic pages
src/lib/          small helpers
src/config/       env access
```

- Components call feature hooks (`useUsers`), never `api.*` or `fetch` directly.
- Server state lives in React Query. Don't copy it into `useState`.
- Forms: validate with zod before submitting; show `ApiError.fieldErrors` from the server next to inputs.
- Role checks in the UI (`hasRole`, `ProtectedRoute roles`) are UX only. The backend enforces access.
- Redirect targets must be internal paths (see `safeRedirect` in `LoginPage.tsx`).
- No `any`, no `dangerouslySetInnerHTML`, no tokens in web storage (ESLint enforces these).

## Security invariants (never weaken without a documented reason)

- Auth cookies: `httpOnly`, `Secure`, `SameSite`; refresh cookie path-scoped to `/api/v1/auth`.
- CSRF middleware protects every unsafe `/api` method except login.
- Access tokens are checked against `user.token_version` and `is_active` on every request.
- Refresh tokens rotate; reuse revokes the whole family.
- Login: generic error, timing-equalized for unknown users, lockout after repeated failures.
- Production refuses to start with a weak `JWT_SECRET_KEY` or insecure cookies.

## Definition of done

- [ ] Follows the layers above; no business logic in routers or components
- [ ] Authorization checked in the service, with tests for each role and for other users' records
- [ ] Tests added/updated; `uv run pytest` and `npm test` pass; coverage ≥ 80%
- [ ] `ruff`, `mypy`, `eslint`, `tsc` clean
- [ ] Migration created and reviewed if models changed; `alembic check` clean
- [ ] `npm run gen:api` run if the API contract changed
- [ ] New config documented in the relevant `.env.example`
- [ ] `review-and-fix` run for significant changes; `security-audit` if auth, input handling or dependencies changed
