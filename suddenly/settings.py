"""
DEPRECATED — This settings file has been replaced.

Use:
  - config.settings.development  (local dev, manage.py, celery)
  - config.settings.production   (wsgi, production deployments)

Set DJANGO_SETTINGS_MODULE accordingly.
"""

raise ImportError(
    "suddenly.settings is deprecated. "
    "Use config.settings.development or config.settings.production instead."
)
