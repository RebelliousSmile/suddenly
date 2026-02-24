"""
Context processors for Suddenly templates.
"""

from django.conf import settings


def site_settings(request):
    """Add site settings to template context."""
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Suddenly"),
        "SITE_DESCRIPTION": getattr(
            settings, "SITE_DESCRIPTION", "Réseau fédéré de fiction partagée"
        ),
        "DOMAIN": getattr(settings, "DOMAIN", "localhost"),
    }
