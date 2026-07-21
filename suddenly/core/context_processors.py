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
        "FEDIVERSE_LOGIN_ENABLED": getattr(settings, "FEDIVERSE_LOGIN_ENABLED", False),
    }


def account_badges(request: object) -> dict[str, object]:
    """Inject account-menu badge counts (Front #5).

    The base template references ``pending_requests_count`` and
    ``unread_notifications_count`` but nothing populated them. Compute them here
    for authenticated users only (two cheap indexed counts); anonymous requests
    get an empty dict so the badges simply don't render.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    from suddenly.characters.models import LinkRequest, LinkRequestStatus
    from suddenly.core.models import Notification, UnlockedAchievement
    from suddenly.messaging.services import MessageService

    return {
        "pending_requests_count": LinkRequest.objects.filter(
            target_character__creator=user, status=LinkRequestStatus.PENDING
        ).count(),
        "unread_notifications_count": Notification.objects.filter(
            recipient=user, is_read=False
        ).count(),
        "unread_messages_count": MessageService.unread_count(user),
        # Newly unlocked achievements not yet seen on the Stats page (#153).
        "new_stats_count": UnlockedAchievement.objects.filter(
            user=user, seen_at__isnull=True
        ).count(),
    }
