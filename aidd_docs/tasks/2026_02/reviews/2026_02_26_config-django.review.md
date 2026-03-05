# Code Review for config-django (Tâche 01)

Configuration Django modulaire base/development/production + asgi + pyproject.toml.

- Statut: Terminé
- Confidence: 🟡 Quelques points à corriger

## Main expected Changes

- [x] `config/settings/base.py` — INSTALLED_APPS, MIDDLEWARE, SITE_ID
- [x] `config/settings/development.py` — EMAIL_BACKEND
- [x] `config/asgi.py` — créé
- [x] `pyproject.toml` — django-htmx ajouté

## Scoring

| Title | Files | Score |
|-------|-------|-------|
| `"0.0.0.0"` dans ALLOWED_HOSTS (bind address, pas un hostname HTTP valide) | `config/settings/development.py:15` | 1 |
| `STATICFILES_STORAGE` déprécié en Django 5.x — remplacé par `STORAGES` | `config/settings/base.py:116`, `development.py:16` | 2 |
| `CELERY_BEAT_SCHEDULE` référence des tâches inexistantes (`suddenly.activitypub.tasks.*`) | `config/settings/base.py:132-141` | 1 |

## ✅ Code Quality Checklist

### Potentially Unnecessary Elements

- [🟢] Aucun import mort, aucune variable inutilisée

### Standards Compliance

- [🟢] Naming conventions suivies (SCREAMING_SNAKE_CASE pour settings)
- [🟢] Docstrings présentes sur chaque fichier
- [🟢] Règles KISS/YAGNI/DRY respectées

### Architecture

- [🟢] Séparation base/development/production correcte
- [🟢] Fail Fast en production (KeyError sur vars manquantes)
- [🟢] Divergences intentionnelles documentées dans la tâche

### Code Health

- [🟢] Taille des fichiers : base.py 267 lignes < 500 max
- [🟡] **`STATICFILES_STORAGE` déprécié** `config/settings/base.py:116` Django 5.x a remplacé ce setting par `STORAGES = {"staticfiles": {...}}` — génère des DeprecationWarnings en production (utiliser `STORAGES`)
- [🟡] **Celery Beat tâches fantômes** `config/settings/base.py:132-141` `suddenly.activitypub.tasks.*` non encore implémentées — Celery Beat loggue des erreurs au démarrage (acceptable pour scaffolding, à résoudre en tâche ActivityPub)

### Security

- [🟢] SQL injection : ORM Django exclusivement
- [🟢] XSS : headers sécurité production configurés (SECURE_BROWSER_XSS_FILTER, CONTENT_TYPE_NOSNIFF)
- [🟢] Secrets via env vars uniquement, jamais en dur (hors default dev explicite)
- [🟢] HSTS configuré en production
- [🟢] SESSION_COOKIE_SECURE + CSRF_COOKIE_SECURE en production
- [🟡] **`"0.0.0.0"` dans ALLOWED_HOSTS** `config/settings/development.py:15` `0.0.0.0` est une adresse de bind réseau, pas un hostname HTTP. Django valide le header `Host:` — aucun client n'envoie `Host: 0.0.0.0`. Inoffensif mais trompeur (supprimer)

### Backend specific

#### Logging

- [🟢] Logging configuré avec formatter verbose, root + loggers métier
- [🟢] Override DEBUG en development, override niveau log en production

## Final Review

- **Score**: 🟡 Mineur — 1 point score 2, 2 points score 1
- **Feedback**: L'implémentation est solide et suit les règles du projet. Le point principal est la migration de `STATICFILES_STORAGE` vers `STORAGES` qui évitera des warnings Django 5.x en production.
- **Follow-up Actions**:
  - Remplacer `STATICFILES_STORAGE` par `STORAGES` (base.py + development.py)
  - Supprimer `"0.0.0.0"` de `ALLOWED_HOSTS` développement
  - `CELERY_BEAT_SCHEDULE` à compléter lors de la tâche ActivityPub
- **Additional Notes**: `CELERY_BEAT_SCHEDULE` référençant des tâches futures est acceptable dans ce contexte de scaffolding — ne pas bloquer.
