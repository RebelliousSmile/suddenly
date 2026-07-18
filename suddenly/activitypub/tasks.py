"""
Celery tasks for ActivityPub federation.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# =================================================================
# Outgoing activities
# =================================================================


@shared_task(  # type: ignore[untyped-decorator]
    bind=True,
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=120,
    time_limit=150,
)
def deliver_activity(
    self: Any,
    activity: dict[str, Any],
    inbox_url: str,
    actor_key_id: str | None = None,
    private_key_pem: str | None = None,
    **kwargs: Any,
) -> None:
    """Deliver a signed activity to a remote inbox.

    Signs outgoing requests with HTTP Signatures (DEC-018).
    Falls back to unsigned if no key provided (dev mode).
    """
    import json as json_module

    import httpx

    from .signatures import sign_request

    try:
        headers = {
            # POST-to-inbox requires the profiled ld+json content type (08-activitypub);
            # Content-Type is not among the signed headers, so this is signature-safe.
            "Content-Type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            "Accept": "application/activity+json",
        }

        # Sign request (pass dict — sign_request calls json.dumps internally)
        if actor_key_id and private_key_pem:
            headers = sign_request(
                method="POST",
                url=inbox_url,
                headers=headers,
                body=activity,
                key_id=actor_key_id,
                private_key_pem=private_key_pem,
            )

        body = json_module.dumps(activity).encode()

        with httpx.Client(timeout=30) as client:
            response = client.post(inbox_url, content=body, headers=headers)

        if response.status_code == 410:
            # Gone: actor/inbox permanently removed. Log and stop retrying.
            # Proper unfederate (actor removal) is handled by a separate task.
            logger.warning("AP delivery 410 Gone: %s", inbox_url)
            return

        if 400 <= response.status_code < 500:
            # Permanent client error: retrying will not help.
            logger.warning(
                "AP permanent delivery failure %s -> %s", inbox_url, response.status_code
            )
            return

        if response.status_code >= 500:
            # Transient server error: retry with exponential backoff.
            raise self.retry(countdown=2**self.request.retries * 60)

    except httpx.RequestError as e:
        raise self.retry(exc=e, countdown=2**self.request.retries * 60)


@shared_task  # type: ignore[untyped-decorator]
def broadcast_activity(activity: dict[str, Any], actor_id: str, actor_type: str) -> None:
    """Broadcast an activity to all followers."""
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Follow

    model_map: dict[str, tuple[str, str]] = {
        "User": ("users", "user"),
        "Game": ("games", "game"),
        "Character": ("characters", "character"),
    }

    result = model_map.get(actor_type)
    if not result:
        return

    app_label, model_name = result

    content_type = ContentType.objects.get(app_label=app_label, model=model_name)

    followers = Follow.objects.filter(content_type=content_type, object_id=actor_id).select_related(
        "follower"
    )

    # Get actor's signing key
    from suddenly.characters.models import Character
    from suddenly.games.models import Game
    from suddenly.users.models import User

    actor_models: dict[str, Any] = {"User": User, "Game": Game, "Character": Character}
    ActorModel = actor_models.get(actor_type)  # noqa: N806
    actor_obj = ActorModel.objects.filter(pk=actor_id).first() if ActorModel else None
    key_id, private_key = get_actor_signing_keys(actor_obj) if actor_obj else (None, None)

    inboxes = {f.follower.inbox_url for f in followers if f.follower.inbox_url}

    for inbox_url in inboxes:
        deliver_activity.delay(
            activity, inbox_url, actor_key_id=key_id, private_key_pem=private_key
        )


@shared_task  # type: ignore[untyped-decorator]
def send_accept_follow(target_id: str, target_type: str, follow_activity: dict[str, Any]) -> None:
    """Send Accept for a follow request."""
    from suddenly.characters.models import Character
    from suddenly.games.models import Game
    from suddenly.users.models import User

    from .serializers import create_accept_activity

    models_map: dict[str, Any] = {
        "User": User,
        "Game": Game,
        "Character": Character,
    }
    Model = models_map.get(target_type)  # noqa: N806
    if not Model:
        return

    target = Model.objects.filter(id=target_id).first()
    if not target:
        return

    accept = create_accept_activity(target, follow_activity)

    actor_url = follow_activity.get("actor")
    remote_user = User.objects.filter(ap_id=actor_url).first()
    if remote_user and remote_user.inbox_url:
        key_id, private_key = get_actor_signing_keys(target)
        deliver_activity.delay(
            accept,
            remote_user.inbox_url,
            actor_key_id=key_id,
            private_key_pem=private_key,
        )


@shared_task  # type: ignore[untyped-decorator]
def send_create_activity(object_type: str, object_id: str) -> None:
    """
    Send a Create activity for new content.

    Args:
        object_type: 'report', 'character', or 'quote'
        object_id: UUID of the object
    """
    from django.db import models as db_models

    from suddenly.characters.models import Character, Quote
    from suddenly.games.models import Report

    from .serializers import (
        create_create_activity,
        serialize_character,
        serialize_quote,
        serialize_report,
    )

    serialized: dict[str, Any]
    actor: db_models.Model
    actor_type: str

    if object_type == "report":
        report = Report.objects.filter(id=object_id).select_related("author", "game").first()
        if not report or report.remote:
            return
        serialized = serialize_report(report)
        actor = report.game  # Game is the actor for reports
        actor_type = "Game"

    elif object_type == "character":
        character = Character.objects.filter(id=object_id).select_related("origin_game").first()
        if not character or character.remote:
            return
        serialized = serialize_character(character)
        actor = character.origin_game
        actor_type = "Game"

    elif object_type == "quote":
        quote = Quote.objects.filter(id=object_id).select_related("character").first()
        if not quote or quote.remote:
            return
        serialized = serialize_quote(quote)
        actor = quote.character
        actor_type = "Character"

    else:
        return

    activity = create_create_activity(actor, serialized)
    broadcast_activity.delay(activity, str(actor.pk), actor_type)


@shared_task  # type: ignore[untyped-decorator]
def send_offer_activity(link_request_id: str) -> None:
    """Send Offer activity for a link request."""
    from suddenly.characters.models import LinkRequest

    from .serializers import serialize_link_request

    request = (
        LinkRequest.objects.filter(id=link_request_id)
        .select_related("requester", "target_character", "target_character__creator")
        .first()
    )

    if not request:
        return

    activity = serialize_link_request(request)

    # Send to target character's creator
    creator = request.target_character.creator
    if creator and creator.remote and creator.inbox_url:
        key_id, private_key = get_actor_signing_keys(request.requester)
        deliver_activity.delay(
            activity,
            creator.inbox_url,
            actor_key_id=key_id,
            private_key_pem=private_key,
        )


@shared_task  # type: ignore[untyped-decorator]
def send_follow_activity(
    user_id: str, target_actor_url: str, follow_ap_id: str | None = None
) -> None:
    """Send a Follow activity from a local user to a remote actor.

    Resolves the remote actor's inbox URL, builds a signed Follow activity,
    and delivers it via ``deliver_activity``.
    """
    from suddenly.users.models import User

    from .serializers import create_follow_activity

    user = User.objects.filter(pk=user_id).first()
    if not user or user.remote:
        return

    remote_user = get_or_create_remote_user(target_actor_url)
    if not remote_user or not remote_user.inbox_url:
        return

    activity = create_follow_activity(user, target_actor_url, follow_ap_id)
    key_id, private_key = get_actor_signing_keys(user)

    deliver_activity.delay(
        activity=activity,
        inbox_url=remote_user.inbox_url,
        actor_key_id=key_id,
        private_key_pem=private_key,
    )


@shared_task  # type: ignore[untyped-decorator]
def send_undo_follow_activity(user_id: str, target_actor_url: str) -> None:
    """Send an Undo(Follow) activity from a local user to a remote actor.

    Looks up the Follow record by follower+target to retrieve its ``ap_id``,
    builds a signed Undo(Follow) activity, delivers it, then deletes the
    local Follow record.
    """
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Follow
    from suddenly.users.models import User

    from .serializers import create_undo_follow_activity

    user = User.objects.filter(pk=user_id).first()
    if not user or user.remote:
        return

    remote_user = User.objects.filter(ap_id=target_actor_url, remote=True).first()
    if not remote_user or not remote_user.inbox_url:
        return

    content_type = ContentType.objects.get_for_model(User)
    follow = Follow.objects.filter(
        follower=user,
        content_type=content_type,
        object_id=remote_user.pk,
    ).first()

    if not follow or not follow.ap_id:
        return

    activity = create_undo_follow_activity(user, follow.ap_id, target_actor_url)
    key_id, private_key = get_actor_signing_keys(user)

    deliver_activity.delay(
        activity=activity,
        inbox_url=remote_user.inbox_url,
        actor_key_id=key_id,
        private_key_pem=private_key,
    )

    follow.delete()


@shared_task  # type: ignore[untyped-decorator]
def send_accept_activity(link_request_id: str) -> None:
    """Send Accept activity for an accepted link request."""
    from suddenly.characters.models import LinkRequest

    from .serializers import create_accept_activity, serialize_link_request

    request = (
        LinkRequest.objects.filter(id=link_request_id)
        .select_related("requester", "target_character", "target_character__creator")
        .first()
    )

    if not request:
        return

    # DEC-038 Part 1: for a request of remote origin, the Accept must reference
    # the requester's ORIGINAL Offer id (a string) — not this instance's local
    # PK, which the requester does not know. Locally-created requests keep the
    # full serialized Offer object.
    offer: dict[str, Any] | str = request.origin_offer_id or serialize_link_request(request)
    creator = request.target_character.creator
    accept = create_accept_activity(creator, offer)

    # Send to requester
    if request.requester.remote and request.requester.inbox_url:
        key_id, private_key = get_actor_signing_keys(creator)
        deliver_activity.delay(
            accept,
            request.requester.inbox_url,
            actor_key_id=key_id,
            private_key_pem=private_key,
        )


@shared_task  # type: ignore[untyped-decorator]
def send_reject_activity(link_request_id: str) -> None:
    """Send Reject activity for a rejected link request."""
    from suddenly.characters.models import LinkRequest

    from .serializers import create_reject_activity, serialize_link_request

    request = (
        LinkRequest.objects.filter(id=link_request_id)
        .select_related("requester", "target_character", "target_character__creator")
        .first()
    )

    if not request:
        return

    # DEC-038 Part 1: mirror send_accept_activity — reference the requester's
    # original Offer id for remote-origin requests.
    offer: dict[str, Any] | str = request.origin_offer_id or serialize_link_request(request)
    creator = request.target_character.creator
    reject = create_reject_activity(creator, offer)

    # Send to requester
    if request.requester.remote and request.requester.inbox_url:
        key_id, private_key = get_actor_signing_keys(creator)
        deliver_activity.delay(
            reject,
            request.requester.inbox_url,
            actor_key_id=key_id,
            private_key_pem=private_key,
        )


# =================================================================
# Periodic tasks
# =================================================================


@shared_task  # type: ignore[untyped-decorator]
def send_announce_activity(user_id: str, report_id: str) -> None:
    """Send Announce (recommendation/boost) for a report. US-28."""
    from django.conf import settings as django_settings

    from suddenly.games.models import Report
    from suddenly.users.models import User

    user = User.objects.filter(pk=user_id).first()
    report = Report.objects.filter(pk=report_id).first()
    if not user or not report:
        return

    domain = django_settings.DOMAIN
    report_url = report.ap_id or f"https://{domain}/reports/{report.pk}"

    activity: dict[str, Any] = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Announce",
        "id": f"https://{domain}/users/{user.username}/announce/{report.pk}",
        "actor": user.actor_url,
        "object": report_url,
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [f"{user.actor_url}/followers"],
        "published": timezone.now().isoformat(),
    }

    broadcast_activity.delay(activity, str(user.pk), "User")


@shared_task  # type: ignore[untyped-decorator]
def cleanup_expired_quotes() -> None:
    """Delete expired ephemeral quotes."""
    from suddenly.characters.models import Quote, QuoteVisibility

    Quote.objects.filter(
        visibility=QuoteVisibility.EPHEMERAL, expires_at__lt=timezone.now()
    ).delete()


@shared_task  # type: ignore[untyped-decorator]
def refresh_remote_actors() -> None:
    """Refresh stale remote actors."""
    from suddenly.users.models import User

    stale = User.objects.filter(remote=True, updated_at__lt=timezone.now() - timedelta(hours=24))[
        :100
    ]

    for user in stale:
        fetch_remote_actor.delay(user.ap_id)


@shared_task  # type: ignore[untyped-decorator]
def fetch_remote_actor(actor_url: str) -> None:
    """Fetch and update a remote actor."""
    from ._http import fetch_ap_actor

    actor_data = fetch_ap_actor(actor_url, timeout=30)
    if actor_data is not None:
        update_remote_user(actor_url, actor_data)


# =================================================================
# Helpers
# =================================================================


def get_actor_signing_keys(actor: Any) -> tuple[str | None, str | None]:
    """Return (actor_key_id, private_key_pem) for a local actor, or (None, None).

    The returned key_id follows the convention ``<actor_url>#main-key``.
    Returns (None, None) for remote actors or actors without a private key.
    """
    actor_url = getattr(actor, "actor_url", None)
    private_key_pem: str | None = getattr(actor, "private_key", None) or None
    actor_key_id: str | None = f"{actor_url}#main-key" if actor_url else None
    return actor_key_id, private_key_pem


def get_or_create_remote_user(actor_url: str | None) -> Any:
    """Get or create a remote user."""
    from suddenly.users.models import User

    from ._http import fetch_ap_actor

    if not actor_url:
        return None

    user = User.objects.filter(ap_id=actor_url).first()
    if user:
        return user

    data = fetch_ap_actor(actor_url)
    if data is None:
        return None

    try:
        from urllib.parse import urlparse

        domain = urlparse(actor_url).netloc
        username = data.get("preferredUsername", "unknown")

        return User.objects.create(
            username=f"{username}@{domain}"[:150],
            remote=True,
            ap_id=actor_url,
            inbox_url=data.get("inbox"),
            outbox_url=data.get("outbox"),
            display_name=data.get("name", username)[:100],
            bio=data.get("summary", ""),
            public_key=data.get("publicKey", {}).get("publicKeyPem", ""),
        )
    except Exception as e:
        logger.exception(f"Error creating remote user: {e}")
        return None


def update_remote_user(actor_url: str, data: dict[str, Any]) -> None:
    """Update remote user from AP data."""
    from suddenly.users.models import User

    User.objects.filter(ap_id=actor_url).update(
        inbox_url=data.get("inbox"),
        outbox_url=data.get("outbox"),
        display_name=data.get("name", "")[:100],
        bio=data.get("summary", ""),
        public_key=data.get("publicKey", {}).get("publicKeyPem", ""),
        updated_at=timezone.now(),
    )
