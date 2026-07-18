"""
ActivityPub activity builders.

Functions to construct ActivityPub activity objects
following the spec: https://www.w3.org/TR/activitypub/
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils import timezone


def get_context() -> list[str]:
    """Return the standard ActivityPub context."""
    return [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
    ]


def build_follow_activity(follower: Any, target_actor_url: str) -> dict[str, Any]:
    """
    Build a Follow activity.
    """
    return {
        "@context": get_context(),
        "id": (
            f"{settings.AP_BASE_URL}/activities/follow/{follower.pk}/{timezone.now().timestamp()}"
        ),
        "type": "Follow",
        "actor": follower.actor_url,
        "object": target_actor_url,
        "published": timezone.now().isoformat(),
    }


def build_undo_activity(original_activity_id: str, actor_url: str) -> dict[str, Any]:
    """
    Build an Undo activity (e.g., for unfollowing).
    """
    return {
        "@context": get_context(),
        "id": f"{settings.AP_BASE_URL}/activities/undo/{timezone.now().timestamp()}",
        "type": "Undo",
        "actor": actor_url,
        "object": original_activity_id,
        "published": timezone.now().isoformat(),
    }
