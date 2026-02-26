# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# Prevents Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------------------
# Frontend builder stage: build JS/CSS assets
# -------------------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# -------------------------------------------------------------------
# Builder stage: install Python dependencies
# -------------------------------------------------------------------
FROM base AS builder

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# -------------------------------------------------------------------
# Final stage: production image
# -------------------------------------------------------------------
FROM base AS final

# Create non-root user for security
RUN groupadd --gid 1000 suddenly \
    && useradd --uid 1000 --gid suddenly --shell /bin/bash --create-home suddenly

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=suddenly:suddenly . .

# Copy built frontend assets
COPY --from=frontend-builder --chown=suddenly:suddenly /static/ ./static/

# Créer staticfiles et media avec les bons droits avant de switcher d'utilisateur
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R suddenly:suddenly /app/staticfiles /app/media \
    && chmod +x scripts/entrypoint.sh

USER suddenly

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# collectstatic + migrate + gunicorn au démarrage (vars Railway disponibles)
CMD ["scripts/entrypoint.sh"]
