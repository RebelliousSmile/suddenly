"""
Production settings — strict, env-required, security-hardened.

All secrets must be provided via environment variables.
Missing required variables raise KeyError at startup (fail fast).
"""

import os
from urllib.parse import urlparse

from .base import *  # noqa: F401, F403

DEBUG = False

# Fail fast if required secrets are absent
SECRET_KEY = os.environ["SECRET_KEY"]
DOMAIN = os.environ["DOMAIN"]
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", DOMAIN).split(",")

# Production database (required)
_db_url = urlparse(os.environ["DATABASE_URL"])
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _db_url.path[1:],
        "USER": _db_url.username,
        "PASSWORD": _db_url.password,
        "HOST": _db_url.hostname,
        "PORT": _db_url.port or 5432,
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 10},
    }
}

# Production Redis (required)
REDIS_URL = os.environ["REDIS_URL"]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# ActivityPub base URL
AP_BASE_URL = f"https://{DOMAIN}"

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [f"https://{DOMAIN}"]

# Production logging override
LOGGING["loggers"]["django"]["level"] = os.environ.get("DJANGO_LOG_LEVEL", "INFO")  # type: ignore[index]
