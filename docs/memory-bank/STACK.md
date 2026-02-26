# Stack Technique — Suddenly

## Backend

@requirements.txt

### Dépendances principales

| Package | Version | Usage |
|---------|---------|-------|
| **Django** | 5.x | Framework web principal |
| **psycopg2** | latest | Connecteur PostgreSQL |
| **django-allauth** | latest | Authentification |
| **celery** | latest | Tâches asynchrones (optionnel) |
| **redis** | latest | Cache + broker Celery (optionnel) |
| **cryptography** | latest | HTTP Signatures ActivityPub |
| **requests** | latest | Appels HTTP (fédération) |
| **bleach** | latest | Sanitisation HTML/Markdown |

### Dépendances dev

| Package | Usage |
|---------|-------|
| **mypy** | Vérification types statique |
| **ruff** | Linter Python |
| **black** | Formateur de code |
| **pytest** | Tests |
| **pytest-django** | Intégration Django |

## Frontend

| Technologie | Usage | CDN |
|-------------|-------|-----|
| **HTMX** | Interactions dynamiques sans JS | `unpkg.com/htmx.org` |
| **Alpine.js** | État UI léger (modals, etc.) | `cdn.jsdelivr.net` |
| **Tailwind CSS** | Styles utilitaires | CDN ou build |

Pas de build frontend obligatoire — tout peut tourner avec les CDN.

## Infrastructure

| Composant | Requis | Optionnel | Fallback |
|-----------|--------|-----------|---------|
| **Python 3.12+** | ✅ | — | — |
| **PostgreSQL 16+** | ✅ | — | — |
| **Redis** | — | ✅ | Cache DB Django |
| **Celery** | — | ✅ | Tâches synchrones |
| **Nginx** | — | ✅ (VPS) | Serveur Django direct |
| **Gunicorn** | — | ✅ (prod) | `runserver` (dev) |
| **Docker** | — | ✅ | Déploiement direct |

## Environnements

| Variable | Requis | Description |
|----------|--------|-------------|
| `SECRET_KEY` | ✅ | Clé secrète Django (64+ chars) |
| `DATABASE_URL` | ✅ | URL PostgreSQL |
| `DOMAIN` | ✅ | Domaine de l'instance |
| `DEBUG` | — | `false` en prod |
| `REDIS_URL` | — | URL Redis si disponible |
| `CELERY_ENABLED` | — | `true` si Redis dispo |
| `EMAIL_HOST` | — | Serveur SMTP |
| `FEDERATION_ENABLED` | — | `true` par défaut |

@.env.example
