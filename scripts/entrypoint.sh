#!/bin/sh
# Entrypoint script — exécuté au démarrage du conteneur.
# Les variables d'environnement Railway sont disponibles ici.
set -e

echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Creating DB cache table (no-op if already exists)..."
python manage.py createcachetable 2>/dev/null || true

echo "==> Starting gunicorn..."
exec gunicorn suddenly.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile -
