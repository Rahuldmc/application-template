---
name: review-and-fix
description: Run a code review on the current changes with the built-in /code-review, triage the findings, fix the real ones, verify with tests, and re-review. Use after a major code change, before opening a PR, or when asked to review and address findings.
---

# Review and fix

## 1. Scope the review

```bash
git status
git diff --stat main...HEAD   # or against the branch you started from
```

Know what changed and why before judging it.

## 2. Run the review

Invoke the built-in **`code-review`** skill on the current diff (`/code-review`, or `/code-review high` for a large or risky change such as auth, payments or migrations).

Then check the diff against this repo's rules, which a generic review can miss:

- [ ] Layering: no queries or business rules in routers; services don't import FastAPI; only services commit
- [ ] Authorization in the service; other users' records → 404; tests for each role
- [ ] Request schemas have `extra="forbid"`; responses don't leak internal fields
- [ ] Typed errors, not `HTTPException`, in services
- [ ] Model changes have a reviewed migration (`db-migration` checklist)
- [ ] Frontend calls go through feature hooks → `api` client; no `any`; loading/error states handled
- [ ] Tests cover the new behaviour (`write-tests` matrix)
- [ ] New config in `.env.example`; no secrets in code

## 3. Triage every finding

Record each as:

| # | Severity | File:line | Finding | Decision |
|---|---|---|---|---|
| 1 | High | `app/services/orders.py:42` | Missing ownership check on update | Fix |
| 2 | Low | … | Style preference | Won't fix: conflicts with repo convention |

- **Critical/High** (security, data loss, wrong results): must fix.
- **Medium** (robustness, missing tests, unclear code): fix unless there's a concrete reason not to.
- **Low** (style, naming): fix if cheap and consistent with the repo.
- False positive: say why, briefly. Don't silently drop findings.

## 4. Fix

- One finding at a time. For each bug, first add a test that fails, then fix it.
- Keep fixes minimal. Don't refactor unrelated code in the same pass.

## 5. Verify

Run the full check from the `run-tests` skill. Everything green, nothing newly skipped.

## 6. Re-review

Run `/code-review` again on the updated diff. Repeat until no Critical/High/Medium findings remain.

## 7. Report

Summarize for the user: the findings table with final status, what changed, and the test results. List anything intentionally deferred, with the reason.
