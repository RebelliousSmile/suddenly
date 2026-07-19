"""
Celery tasks for ActivityPub federation.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
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
        raise self.retry(exc=e, countdown=2**self.request.retries * 60) from e


@shared_task  # type: ignore[untyped-decorator]
def broadcast_activity(activity: dict[str, Any], actor_id: str, actor_type: str) -> None:
    """Broadcast an activity to all followers."""
    from suddenly.characters.models import Follow
    from suddenly.core.utils import actor_model_for, content_type_for_actor

    from ._http import sign_and_deliver

    try:
        content_type = content_type_for_actor(actor_type)
        ActorModel = actor_model_for(actor_type)  # noqa: N806
    except ValueError:
        return

    followers = Follow.objects.filter(content_type=content_type, object_id=actor_id).select_related(
        "follower"
    )

    actor_obj = ActorModel._default_manager.filter(pk=actor_id).first()

    inboxes = {f.follower.inbox_url for f in followers if f.follower.inbox_url}

    for inbox_url in inboxes:
        sign_and_deliver(activity, inbox_url, signer=actor_obj)


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
    from urllib.parse import urlparse

    from suddenly.characters.models import LinkRequest

    from ._http import sign_and_deliver
    from .models import FederatedServer
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
    if not (creator and creator.remote and creator.inbox_url):
        return

    # Suddenly-only guard: Claim/Adopt/Fork Offers carry Suddenly-specific
    # AS2 extensions (suddenly:* namespace, DEC-038) a non-Suddenly instance
    # cannot interpret (08-activitypub.md "Never send Suddenly-only
    # activities to non-Suddenly instances"). Resolve the target inbox's
    # FederatedServer by domain (same lookup as inbox.py's rate limiter) and
    # skip only when it is a KNOWN non-Suddenly instance. An instance with
    # no FederatedServer row (never NodeInfo-probed) is NOT blocked here —
    # blocking on "unknown" would prevent first contact with any instance
    # entirely, since a FederatedServer row only exists after a prior
    # WebFinger/NodeInfo discovery.
    domain = urlparse(creator.inbox_url).netloc
    server = FederatedServer.objects.filter(server_name=domain).first()
    if server is not None and not server.is_suddenly_instance():
        logger.info("Skipping Offer delivery to non-Suddenly instance: %s", domain)
        return

    sign_and_deliver(activity, creator.inbox_url, signer=request.requester)


def _resolve_remote_follow_target(target_type: str, target_actor_url: str) -> Any:
    """Resolve a remote actor URL to its local mirror, dispatched by `target_type`.

    `target_type` defaults to ``"user"`` everywhere it is optional (DEC-C4,
    Epic C #133) so existing callers/tests that predate polymorphic Follow
    targets keep working unchanged. Returns `None` on any resolution failure
    — callers must degrade gracefully, never 500.
    """
    from .inbox import get_or_create_remote_character, get_or_create_remote_game

    key = target_type.lower()
    if key == "character":
        return get_or_create_remote_character(target_actor_url)
    if key == "game":
        return get_or_create_remote_game(target_actor_url)
    return get_or_create_remote_user(target_actor_url)


@shared_task  # type: ignore[untyped-decorator]
def send_follow_activity(
    user_id: str,
    target_actor_url: str,
    follow_ap_id: str | None = None,
    target_type: str = "user",
) -> None:
    """Send a Follow activity from a local user to a remote actor.

    Resolves the remote actor's inbox URL, builds a signed Follow activity,
    and delivers it via ``deliver_activity``. `target_type` ("user"/"character"
    /"game", DEC-C4) selects the resolver — a followed remote Character or Game
    actor mirrors the same delivery path as a followed remote User.
    """
    from suddenly.users.models import User

    from ._http import sign_and_deliver
    from .serializers import create_follow_activity

    user = User.objects.filter(pk=user_id).first()
    if not user or user.remote:
        return

    remote_target = _resolve_remote_follow_target(target_type, target_actor_url)
    if not remote_target or not remote_target.inbox_url:
        return

    activity = create_follow_activity(user, target_actor_url, follow_ap_id)
    sign_and_deliver(activity, remote_target.inbox_url, signer=user)


@shared_task  # type: ignore[untyped-decorator]
def send_undo_follow_activity(
    user_id: str, target_actor_url: str, target_type: str = "user"
) -> None:
    """Send an Undo(Follow) activity from a local user to a remote actor.

    Looks up the Follow record by follower+target to retrieve its ``ap_id``,
    builds a signed Undo(Follow) activity, delivers it, then deletes the
    local Follow record. `target_type` ("user"/"character"/"game", DEC-C4)
    selects the target model/resolver.
    """
    from suddenly.core.utils import actor_model_for, content_type_for_actor
    from suddenly.users.models import User

    from ._http import sign_and_deliver
    from .serializers import create_undo_follow_activity

    user = User.objects.filter(pk=user_id).first()
    if not user or user.remote:
        return

    try:
        target_model: Any = actor_model_for(target_type)
    except ValueError:
        return

    remote_target = target_model._default_manager.filter(
        ap_id=target_actor_url, remote=True
    ).first()
    if not remote_target or not remote_target.inbox_url:
        return

    content_type = content_type_for_actor(target_type)

    from suddenly.characters.models import Follow

    follow = Follow.objects.filter(
        follower=user,
        content_type=content_type,
        object_id=remote_target.pk,
    ).first()

    if not follow or not follow.ap_id:
        return

    activity = create_undo_follow_activity(user, follow.ap_id, target_actor_url)
    sign_and_deliver(activity, remote_target.inbox_url, signer=user)

    follow.delete()


def _send_link_response(
    link_request_id: str, build_activity: Callable[[Any, dict[str, Any] | str], dict[str, Any]]
) -> None:
    """Fetch the LinkRequest, build the response activity, sign and deliver it.

    Single source for the Accept/Reject link-response pair (audit rows 6, 26)
    — `send_accept_activity`/`send_reject_activity` differ only in which
    serializer builds the activity (`create_accept_activity` vs
    `create_reject_activity`). Preserves DEC-038 Part 1 exactly: for a request
    of remote origin, the response must reference the requester's ORIGINAL
    Offer id (a string) — not this instance's local PK, which the requester
    does not know. Locally-created requests keep the full serialized Offer
    object.
    """
    from suddenly.characters.models import LinkRequest

    from ._http import sign_and_deliver
    from .serializers import serialize_link_request

    request = (
        LinkRequest.objects.filter(id=link_request_id)
        .select_related("requester", "target_character", "target_character__creator")
        .first()
    )

    if not request:
        return

    offer: dict[str, Any] | str = request.origin_offer_id or serialize_link_request(request)
    creator = request.target_character.creator
    activity = build_activity(creator, offer)

    # Send to requester
    if request.requester.remote and request.requester.inbox_url:
        sign_and_deliver(activity, request.requester.inbox_url, signer=creator)


@shared_task  # type: ignore[untyped-decorator]
def send_accept_activity(link_request_id: str) -> None:
    """Send Accept activity for an accepted link request."""
    from .serializers import create_accept_activity

    _send_link_response(link_request_id, create_accept_activity)


@shared_task  # type: ignore[untyped-decorator]
def send_reject_activity(link_request_id: str) -> None:
    """Send Reject activity for a rejected link request."""
    from .serializers import create_reject_activity

    _send_link_response(link_request_id, create_reject_activity)


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


def _like_activity_id(domain: str, username: str, report_pk: Any) -> str:
    """Deterministic AP ``id`` for a user's Like of a report (#138).

    Stable by construction so ``Undo(Like)`` can reference the exact same ``id``
    the receiver saw on the original ``Like`` — the risk-register requirement
    against uncorrelated Like/Undo pairs on the remote side.
    """
    return f"https://{domain}/users/{username}/like/{report_pk}"


@shared_task  # type: ignore[untyped-decorator]
def send_like_activity(user_id: str, report_id: str) -> None:
    """Send a directed AP ``Like`` to a remote scene's actor. #138 part 2.

    Directed to the remote author's inbox (not a followers broadcast like
    ``Announce``): a Like is a private engagement signal to the object's owner.
    No-op on a local scene — local likes stay local.
    """
    from django.conf import settings as django_settings

    from suddenly.games.models import Report
    from suddenly.users.models import User

    from ._http import sign_and_deliver

    user = User.objects.filter(pk=user_id).first()
    report = Report.objects.filter(pk=report_id).select_related("author").first()
    if not user or not report or not report.remote or not report.ap_id:
        return

    domain = django_settings.DOMAIN
    activity: dict[str, Any] = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Like",
        "id": _like_activity_id(domain, user.username, report.pk),
        "actor": user.actor_url,
        "object": report.ap_id,
        "published": timezone.now().isoformat(),
    }

    sign_and_deliver(activity, report.author.actor_inbox, signer=user)


@shared_task  # type: ignore[untyped-decorator]
def send_undo_like_activity(user_id: str, report_id: str) -> None:
    """Send a directed AP ``Undo(Like)`` to a remote scene's actor. #138 part 2.

    Wraps the same ``Like`` object (identical ``id``) inside an ``Undo`` so the
    remote side correlates it with the original Like. No-op on a local scene.
    """
    from django.conf import settings as django_settings

    from suddenly.games.models import Report
    from suddenly.users.models import User

    from ._http import sign_and_deliver

    user = User.objects.filter(pk=user_id).first()
    report = Report.objects.filter(pk=report_id).select_related("author").first()
    if not user or not report or not report.remote or not report.ap_id:
        return

    domain = django_settings.DOMAIN
    like_id = _like_activity_id(domain, user.username, report.pk)
    activity: dict[str, Any] = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Undo",
        "id": f"{like_id}/undo",
        "actor": user.actor_url,
        "object": {
            "type": "Like",
            "id": like_id,
            "actor": user.actor_url,
            "object": report.ap_id,
        },
        "published": timezone.now().isoformat(),
    }

    sign_and_deliver(activity, report.author.actor_inbox, signer=user)


@shared_task  # type: ignore[untyped-decorator]
def cleanup_expired_quotes() -> None:
    """Delete expired ephemeral quotes."""
    from suddenly.characters.models import Quote, QuoteVisibility

    Quote.objects.filter(
        visibility=QuoteVisibility.EPHEMERAL, expires_at__lt=timezone.now()
    ).delete()


@shared_task  # type: ignore[untyped-decorator]
def expire_stale_link_requests() -> None:
    """
    Expire stale cross-instance PENDING link requests (idempotent, daily).

    Thin wrapper: the state transition, the cross-instance predicate, and
    the requester notification all live in
    ``LinkService.expire_stale_requests`` (08-characters.md: all link
    state changes go through ``LinkService``, never inline in a task).
    Scheduled in ``CELERY_BEAT_SCHEDULE``.
    """
    from suddenly.characters.services import LinkService

    LinkService.expire_stale_requests()


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
    """Get or create a remote user.

    Thin wrapper over the canonical `_http.get_or_create_remote_user` (audit
    row 4) — unwraps its `(user, created)` tuple to a plain object/`None`
    return, since callers here (and existing tests, which patch this exact
    module attribute with `return_value=<bare User instance>`) expect that
    contract rather than the tuple.
    """
    from ._http import get_or_create_remote_user as _get_or_create_remote_user

    result = _get_or_create_remote_user(actor_url)
    if result is None:
        return None
    user, _created = result
    return user


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
