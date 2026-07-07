FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    LOG_FILE=/app/logs/agent.log \
    SIMULATION_ENABLED=true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai_agent.py alert_handler.py backend_api.py data_service.py data_sync.py integrated_server.py sensor_simulator.py ./
COPY config ./config
COPY client/dist ./client/dist

RUN mkdir -p /app/data /app/logs \
    && adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()" || exit 1

CMD ["python", "integrated_server.py"]
