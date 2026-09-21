#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-ai-digital-twin}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"
LOG_DIR="${LOG_DIR:-/var/log/ai-digital-twin}"
MONITOR_SCRIPT="${MONITOR_SCRIPT:-/usr/local/bin/monitor-ai-digital-twin.sh}"
LOGROTATE_FILE="${LOGROTATE_FILE:-/etc/logrotate.d/ai-digital-twin}"
CRON_FILE="${CRON_FILE:-/etc/cron.d/ai-digital-twin-monitor}"

for command in docker curl grep; do
    if ! command -v "${command}" >/dev/null 2>&1; then
        echo "Required command not found: ${command}" >&2
        exit 1
    fi
done

mkdir -p "${LOG_DIR}"
chmod 755 "${LOG_DIR}"

cat > "${LOGROTATE_FILE}" <<LOGROTATE
${LOG_DIR}/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
}
LOGROTATE

cat > "${MONITOR_SCRIPT}" <<MONITOR
#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="\${CONTAINER_NAME:-${CONTAINER_NAME}}"
HEALTH_URL="\${HEALTH_URL:-${HEALTH_URL}}"

if ! docker ps --format '{{.Names}}' | grep -qx "\${CONTAINER_NAME}"; then
    docker start "\${CONTAINER_NAME}" >/dev/null
fi

if ! curl -fsS "\${HEALTH_URL}" >/dev/null; then
    docker restart "\${CONTAINER_NAME}" >/dev/null
fi

printf 'AI Digital Twin monitor passed at %s\n' "\$(date -Is)"
MONITOR

chmod +x "${MONITOR_SCRIPT}"

cat > "${CRON_FILE}" <<CRON
*/5 * * * * root ${MONITOR_SCRIPT} >> ${LOG_DIR}/monitor.log 2>&1
CRON
chmod 0644 "${CRON_FILE}"

echo "Monitoring configured for ${CONTAINER_NAME}"
