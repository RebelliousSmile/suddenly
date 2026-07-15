"""App config for the Muses client seam."""

from __future__ import annotations

from django.apps import AppConfig


class MusesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "suddenly.muses"
    verbose_name = "Muses"
