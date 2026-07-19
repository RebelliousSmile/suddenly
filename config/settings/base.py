"""
Shared settings for all environments.

Environment-specific overrides live in development.py and production.py.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SITE_NAME = "Suddenly"
SITE_DESCRIPTION = None  # Translated at runtime via context processor

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
    "suddenly.docs",
    "suddenly.muses",
    "suddenly.fediverse_auth",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "suddenly.core.middleware.InstanceLanguageMiddleware",
    "suddenly.core.middleware.UserLanguageMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "suddenly.core.middleware.AuthRateLimitMiddleware",
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
                "django.template.context_processors.i18n",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "suddenly.core.context_processors.site_settings",
                "suddenly.core.context_processors.account_badges",
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

ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_ADAPTER = "suddenly.users.adapters.SuddenlyAccountAdapter"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# =================================================================
# FEDIVERSE LOGIN ("Se connecter avec le Fediverse")
# =================================================================

# Master switch for the "Sign in with Mastodon" flow. When on, the login and
# signup pages show a "Se connecter avec le Fediverse" button. The flow works
# with any Mastodon-API-compatible server (Mastodon, Pleroma, Akkoma,
# GoToSocial, Pixelfed) — apps are registered per-instance on demand, so no
# admin credential setup is required. It does need a correct public AP_BASE_URL
# so the instance can redirect back to this server's callback.
FEDIVERSE_LOGIN_ENABLED = os.environ.get("FEDIVERSE_LOGIN_ENABLED", "1") == "1"
# Client name shown to users on the remote instance's consent screen.
FEDIVERSE_APP_NAME = os.environ.get("FEDIVERSE_APP_NAME", SITE_NAME)

# =================================================================
# INTERNATIONALIZATION
# =================================================================

LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", "fr")
LANGUAGES = [
    ("en", "English"),
    ("fr", "Français"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
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

CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
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
    "expire-stale-link-requests": {
        "task": "suddenly.activitypub.tasks.expire_stale_link_requests",
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

# Maximum allowed clock skew (seconds) between an incoming request's signed
# Date header and server time before the signature is rejected as a replay.
# 30s is too aggressive for real-world clock drift across federated peers;
# Mastodon uses a comparable window (SUD-F2).
AP_SIGNATURE_MAX_SKEW = int(os.environ.get("AP_SIGNATURE_MAX_SKEW", "300"))

# Whether plain-http actor fetches are permitted. https is mandatory by default;
# development overrides this to reach local http peers (SUD-F3).
AP_ALLOW_INSECURE_HTTP = os.environ.get("AP_ALLOW_INSECURE_HTTP", "0") == "1"

# =================================================================
# INGESTION
# =================================================================

# Shared secret for the choix-narratifs → Suddenly ingest endpoint.
# Set via environment variable; leave empty to disable the endpoint.
INGEST_TOKEN = os.environ.get("INGEST_TOKEN", "")

# =================================================================
# MUSES (AI hub)
# =================================================================

# Client seam to the suddenly-muses hub (#76). All Muses features degrade
# cleanly when the hub is disabled or unreachable (#88), so leaving this off
# is a fully supported deployment — features simply don't appear / no-op.
SUDDENLY_MUSES_ENABLED = os.environ.get("SUDDENLY_MUSES_ENABLED", "0") == "1"
# Base URL of the hub (production: https://muse.suddenly.social).
SUDDENLY_MUSES_URL = os.environ.get("SUDDENLY_MUSES_URL", "")
# Bearer token issued by the hub for this instance.
SUDDENLY_MUSES_API_KEY = os.environ.get("SUDDENLY_MUSES_API_KEY", "")
# Per-request timeout (seconds) for hub calls.
SUDDENLY_MUSES_TIMEOUT = float(os.environ.get("SUDDENLY_MUSES_TIMEOUT", "30"))

# =================================================================
# FEED
# =================================================================

# Interleave a claim/adopt/fork promocard every N reports in the connected
# (Abonnements) feed (SUD-P1). Matches the v3 wireframe default of 6. On a feed
# shorter than this, at least one promo is still guaranteed.
FEED_PROMO_EVERY = int(os.environ.get("FEED_PROMO_EVERY", "6"))

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
