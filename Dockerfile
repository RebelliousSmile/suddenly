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
    gettext \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------------------
# Frontend builder: UnoCSS + Vite → static/dist
# -------------------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
# UnoCSS scans ../templates/ and ../suddenly/ — copy them before build
COPY templates/ ../templates/
COPY suddenly/ ../suddenly/
RUN npm run build
# Output: /app/static/dist/ (vite.config.js: outDir = '../static/dist')

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

# Copy all code first (needed for editable install)
COPY . .
RUN pip install -e ".[dev,federation]"

# -------------------------------------------------------------------
# Final: production image
# -------------------------------------------------------------------
FROM base AS final

ENV DJANGO_SETTINGS_MODULE=config.settings.production

RUN groupadd --gid 1000 suddenly \
    && useradd --uid 1000 --gid suddenly --shell /bin/bash --create-home suddenly

# Python packages from builder
COPY --from=builder /install /usr/local

# Application code
COPY --chown=suddenly:suddenly . .

# Built frontend assets from Vite
COPY --from=frontend-builder --chown=suddenly:suddenly /app/static/dist/ ./static/dist/

RUN DJANGO_SETTINGS_MODULE=config.settings.development python manage.py compilemessages -l fr -l en \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R suddenly:suddenly /app/staticfiles /app/media \
    && chmod +x scripts/entrypoint.sh

USER suddenly

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

CMD ["scripts/entrypoint.sh"]
