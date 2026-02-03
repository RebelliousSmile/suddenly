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

# Collect static files
RUN python manage.py collectstatic --noinput --clear

USER suddenly

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run with gunicorn
CMD ["gunicorn", "suddenly.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4"]
