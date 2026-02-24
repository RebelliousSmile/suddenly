# Tâche 00 : Initialisation du Projet

**Durée estimée** : 30 min
**Phase** : 1 - Fondations
**Statut** : [ ] À faire

---

## Objectif

Créer la structure de base du projet Django avec l'environnement virtuel et les dépendances.

## Prérequis

- Python 3.12+ installé
- PostgreSQL 16+ installé et accessible
- Git installé

## Fichiers à Créer

```
suddenly/
├── .venv/                    # Environnement virtuel
├── .gitignore
├── .env.example
├── pyproject.toml            # Dépendances et config
├── manage.py
├── config/
│   └── __init__.py
├── apps/
│   └── __init__.py
├── templates/
│   └── .gitkeep
├── static/
│   └── .gitkeep
└── tests/
    ├── __init__.py
    └── conftest.py
```

## Étapes

### 1. Créer le répertoire et venv

```bash
cd C:\Users\fxgui\Documents\Projets\suddenly
python -m venv .venv
.venv\Scripts\activate
```

### 2. Créer pyproject.toml

```toml
[project]
name = "suddenly"
version = "0.1.0"
description = "Réseau fédéré de fiction partagée"
requires-python = ">=3.12"

dependencies = [
    "django>=5.0,<6.0",
    "psycopg[binary]>=3.1",
    "django-environ>=0.11",
    "django-allauth>=0.60",
    "django-htmx>=1.17",
    "markdown>=3.5",
    "bleach>=6.1",
    "pillow>=10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-django>=4.7",
    "mypy>=1.8",
    "django-stubs>=4.2",
    "ruff>=0.2",
    "black>=24.1",
]
federation = [
    "cryptography>=42.0",
    "httpx>=0.26",
    "celery>=5.3",
    "redis>=5.0",
]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["mypy_django_plugin.main"]

[tool.django-stubs]
django_settings_module = "config.settings.development"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.development"
python_files = ["test_*.py"]
```

### 3. Installer les dépendances

```bash
pip install -e ".[dev]"
```

### 4. Créer .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*.so
.venv/
venv/
*.egg-info/

# Django
*.log
local_settings.py
db.sqlite3
media/

# Environment
.env
.env.local

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Static files (generated)
staticfiles/

# Coverage
htmlcov/
.coverage
```

### 5. Créer .env.example

```bash
# Django
DEBUG=True
SECRET_KEY=change-me-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://suddenly:suddenly@localhost:5432/suddenly

# Domain (pour ActivityPub)
DOMAIN=localhost:8000
```

### 6. Créer la structure de répertoires

```bash
mkdir -p config/settings apps templates static tests/contracts
touch config/__init__.py
touch apps/__init__.py
touch tests/__init__.py
touch templates/.gitkeep
touch static/.gitkeep
```

### 7. Créer manage.py

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
```

### 8. Créer tests/conftest.py

```python
"""Fixtures partagées pour les tests pytest."""
import pytest


@pytest.fixture
def client():
    """Client de test Django."""
    from django.test import Client
    return Client()
```

### 9. Créer la base de données PostgreSQL

```bash
createdb suddenly
# ou via psql :
# CREATE DATABASE suddenly;
# CREATE USER suddenly WITH PASSWORD 'suddenly';
# GRANT ALL PRIVILEGES ON DATABASE suddenly TO suddenly;
```

### 10. Initialiser Git

```bash
git init
git add .
git commit -m "chore: initial project structure"
```

## Validation

- [ ] `.venv` créé et activé
- [ ] `pip list` montre Django 5.x installé
- [ ] Structure de répertoires conforme
- [ ] `.env.example` présent
- [ ] `git status` montre un repo propre après commit

## Références

- `documentation/ARCHITECTURE.md` — Structure projet cible
- `documentation/memory-bank/02-development-standards.md` — Standards
