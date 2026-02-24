"""
Suddenly - Django Settings
"""

import os
from pathlib import Path
from urllib.parse import urlparse

# =================================================================
# BASE CONFIGURATION
# =================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load from environment
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
DOMAIN = os.environ.get("DOMAIN", "localhost")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", DOMAIN).split(",")

# Site info for ActivityPub
SITE_NAME = "Suddenly"
SITE_DESCRIPTION = "Réseau fédéré de fiction partagée"

# =================================================================
# APPLICATION DEFINITION
# =================================================================

INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "allauth",
    "allauth.account",
    # Suddenly apps
    "suddenly.core",
    "suddenly.users",
    "suddenly.games",
    "suddenly.characters",
    "suddenly.activitypub",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "suddenly.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Suddenly context
                "suddenly.core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "suddenly.wsgi.application"

# =================================================================
# DATABASE
# =================================================================

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgres://suddenly:suddenly@localhost:5432/suddenly"
)
db_url = urlparse(DATABASE_URL)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": db_url.path[1:],
        "USER": db_url.username,
        "PASSWORD": db_url.password,
        "HOST": db_url.hostname,
        "PORT": db_url.port or 5432,
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# =================================================================
# CACHE & CELERY
# =================================================================

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# Celery configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Celery Beat schedule (periodic tasks)
CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-quotes": {
        "task": "suddenly.activitypub.tasks.cleanup_expired_quotes",
        "schedule": 3600,  # Every hour
    },
    "refresh-remote-actors": {
        "task": "suddenly.activitypub.tasks.refresh_remote_actors",
        "schedule": 86400,  # Every 24 hours
    },
}

# =================================================================
# AUTHENTICATION
# =================================================================

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# django-allauth
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_VERIFICATION = "optional"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# =================================================================
# INTERNATIONALIZATION
# =================================================================

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =================================================================
# STATIC & MEDIA FILES
# =================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise for static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =================================================================
# SECURITY
# =================================================================

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [f"https://{DOMAIN}"]

# =================================================================
# REST FRAMEWORK
# =================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# =================================================================
# API DOCUMENTATION (drf-spectacular)
# =================================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "Suddenly API",
    "DESCRIPTION": """
## Suddenly — Federated Fiction Network API

Suddenly is a federated platform for sharing tabletop RPG session reports.
NPCs from one player's stories can become PCs in another's through claim, adopt, or fork mechanics.

### Core Concepts

- **Game**: An ongoing fiction that receives reports over time
- **Report**: A narrative account of a game session
- **Character**: A unified entity that can be NPC or PC, with evolving status
- **Quote**: A memorable character quote (public, private, or ephemeral)
- **Link**: A claim, adopt, or fork relationship between characters

### Authentication

Most read endpoints are public. Write operations require session authentication.
ActivityPub federation uses HTTP Signatures.

### ActivityPub

This instance federates via ActivityPub. Actors include:
- Users (`/users/{username}`)
- Games (`/games/{id}`)
- Characters (`/characters/{id}`)
    """,
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "games", "description": "Game (ongoing fiction) operations"},
        {"name": "reports", "description": "Session report operations"},
        {"name": "characters", "description": "Character (PC/NPC) operations"},
        {"name": "quotes", "description": "Character quote operations"},
        {"name": "links", "description": "Claim/Adopt/Fork link operations"},
        {"name": "users", "description": "User profile operations"},
        {"name": "activitypub", "description": "ActivityPub federation endpoints"},
    ],
    "EXTERNAL_DOCS": {
        "description": "Suddenly Documentation",
        "url": "https://docs.suddenly.social/",
    },
    "CONTACT": {
        "name": "Suddenly Team",
        "url": "https://suddenly.social/",
    },
    "LICENSE": {
        "name": "AGPL-3.0",
        "url": "https://www.gnu.org/licenses/agpl-3.0.html",
    },
}

# =================================================================
# ACTIVITYPUB
# =================================================================

# Base URL for ActivityPub identifiers
AP_BASE_URL = f"https://{DOMAIN}"

# HTTP signature key (generated on first run)
AP_PRIVATE_KEY_PATH = BASE_DIR / "keys" / "private.pem"
AP_PUBLIC_KEY_PATH = BASE_DIR / "keys" / "public.pem"

# Accepted Activity types
AP_ACCEPTED_ACTIVITIES = [
    "Create",
    "Update",
    "Delete",
    "Follow",
    "Accept",
    "Reject",
    "Undo",
    "Offer",
]

# =================================================================
# LOGGING
# =================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "suddenly": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# =================================================================
# MISC
# =================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Max upload size (10 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
