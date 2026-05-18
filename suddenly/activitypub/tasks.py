"""
Celery tasks for ActivityPub federation.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Protocol

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# =================================================================
# Incoming activities processing
# =================================================================


@shared_task(bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def process_incoming_activity(
    self: Any,
    user_id: str | None,
    activity: dict[str, Any],
    game_id: str | None = None,
    character_id: str | None = None,
) -> None:
    """
    Process an incoming ActivityPub activity.
    """
    try:
        activity_type = activity.get("type")

        handlers: dict[str, _ActivityHandler] = {
            "Follow": handle_follow,
            "Undo": handle_undo,
            "Create": handle_create,
            "Update": handle_update,
            "Delete": handle_delete,
            "Accept": handle_accept,
            "Reject": handle_reject,
            "Offer": handle_offer,
        }

        handler = handlers.get(activity_type)  # type: ignore[arg-type]
        if handler:
            handler(activity, user_id, game_id, character_id)
        else:
            logger.warning(f"Unknown activity type: {activity_type}")

    except Exception as e:
        logger.exception(f"Error processing activity: {e}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


class _ActivityHandler(Protocol):
    def __call__(
        self,
        activity: dict[str, Any],
        user_id: str | None,
        game_id: str | None,
        character_id: str | None,
    ) -> None: ...


def handle_follow(
    activity: dict[str, Any],
    user_id: str | None,
    game_id: str | None,
    character_id: str | None,
) -> None:
    """Handle incoming Follow activity."""
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Character, Follow
    from suddenly.games.models import Game
    from suddenly.users.models import User

    actor_url = activity.get("actor")
    follower = get_or_create_remote_user(actor_url)
    if not follower:
        return

    target_obj: User | Game | Character | None = None
    content_type: ContentType | None = None

    if user_id:
        target_obj = User.objects.filter(id=user_id).first()
        content_type = ContentType.objects.get_for_model(User)
    elif game_id:
        target_obj = Game.objects.filter(id=game_id).first()
        content_type = ContentType.objects.get_for_model(Game)
    elif character_id:
        target_obj = Character.objects.filter(id=character_id).first()
        content_type = ContentType.objects.get_for_model(Character)

    if not target_obj:
        return

    Follow.objects.get_or_create(
        follower=follower,
        content_type=content_type,
        object_id=target_obj.id,
        defaults={"remote": True, "ap_id": activity.get("id")},
    )

    send_accept_follow.delay(str(target_obj.id), type(target_obj).__name__, activity)


def handle_undo(
    activity: dict[str, Any],
    user_id: str | None,
    game_id: str | None,
    character_id: str | None,
) -> None:
    """Handle Undo activity."""
    obj = activity.get("object", {})
    if obj.get("type") == "Follow":
        from suddenly.characters.models import Follow

        Follow.objects.filter(ap_id=obj.get("id")).delete()


def handle_create(
    activity: dict[str, Any],
    user_id: str | None,
    game_id: str | None,
    character_id: str | None,
) -> None:
    logger.info(f"Received Create: {activity.get('object', {}).get('type')}")


def handle_update(
    activity: dict[str, Any],
    user_id: str | None,
    game_id: str | None,
    character_id: str | None,
) -> None:
    logger.info("Received Update")


def handle_delete(
    activity: dict[str, Any],
    user_id: str | None,
    game_id: str | None,
    character_id: str | None,
) -> None:
    logger.info("Received Delete")


def handle_accept(
    activity: dict[str, Any],
    user_id: str | None,
    game_id: str | None,
    character_id: str | None,
) -> None:
    logger.info("Received Accept")


def handle_reject(
    activity: dict[str, Any],
    user_id: str | None,
    game_id: str | None,
    character_id: str | None,
) -> None:
    logger.info("Received Reject")


def handle_offer(
    activity: dict[str, Any],
    user_id: str | None,
    game_id: str | None,
    character_id: str | None,
) -> None:
    """Handle Offer (link requests from remote)."""
    logger.info("Received Offer")


# =================================================================
# Outgoing activities
# =================================================================


@shared_task(bind=True, max_retries=3)  # type: ignore[untyped-decorator]
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
            "Content-Type": "application/activity+json",
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

        if response.status_code >= 500:
            raise self.retry(countdown=60 * (self.request.retries + 1))

    except httpx.RequestError as e:
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


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
        deliver_activity.delay(accept, remote_user.inbox_url)


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
        deliver_activity.delay(activity, creator.inbox_url)


@shared_task  # type: ignore[untyped-decorator]
def send_follow_activity(user_id: str, target_actor_url: str) -> None:
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

    activity = create_follow_activity(user, target_actor_url)
    key_id, private_key = get_actor_signing_keys(user)

    deliver_activity.delay(
        activity=activity,
        inbox_url=remote_user.inbox_url,
        actor_key_id=key_id,
        private_key_pem=private_key,
    )


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

    offer = serialize_link_request(request)
    creator = request.target_character.creator
    accept = create_accept_activity(creator, offer)

    # Send to requester
    if request.requester.remote and request.requester.inbox_url:
        deliver_activity.delay(accept, request.requester.inbox_url)


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

    offer = serialize_link_request(request)
    creator = request.target_character.creator
    reject = create_reject_activity(creator, offer)

    # Send to requester
    if request.requester.remote and request.requester.inbox_url:
        deliver_activity.delay(reject, request.requester.inbox_url)


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
    import httpx

    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(actor_url, headers={"Accept": "application/activity+json"})

        if response.status_code == 200:
            update_remote_user(actor_url, response.json())
    except Exception as e:
        logger.exception(f"Error fetching {actor_url}: {e}")


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
    import httpx

    from suddenly.users.models import User

    if not actor_url:
        return None

    user = User.objects.filter(ap_id=actor_url).first()
    if user:
        return user

    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(actor_url, headers={"Accept": "application/activity+json"})

        if response.status_code != 200:
            return None

        data = response.json()

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
