# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.12.4 AS uv
FROM python:3.11-slim-bookworm AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project
COPY apps/api/app ./app
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable

FROM python:3.11-slim-bookworm AS runtime
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN groupadd --gid 10001 gavin && useradd --uid 10001 --gid 10001 --no-create-home gavin \
    && mkdir -p /data/content /data/media /data/runtime /models \
    && chown 10001:10001 /data/content /data/media /data/runtime /models
COPY --from=build /app/.venv ./.venv
COPY apps/api/app ./app
COPY apps/api/migrations ./migrations
COPY apps/api/assistant_runtime_migrations ./assistant_runtime_migrations
COPY apps/api/alembic.ini apps/api/assistant_runtime_alembic.ini ./
COPY apps/api/scripts ./scripts
COPY deploy/bootstrap.py deploy/check_api.py deploy/assistant-control.py /opt/deploy/
USER 10001:10001
EXPOSE 8000
CMD ["python", "/opt/deploy/check_api.py"]
