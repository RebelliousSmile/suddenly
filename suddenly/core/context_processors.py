"""
Context processors for Suddenly templates.
"""

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from suddenly.core.version import get_version


def site_settings(request: object) -> dict[str, object]:
    """Add site settings to template context."""
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Suddenly"),
        "SITE_DESCRIPTION": getattr(settings, "SITE_DESCRIPTION", None)
        or _("Federated shared fiction network"),
        "DOMAIN": getattr(settings, "DOMAIN", "localhost"),
        "APP_VERSION": get_version(),
    }
