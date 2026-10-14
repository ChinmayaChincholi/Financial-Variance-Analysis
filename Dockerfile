# syntax=docker/dockerfile:1
#
# Hosted web demo of Variance Studio (one container = frontend + API).
# The offline desktop application does not use this file.

# ---------- 1. Build the React interface in web-demo mode ----------
FROM node:20-alpine AS frontend
WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# Turns on the web-only parts of the interface (banner, sample dataset button).
ENV VITE_APP_MODE=web
RUN npm run build


# ---------- 2. Python runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VARIANCE_STUDIO_MODE=web \
    VARIANCE_STUDIO_DATA_DIR=/data

# gosu lets the entrypoint fix the data volume's ownership and then drop root.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend /build/frontend/dist frontend/dist

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
# The sed strips Windows (CRLF) line endings, which would otherwise break the
# script's shebang when the repository is checked out on Windows.
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /data \
    && chown app:app /data

WORKDIR /app/backend
EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]

# One worker on purpose: storage is SQLite and the processing limit is
# counted in-process. $PORT is set by most hosts; 8000 otherwise.
CMD ["sh", "-c", "exec uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*' --no-server-header"]