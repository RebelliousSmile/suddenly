"""
Shared settings for all environments.

Environment-specific overrides live in development.py and production.py.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SITE_NAME = "Suddenly"
SITE_DESCRIPTION = "Réseau fédéré de fiction partagée"

# =================================================================
# APPLICATION DEFINITION
# =================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_htmx",
    "suddenly.core",
    "suddenly.users",
    "suddenly.games",
    "suddenly.characters",
    "suddenly.activitypub",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
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
                "suddenly.core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "suddenly.wsgi.application"

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
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =================================================================
# CELERY
# =================================================================

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-quotes": {
        "task": "suddenly.activitypub.tasks.cleanup_expired_quotes",
        "schedule": 3600,
    },
    "refresh-remote-actors": {
        "task": "suddenly.activitypub.tasks.refresh_remote_actors",
        "schedule": 86400,
    },
}

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
# API DOCUMENTATION
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

AP_PRIVATE_KEY_PATH = BASE_DIR / "keys" / "private.pem"
AP_PUBLIC_KEY_PATH = BASE_DIR / "keys" / "public.pem"

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
# MISC
# =================================================================

SITE_ID = 1

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# =================================================================
# LOGGING
# =================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "suddenly": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
