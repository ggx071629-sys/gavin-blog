# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.12.4 AS uv
FROM python:3.11-slim-bookworm AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY apps/api/embedding_service/pyproject.toml apps/api/embedding_service/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project

FROM python:3.11-slim-bookworm AS runtime
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
WORKDIR /app
RUN groupadd --gid 10001 gavin && useradd --uid 10001 --gid 10001 --no-create-home gavin \
    && mkdir /models && chown 10001:10001 /models
COPY --from=build /app/.venv ./.venv
COPY apps/api/app ./app
COPY apps/api/scripts/download_e5.py ./scripts/download_e5.py
USER 10001:10001
EXPOSE 8091
CMD ["uvicorn", "app.local_embedding.service:create_app", "--factory", "--host", "0.0.0.0", "--port", "8091", "--workers", "1", "--no-proxy-headers", "--no-access-log"]
