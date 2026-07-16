"""
ActivityPub activity builders.

Functions to construct ActivityPub activity objects
following the spec: https://www.w3.org/TR/activitypub/
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils import timezone

from suddenly.activitypub.url_utils import absolute_media_url, media_type_for_file


def get_context() -> list[str]:
    """Return the standard ActivityPub context."""
    return [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
    ]


def build_actor(user_or_game_or_character: Any) -> dict[str, Any]:
    """
    Build an ActivityPub actor object.

    Works for User, Game, or Character models.
    """
    obj = user_or_game_or_character

    actor: dict[str, Any] = {
        "@context": get_context(),
        "id": obj.actor_url,
        "type": "Person",  # Could be customized per type
        "preferredUsername": getattr(obj, "username", None) or str(obj.pk),
        "inbox": f"{obj.actor_url}/inbox",
        "outbox": f"{obj.actor_url}/outbox",
        "followers": f"{obj.actor_url}/followers",
        "following": f"{obj.actor_url}/following",
    }

    # Name
    if hasattr(obj, "display_name") and obj.display_name:
        actor["name"] = obj.display_name
    elif hasattr(obj, "name"):
        actor["name"] = obj.name
    elif hasattr(obj, "title"):
        actor["name"] = obj.title

    # Summary/bio
    if hasattr(obj, "bio") and obj.bio:
        actor["summary"] = obj.bio
    elif hasattr(obj, "description") and obj.description:
        actor["summary"] = obj.description

    # Avatar/icon
    if hasattr(obj, "avatar") and obj.avatar:
        actor["icon"] = {
            "type": "Image",
            "mediaType": media_type_for_file(obj.avatar),
            "url": absolute_media_url(obj.avatar),
        }

    # Public key for HTTP signatures
    if hasattr(obj, "public_key") and obj.public_key:
        actor["publicKey"] = {
            "id": f"{obj.actor_url}#main-key",
            "owner": obj.actor_url,
            "publicKeyPem": obj.public_key,
        }

    return actor


def build_offer_activity(link_request: Any) -> dict[str, Any]:
    """
    Build an Offer activity for a link request.

    The Offer activity type is used for claim/adopt/fork requests.
    """
    activity: dict[str, Any] = {
        "@context": get_context(),
        "id": f"{settings.AP_BASE_URL}/activities/offer/{link_request.pk}",
        "type": "Offer",
        "actor": link_request.requester.actor_url,
        "published": link_request.created_at.isoformat(),
        "to": [link_request.target_character.creator.actor_url],
        "object": {
            "type": "Relationship",
            "relationship": link_request.type,
            "subject": link_request.requester.actor_url,
            "object": link_request.target_character.actor_url,
        },
        "summary": link_request.message,
    }

    # For claims, include the proposed PC
    if link_request.proposed_character:
        activity["object"]["subject"] = link_request.proposed_character.actor_url

    return activity


def build_accept_activity(link_request: Any) -> dict[str, Any]:
    """
    Build an Accept activity for an accepted link request.
    """
    return {
        "@context": get_context(),
        "id": f"{settings.AP_BASE_URL}/activities/accept/{link_request.pk}",
        "type": "Accept",
        "actor": link_request.target_character.creator.actor_url,
        "published": (
            link_request.resolved_at.isoformat()
            if link_request.resolved_at
            else timezone.now().isoformat()
        ),
        "to": [link_request.requester.actor_url],
        "object": f"{settings.AP_BASE_URL}/activities/offer/{link_request.pk}",
        "summary": link_request.response_message or None,
    }


def build_reject_activity(link_request: Any) -> dict[str, Any]:
    """
    Build a Reject activity for a rejected link request.
    """
    return {
        "@context": get_context(),
        "id": f"{settings.AP_BASE_URL}/activities/reject/{link_request.pk}",
        "type": "Reject",
        "actor": link_request.target_character.creator.actor_url,
        "published": (
            link_request.resolved_at.isoformat()
            if link_request.resolved_at
            else timezone.now().isoformat()
        ),
        "to": [link_request.requester.actor_url],
        "object": f"{settings.AP_BASE_URL}/activities/offer/{link_request.pk}",
        "summary": link_request.response_message or None,
    }


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
