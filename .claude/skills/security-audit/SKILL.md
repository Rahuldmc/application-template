---
name: security-audit
description: Security review of the application - runs the built-in /security-review, automated scanners (bandit, pip-audit, npm audit, gitleaks) and a checklist covering auth, sessions, authorization, input handling, secrets, headers and deployment. Use before a release, after changes to auth/permissions/input handling/dependencies, or when asked for a security check.
---

# Security audit

## 1. Automated scans

```bash
# backend/
uv run bandit -q -c pyproject.toml -r app
uv export --no-dev --no-hashes --format requirements-txt > /tmp/req.txt && uv run pip-audit -r /tmp/req.txt
uv run ruff check . --select S          # security lint rules

# frontend/
npm audit --omit=dev
npm run lint                             # includes XSS / token-storage rules

# repo root (if gitleaks is installed)
gitleaks detect --source . --no-banner
```

## 2. Review the changes

Invoke the built-in **`security-review`** skill (`/security-review`) on the pending changes.

## 3. Checklist (whole application, not just the diff)

### Authentication and sessions
- [ ] Passwords hashed with argon2 (`hash_password`); min 12 / max 128 chars
- [ ] Login errors are generic; unknown emails take the same time (`burn_password_check`)
- [ ] Lockout after `MAX_FAILED_LOGINS`
- [ ] Access token ≤ 15 min; algorithm pinned; `iss`/`aud`/`exp`/`type` verified
- [ ] Refresh tokens: random, stored hashed, rotated, reuse revokes the family, revoked on logout and password change
- [ ] `token_version` bumped on password change, role change and deactivation
- [ ] Cookies: `HttpOnly` (access, refresh), `Secure`, `SameSite`; refresh path-scoped

### Authorization
- [ ] Every non-public endpoint has `CurrentUser` / `AdminUser`
- [ ] Every service method checks ownership or role on the **specific record** (IDOR)
- [ ] Other users' records → 404
- [ ] Users can't change their own role, status, or protected fields (`extra="forbid"`)
- [ ] Tests exist for each of the above

### Input and output
- [ ] All input goes through Pydantic schemas with bounds (lengths, ranges, `le=` on limits)
- [ ] No SQL built from strings; no `text()` with interpolation
- [ ] No `eval`, `exec`, `pickle`, `subprocess` with user input, `yaml.load`
- [ ] File uploads (if any): size limit, type allowlist, stored outside the web root, random names
- [ ] Responses never include hashes, tokens, stack traces or internal ids that shouldn't leak
- [ ] Validation errors don't echo submitted values

### CSRF / CORS / headers
- [ ] CSRF middleware active; exempt list is only `/auth/login`
- [ ] `CORS_ORIGINS` empty (same-origin) or an explicit allowlist; never `*` with credentials
- [ ] API responses: CSP `default-src 'none'`, `nosniff`, `X-Frame-Options DENY`, `no-store`
- [ ] Caddy (SPA): strict CSP with no `unsafe-inline`/`unsafe-eval`; HSTS in cloud mode

### Frontend
- [ ] No `dangerouslySetInnerHTML`, no tokens in `localStorage`/`sessionStorage`
- [ ] No secrets in `VITE_*` variables (they're public)
- [ ] Redirects after login only to internal paths
- [ ] Source maps off in production builds

### Secrets and configuration
- [ ] No secrets committed (`git log -p | gitleaks`, or check the diff manually)
- [ ] Production: `ENVIRONMENT=production`, strong `JWT_SECRET_KEY` (the app refuses weak ones), `ENABLE_DOCS=false`
- [ ] `.env` files are `chmod 600` on servers

### Infrastructure / deployment
- [ ] Only Caddy exposes ports; Postgres and the backend are on the internal network
- [ ] Containers run as non-root
- [ ] Backups run, are copied off-machine, and a restore has been tested
- [ ] Logs contain no passwords, tokens or cookies

## 4. Report

For each finding: **severity** (Critical/High/Medium/Low), **location**, **exploit scenario** (who can do what), **fix**. Fix Critical/High before release, with a regression test each. Then rerun the scans and tests and report the final state honestly, including anything not checked.
