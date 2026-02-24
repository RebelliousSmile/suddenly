# Tâche 01 : Configuration Django

**Durée estimée** : 1h
**Phase** : 1 - Fondations
**Statut** : [ ] À faire
**Dépend de** : 00-init-projet

---

## Objectif

Configurer Django avec des settings modulaires (base/development/production), les URLs de base et le wsgi.

## Prérequis

- Tâche 00 complétée
- Environnement virtuel activé

## Fichiers à Créer

```
config/
├── __init__.py
├── settings/
│   ├── __init__.py
│   ├── base.py           # Settings communs
│   └── development.py    # Settings dev
├── urls.py
├── wsgi.py
└── asgi.py
```

## Étapes

### 1. Créer config/settings/__init__.py

```python
"""Settings package."""
```

### 2. Créer config/settings/base.py

```python
"""
Django settings for Suddenly project.
Base settings shared by all environments.
"""
import os
from pathlib import Path

import environ

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)
environ.Env.read_env(BASE_DIR / '.env')

# Security
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# Domain for ActivityPub
DOMAIN = env('DOMAIN', default='localhost:8000')

# Application definition
INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.postgres',  # Pour FTS

    # Third-party
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django_htmx',

    # Local apps
    'apps.core',
    'apps.users',
    'apps.federation',
    'apps.games',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres:///suddenly')
}
DATABASES['default']['CONN_MAX_AGE'] = 600

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sites framework (required by allauth)
SITE_ID = 1

# Allauth configuration
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_VERIFICATION = 'optional'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
```

### 3. Créer config/settings/development.py

```python
"""
Development settings.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Debug toolbar (optional)
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
# INTERNAL_IPS = ['127.0.0.1']

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### 4. Créer config/urls.py

```python
"""
URL configuration for Suddenly project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication (allauth)
    path('accounts/', include('allauth.urls')),

    # Apps
    path('', include('apps.games.urls', namespace='games')),
    path('@', include('apps.users.urls', namespace='users')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### 5. Créer config/wsgi.py

```python
"""
WSGI config for Suddenly project.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

application = get_wsgi_application()
```

### 6. Créer config/asgi.py

```python
"""
ASGI config for Suddenly project.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

application = get_asgi_application()
```

### 7. Créer le fichier .env

```bash
cp .env.example .env
# Éditer .env avec une vraie SECRET_KEY :
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Validation

- [ ] `python manage.py check` passe (des erreurs d'apps manquantes sont normales)
- [ ] Les imports fonctionnent
- [ ] `.env` contient une vraie SECRET_KEY

## Notes

Les apps `core`, `users`, `federation`, `games` sont référencées mais pas encore créées. Django va signaler des erreurs — c'est normal à ce stade.

## Références

- `documentation/ARCHITECTURE.md` — Structure settings
- Django 5.x documentation — Settings
