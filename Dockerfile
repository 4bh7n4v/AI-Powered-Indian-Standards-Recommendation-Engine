# syntax=docker/dockerfile:1
# Single container for Linux, Windows (Docker Desktop) and macOS (Intel and Apple Silicon).
# Both base images are multi-arch, so the same file builds natively on amd64 and arm64.

# ---- Stage 1: build the React web app ---------------------------------------------------
FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
# Cache mount: packages already downloaded survive a failed build, so a retry resumes.
RUN --mount=type=cache,target=/root/.npm \
    npm config set fetch-retries 6 && npm config set fetch-retry-maxtimeout 120000 \
 && npm ci --no-fund --no-audit
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python API that also serves the built web app -----------------------------
FROM python:3.12-slim AS app

# true = also install PyTorch + sentence-transformers for BGE-M3 dense retrieval (~2 GB larger image).
ARG INSTALL_ML=false
# Optional PyPI mirror when files.pythonhosted.org is slow or blocked on your network.
ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    ISRE_VAR_DIR=/data/var \
    ISRE_LOG_DIR=/data/logs \
    ISRE_FRONTEND_DIST=/app/frontend/dist \
    HF_HOME=/data/models

WORKDIR /app/backend
COPY backend/requirements.txt backend/requirements-ml.txt ./
# Cache mount keeps downloaded wheels between builds (outside the image), so a flaky
# connection only has to fetch what is still missing on the next attempt.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --index-url "$PIP_INDEX_URL" -r requirements.txt \
 && if [ "$INSTALL_ML" = "true" ]; then pip install --index-url "$PIP_INDEX_URL" -r requirements-ml.txt; fi

COPY backend/ ./
COPY samples/ /app/samples/
COPY --from=web /web/dist /app/frontend/dist

# Run as an unprivileged user. UID 1000 matches the first user on most Linux hosts, so files
# written to bind-mounted folders (logs, var) stay owned by you.
RUN useradd --uid 1000 --create-home app \
 && mkdir -p /data/var /data/logs /data/models \
 && chown -R app:app /data
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# --no-access-log: requests are logged as structured JSON by the app's own middleware.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
