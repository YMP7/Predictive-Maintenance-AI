# Security Policy

## Required Environment Variables

The following environment variables **must** be configured before starting the application:

| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET_KEY` | **Yes** | HMAC signing key for JWT tokens. The app will **refuse to start** without this. Generate one with: `openssl rand -hex 32` |
| `DATABASE_URL` | **Yes** | PostgreSQL connection string. The app will **refuse to start** without this. Format: `postgresql://user:pass@host:5432/dbname` |
| `CORS_ORIGINS` | Recommended | Comma-separated list of allowed frontend origins (e.g., `https://yourdomain.com`). Defaults to `http://localhost:3000` if unset. |
| `MQTT_USERNAME` | Required if MQTT used | Username for the MQTT broker (e.g. `backend_service`) |
| `MQTT_PASSWORD` | Required if MQTT used | Password for the MQTT broker. Fails loudly if `MQTT_BROKER_HOST` is set but creds are missing. |

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

### MQTT Ingestion Security
- **Authentication**: Mosquitto runs with `allow_anonymous false`. A `pwfile` is strictly enforced.
- **Access Control (ACL)**: Edge devices use per-device credentials (e.g., `device_M001`) and are strictly restricted via `mosquitto.acl` to only write to their own topic (`factory/M001/telemetry`). They cannot read data.
- **Payload Validation**: All incoming MQTT payloads are treated as entirely untrusted. They are deserialized and sanitized through strict Pydantic bounds (e.g. preventing negative temperatures, malformed JSON injections, and unknown machine IDs) before they ever touch the internal `DataService`. Malformed packets are logged and dropped without crashing the ingestion loop.

### Password Storage
- All user passwords are hashed with **bcrypt** and stored in the `users` table in TimescaleDB.
- No plaintext passwords are stored at rest — the `hashed_password` column contains only bcrypt `$2b$` hashes.
- User accounts are managed via `scripts/seed_dev.py` (development) or direct SQL (production).
- **Note on Test Accounts**: The credentials for `test_admin`, `test_operator`, and `demo_viewer` are intentionally public for CI/CD and local testing purposes. Their plaintext passwords can be found in `scripts/seed_dev.py` and `tests/test_api.py`. This is by design and not a security oversight.

## Known Limitations

> These are tracked as future work in the Implementation Plan and do not represent vulnerabilities in the current prototype scope.

1. **localStorage Token Storage**: JWT tokens are stored in the browser's `localStorage`. This is vulnerable to XSS (Cross-Site Scripting) attacks. A production deployment should migrate to HttpOnly cookies with `SameSite=Strict`. *(Deferred — out of scope for current hardening pass.)*
2. ~~**In-Memory User Store**~~: ✅ **RESOLVED** — User accounts are now stored in TimescaleDB's `users` table, replacing the old `fake_users_db` in-memory dict.
3. ~~**Weak Default Passwords**~~: ✅ **RESOLVED** — Demo passwords have been rotated to cryptographically generated 16-character secrets.
4. ~~**No Rate Limiting**~~: ✅ **RESOLVED** — The `/api/auth/login` endpoint is now rate-limited to 5 attempts per minute per IP via `slowapi`. Exceeding the limit returns HTTP 429 with a `Retry-After` header.

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do not** open a public GitHub issue.
2. Email the maintainer directly at the address listed in the repository profile.
3. Include a description of the vulnerability, steps to reproduce, and potential impact.
4. You will receive an acknowledgment within 48 hours and a fix timeline within 7 days.
