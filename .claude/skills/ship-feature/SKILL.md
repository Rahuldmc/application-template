---
name: ship-feature
description: End-to-end workflow to build a feature to production quality in this repo - plan, implement across backend and frontend following the reference module, write and run tests, create migrations, review and fix, and run a security check. Use when asked to build, add or implement a feature or module.
---

# Ship a feature

Work through these steps in order. Don't skip a step because the change "looks small". Report progress at each stage.

## 1. Understand and plan
- Restate the requirement. Ask about anything ambiguous that changes the design: who may do what, validation rules, edge cases.
- List the files you'll create or change, per layer (see `engineering-standards` → "Adding a feature module").
- Define the authorization rules explicitly: which roles; ownership; what others see (404).

## 2. Backend
- Model → register in `app/models/__init__.py`
- Migration → `db-migration` skill (generate, review, up/down/up, `alembic check`)
- Schemas (`extra="forbid"` on input) → repository → service (authz + rules + commit) → router → register router
- Tests → `write-tests` skill (authorization matrix + rules)
- `run-tests` for the backend

## 3. Frontend
- `npm run gen:api` → aliases in `src/api/types.ts`
- `src/features/<name>/api.ts` (calls + React Query hooks) → pages/components → route in `src/app/router.tsx` (with `ProtectedRoute roles` if restricted) → nav link if needed
- Tests: loading / error / success / permission / form validation
- `run-tests` for the frontend

## 4. Quality gates
- `review-and-fix` skill: review, fix, re-review until no Critical/High/Medium findings remain
- `security-audit` skill if the feature touches auth, permissions, user input, files, or dependencies (most features do)
- Full `run-tests` pass

## 5. Hand-off
Summarize:
- What was built (endpoints, pages, tables)
- Authorization rules implemented
- Migration name and anything special about it (data changes, irreversibility)
- Test results (counts, coverage) and review/security findings with their status
- Follow-ups or known limitations

Commit only when the user asks. Use a clear message describing the feature.
