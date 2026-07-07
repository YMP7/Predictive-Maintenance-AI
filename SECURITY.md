# Security Policy

## Required Environment Variables

The following environment variables **must** be configured before starting the application:

| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET_KEY` | **Yes** | HMAC signing key for JWT tokens. The app will **refuse to start** without this. Generate one with: `openssl rand -hex 32` |
| `CORS_ORIGINS` | Recommended | Comma-separated list of allowed frontend origins (e.g., `https://yourdomain.com`). Defaults to `http://localhost:3000` if unset. |

## Security Hardening Applied

### JWT Authentication
- All control endpoints (`/api/simulation/*`, `/api/machines/*/fault`) require a valid JWT Bearer token with `admin` role.
- Read-only dashboard endpoints (`/api/dashboard/summary`, `/api/machines/*/telemetry`) are public to allow the dashboard to display data without login.
- Tokens expire after 24 hours (`ACCESS_TOKEN_EXPIRE_MINUTES = 1440`).
- The app crashes on startup if `JWT_SECRET_KEY` is not set — there is no insecure fallback.

### CORS Policy
- CORS no longer defaults to wildcard `*`.
- When `CORS_ORIGINS` is not set, the server only accepts requests from `http://localhost:3000` and logs a warning.
- In production, set `CORS_ORIGINS` to the exact URL of your deployed frontend.

### Password Storage
- All user passwords are hashed with **bcrypt** via the `passlib` library.
- No plaintext passwords are stored at rest.

## Known Limitations

> These are tracked as future work in the Implementation Plan and do not represent vulnerabilities in the current prototype scope.

1. **localStorage Token Storage**: JWT tokens are stored in the browser's `localStorage`. This is vulnerable to XSS (Cross-Site Scripting) attacks. A production deployment should migrate to HttpOnly cookies with `SameSite=Strict`. *(Deferred — out of scope for current hardening pass.)*
2. **In-Memory User Store**: User accounts are currently hardcoded in `backend_api.py` (`fake_users_db`). This will be migrated to TimescaleDB in Step 3 of the Implementation Plan. *(Deferred — tied to database migration.)*
3. ~~**Weak Default Passwords**~~: ✅ **RESOLVED** — Demo passwords have been rotated to cryptographically generated 16-character secrets.
4. ~~**No Rate Limiting**~~: ✅ **RESOLVED** — The `/api/auth/login` endpoint is now rate-limited to 5 attempts per minute per IP via `slowapi`. Exceeding the limit returns HTTP 429 with a `Retry-After` header.

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do not** open a public GitHub issue.
2. Email the maintainer directly at the address listed in the repository profile.
3. Include a description of the vulnerability, steps to reproduce, and potential impact.
4. You will receive an acknowledgment within 48 hours and a fix timeline within 7 days.
