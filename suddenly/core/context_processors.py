"""
Context processors for Suddenly templates.
"""

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from django.utils.translation import gettext_lazy as _

from suddenly.core.version import get_version


def site_settings(request: object) -> dict[str, object]:
    """Add site settings to template context.

    Tries to read live values from ``InstanceSettings`` so that the admin
    panel changes are reflected immediately.  Falls back to Django settings
    when the DB is not yet available (first boot / migration phase).
    """
    try:
        from suddenly.core.models import InstanceSettings  # local import avoids circular deps

        instance = InstanceSettings.get()
        site_name: object = instance.name or getattr(settings, "SITE_NAME", "Suddenly")
        site_description: object = instance.description or _("Federated shared fiction network")
    except (OperationalError, ProgrammingError, Exception):  # noqa: BLE001 — boot-safe fallback
        site_name = getattr(settings, "SITE_NAME", "Suddenly")
        site_description = getattr(settings, "SITE_DESCRIPTION", None) or _(
            "Federated shared fiction network"
        )

    return {
        "SITE_NAME": site_name,
        "SITE_DESCRIPTION": site_description,
        "DOMAIN": getattr(settings, "DOMAIN", "localhost"),
        "APP_VERSION": get_version(),
    }
