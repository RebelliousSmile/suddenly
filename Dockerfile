# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------------------
# Frontend builder: UnoCSS + Vite → static/dist
# -------------------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# -------------------------------------------------------------------
# Python builder: install dependencies from pyproject.toml
# -------------------------------------------------------------------
FROM base AS builder

COPY pyproject.toml .
RUN pip install --prefix=/install ".[federation]"

# -------------------------------------------------------------------
# Development target: used by docker-compose.dev.yml
# -------------------------------------------------------------------
FROM base AS dev

COPY pyproject.toml .
RUN pip install -e ".[dev,federation]"

COPY . .

# -------------------------------------------------------------------
# Final: production image
# -------------------------------------------------------------------
FROM base AS final

RUN groupadd --gid 1000 suddenly \
    && useradd --uid 1000 --gid suddenly --shell /bin/bash --create-home suddenly

# Python packages from builder
COPY --from=builder /install /usr/local

# Application code
COPY --chown=suddenly:suddenly . .

# Built frontend assets
COPY --from=frontend-builder --chown=suddenly:suddenly /static/dist/ ./static/dist/

RUN mkdir -p /app/staticfiles /app/media \
    && chown -R suddenly:suddenly /app/staticfiles /app/media \
    && chmod +x scripts/entrypoint.sh

USER suddenly

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

CMD ["scripts/entrypoint.sh"]
