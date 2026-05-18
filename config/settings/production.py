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

# Railway provides RAILWAY_PUBLIC_DOMAIN for the auto-generated hostname
_railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
if _railway_domain and _railway_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_domain)

# Allow internal healthcheck probes (Railway probes localhost:PORT internally)
for _internal_host in ("127.0.0.1", "localhost"):
    if _internal_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_internal_host)

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

# Redis — optional, falls back to DB cache + sync Celery
REDIS_URL = os.environ.get("REDIS_URL")
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
    CELERY_TASK_ALWAYS_EAGER = True  # Run tasks synchronously without broker

# ActivityPub base URL
AP_BASE_URL = f"https://{DOMAIN}"

# Email — SMTP if configured, silent dummy otherwise (verification is optional)
_email_host = os.environ.get("EMAIL_HOST")
if _email_host:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = _email_host
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", f"no-reply@{DOMAIN}")
else:
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

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
if _railway_domain:
    CSRF_TRUSTED_ORIGINS.append(f"https://{_railway_domain}")

# Production logging override
LOGGING["loggers"]["django"]["level"] = os.environ.get(  # type: ignore[index]  # noqa: F405
    "DJANGO_LOG_LEVEL", "INFO"
)
