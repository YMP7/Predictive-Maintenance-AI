FROM node:20-slim AS frontend

WORKDIR /build
COPY client/package.json client/package-lock.json ./
RUN npm ci
COPY client ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    LOG_FILE=/app/logs/agent.log \
    SIMULATION_ENABLED=true

WORKDIR /app

COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements-ml.txt --extra-index-url https://download.pytorch.org/whl/cpu

COPY server ./server
COPY ml ./ml
COPY scripts ./scripts
COPY config ./config
# The API refuses to start without the C-MAPSS checkpoint; the dashboards read the dataset and result files.
COPY data/models ./data/models
COPY data/cmapss ./data/cmapss
COPY data/*.json ./data/
COPY --from=frontend /build/dist ./client/dist

RUN mkdir -p /app/data /app/logs \
    && adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()" || exit 1

CMD ["python", "server/integrated_server.py"]
