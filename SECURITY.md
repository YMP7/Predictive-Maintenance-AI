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
| `NOTIFICATIONS_ENABLED` | No (default: `false`) | Set to `true` to enable SMS/email/voice dispatch. When `true`, all Twilio + SMTP credentials below become **required**. |
| `TWILIO_ACCOUNT_SID` | Required if notifications enabled | Twilio API account SID |
| `TWILIO_AUTH_TOKEN` | Required if notifications enabled | Twilio API auth token |
| `TWILIO_FROM_NUMBER` | Required if notifications enabled | Twilio sender phone number |
| `SMTP_HOST` | Required if notifications enabled | SMTP server hostname |
| `SMTP_FROM` | Required if notifications enabled | Email sender address |

## Security Hardening Applied

### JWT Authentication & XSS Mitigation (Phase 6)
- JWT session tokens are now stored exclusively in secure, HttpOnly, and SameSite (`Lax`) cookies rather than `localStorage`. This prevents token extraction via Cross-Site Scripting (XSS) attacks.
- A custom header (`X-API-Request: true`) is strictly required on all state-modifying requests, forcing CORS preflight checks and preventing Cross-Site Request Forgery (CSRF).
- Tokens expire after 24 hours (`ACCESS_TOKEN_EXPIRE_MINUTES = 1440`).
- The application crashes on startup if `JWT_SECRET_KEY` is not set — there is no insecure fallback.

### Role-Based Access Control (RBAC)
- All control endpoints (such as `/api/simulation/*` and `/api/machines/*/fault`) require a valid JWT with the `admin` role.
- Operator actions (e.g. manual work order creation) are restricted to accounts with the `operator` or `admin` role.
- Read-only dashboard endpoints (telemetry streams) are public for seamless visualization.

### CORS Policy
- CORS does not default to a wildcard `*` wildcard.
- If `CORS_ORIGINS` is unset, it restricts access to local dev URLs and logs a warning.

### MQTT Ingestion Security (Phase 5)
- **Authentication**: Mosquitto runs with `allow_anonymous false` and strictly enforces encrypted passwords (`pwfile`).
- **Access Control (ACL)**: Edge devices use unique, per-device credentials and are strictly limited via `mosquitto.acl` to publish to `factory/{machine_id}/telemetry`. Devices cannot subscribe or read other machines' telemetry.
- **Payload Validation**: Incoming telemetry payloads are fully sanitized and validated against strict schema boundaries (e.g. blocking negative temperatures, missing columns, or SQL injection payloads) at the API gateway level before database writing.

### Password Storage
- User passwords are encrypted using **bcrypt** and stored in TimescaleDB. Plaintext passwords are never stored at rest.

### Telemetry Grounding & Provenance Safeguards (Phase 8)
To prevent adversarial instructions or injected telemetry from executing unauthorized actions via the Agentic AI:
- **Telemetry Grounding Validation**: The agent's `create_work_order` tool verifies that a matching Critical/High alert was logged in the database within the last 24 hours before authorizing a work order.
- **Provenance Isolation**: A `source` column on the `alerts` table restricts valid grounding alerts strictly to those with `source = 'ai_pipeline'` (inserted only by the internal telemetry processing loop). Injected alerts (written manually or via compromised devices) default to `source = 'unknown'` and will fail validation.
- **Daily Volume Cap**: Limits autonomous work order creation requests to a maximum of 3 work orders per day per machine, preventing resource exhaustion.
- **Audit Logging**: All validation results, rejections, and raw data snapshots are logged to `work_order_audit_log` for compliance auditing.

### Notification Credentials (Phase 5)
- **Fail-loud at startup**: The backend raises a `RuntimeError` on startup if `NOTIFICATIONS_ENABLED=true` but required SMTP/Twilio credentials are missing.
- **Debounce persistence**: Cooldown states are stored in the database (`notifications_sent` hypertable) to prevent alert storm cascades after system reboots.

## Known Limitations

1. **Untested Twilio Delivery**: Twilio notifications have only been verified against the Twilio Sandbox.
2. **No Deployed HTTPS**: Deployed environments must use Nginx as a reverse proxy with Let's Encrypt SSL configuration.
3. **No UI Resolution Flow**: Operators must manually close/resolve work orders via raw DB queries since a front-end closure workflow is not yet implemented.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:
1. Do not open a public GitHub issue.
2. Email the maintainer directly.
3. We will respond within 48 hours and coordinate a fix.
