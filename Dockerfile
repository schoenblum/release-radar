# syntax=docker/dockerfile:1

# The frontend build output is the same on every architecture, so this stage runs
# natively on the build machine even when building for another platform.
FROM --platform=$BUILDPLATFORM node:24-alpine AS frontend
WORKDIR /srv/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# pg_dump must match the Postgres 16 server, and bookworm ships version 15, so the
# client comes from the PostgreSQL project's own repository.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
       -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
       > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && apt-get purge -y --auto-remove curl gnupg \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1000 app
WORKDIR /srv/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


# Source code is mounted from the host in development.
FROM base AS dev
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
USER app
ENTRYPOINT ["sh", "docker/entrypoint.sh"]


FROM base AS runtime
COPY alembic.ini ./
COPY alembic/ alembic/
COPY app/ app/
COPY docker/ docker/
COPY ops/ ops/
COPY --from=frontend /srv/frontend/dist/ app/static/
USER app
ENTRYPOINT ["sh", "docker/entrypoint.sh"]
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --workers ${UVICORN_WORKERS:-2}"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request as r; r.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4)"]
