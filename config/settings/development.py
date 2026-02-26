"""
Development settings — permissive defaults, local services.

Never use in production.
"""

import os
from urllib.parse import urlparse

from .base import *  # noqa: F401, F403

DEBUG = True
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DOMAIN = os.environ.get("DOMAIN", "localhost:8000")
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Local PostgreSQL
_db_url = urlparse(
    os.environ.get("DATABASE_URL", "postgres://suddenly:suddenly@localhost:5432/suddenly")
)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _db_url.path[1:],
        "USER": _db_url.username,
        "PASSWORD": _db_url.password,
        "HOST": _db_url.hostname,
        "PORT": _db_url.port or 5432,
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 10},
    }
}

# Redis (optional — falls back to DB cache + sync tasks if not set)
REDIS_URL = os.environ.get("REDIS_URL", "")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache",
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True  # Run tasks synchronously
    CELERY_TASK_EAGER_PROPAGATES = True

# ActivityPub base URL
AP_BASE_URL = f"http://{DOMAIN}"

CSRF_TRUSTED_ORIGINS = [f"http://{DOMAIN}", "http://localhost:8000"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Development logging overrides
LOGGING["root"]["level"] = "DEBUG"  # type: ignore[index]
LOGGING["loggers"]["suddenly"]["level"] = "DEBUG"  # type: ignore[index]
