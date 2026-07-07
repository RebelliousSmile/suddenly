"""
ActivityPub inbox views for receiving federated activities.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol
from urllib.parse import urlparse

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_ratelimit.core import is_ratelimited

from .models import FederatedServer
from .signatures import verify_signature

logger = logging.getLogger(__name__)

# Rate limits per minute
_KNOWN_INSTANCE_RATE = "100/m"
_UNKNOWN_INSTANCE_RATE = "10/m"


def _get_request_domain(request: HttpRequest) -> str:
    """Extract the remote instance domain from the Signature keyId."""
    sig = request.headers.get("Signature", "")
    for part in sig.split(","):
        key, _, value = part.partition("=")
        if key.strip() == "keyId":
            return urlparse(value.strip('"')).netloc
    return "unknown"


def _check_rate_limit(request: HttpRequest) -> bool:
    """
    Check per-instance rate limit. Returns True if rate limit exceeded.

    Known instances (in FederatedServer): 100 req/min.
    Unknown instances: 10 req/min.
    """
    domain = _get_request_domain(request)
    is_known = FederatedServer.objects.filter(server_name=domain).exists()
    rate = _KNOWN_INSTANCE_RATE if is_known else _UNKNOWN_INSTANCE_RATE
    group = f"ap-inbox-{domain}"

    return bool(
        is_ratelimited(
            request=request,
            group=group,
            key=lambda _g, _r: domain,
            rate=rate,
            increment=True,
        )
    )


@csrf_exempt
@require_POST
def user_inbox(request: HttpRequest, username: str) -> HttpResponse:
    """
    Inbox endpoint for receiving activities addressed to a user.

    POST /users/{username}/inbox
    """
    if get_local_actor("user", username) is None:
        return HttpResponseNotFound("User not found")
    return process_inbox(request, actor_type="user", actor_identifier=username)


@csrf_exempt
@require_POST
def game_inbox(request: HttpRequest, game_id: str) -> HttpResponse:
    """
    Inbox endpoint for receiving activities addressed to a game.

    POST /games/{id}/inbox
    """
    if get_local_actor("game", game_id) is None:
        return HttpResponseNotFound("Game not found")
    return process_inbox(request, actor_type="game", actor_identifier=game_id)


@csrf_exempt
@require_POST
def character_inbox(request: HttpRequest, character_id: str) -> HttpResponse:
    """
    Inbox endpoint for receiving activities addressed to a character.

    POST /characters/{id}/inbox
    """
    if get_local_actor("character", character_id) is None:
        return HttpResponseNotFound("Character not found")
    return process_inbox(request, actor_type="character", actor_identifier=character_id)


def process_inbox(request: HttpRequest, actor_type: str, actor_identifier: str) -> HttpResponse:
    """
    Common inbox processing logic.
    """
    # Rate limit check (before signature verification to save resources)
    if _check_rate_limit(request):
        domain = _get_request_domain(request)
        logger.warning("Rate limit exceeded for domain %s", domain)
        response = HttpResponse("Rate limit exceeded", status=429)
        response["Retry-After"] = "60"
        return response

    # Verify HTTP signature
    is_valid, reason = verify_signature(request)
    if not is_valid:
        logger.warning(
            "Invalid signature for %s inbox %s: %s",
            actor_type,
            actor_identifier,
            reason,
        )
        return HttpResponseForbidden("Invalid signature")

    # Parse activity
    try:
        activity: dict[str, Any] = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    activity_type = activity.get("type")
    activity_id = activity.get("id", "")
    actor_url = activity.get("actor", "")

    if not activity_type:
        return HttpResponseBadRequest("Missing activity type")

    # Validate actor domain matches signature domain
    request_domain = _get_request_domain(request)
    if actor_url and request_domain:
        from urllib.parse import urlparse as _urlparse

        actor_domain = _urlparse(actor_url).hostname
        if not actor_domain:
            return HttpResponseBadRequest("Invalid actor URL")
        # Compare hostnames only (no port) — _get_request_domain may include port
        sig_domain = _urlparse(f"https://{request_domain}").hostname or request_domain
        if actor_domain != sig_domain:
            logger.warning(
                "Actor domain mismatch: actor=%s, signature=%s",
                actor_domain,
                sig_domain,
            )
            return HttpResponseForbidden("Actor domain mismatch")

    # Inbox deduplication — atomic get_or_create to avoid race condition
    if activity_id:
        from django.db import IntegrityError

        from suddenly.activitypub.models import ProcessedActivity

        try:
            _, created = ProcessedActivity.objects.get_or_create(
                ap_id=activity_id,
                defaults={"actor_domain": request_domain or ""},
            )
            if not created:
                logger.info("Skipping duplicate activity %s", activity_id)
                return HttpResponse(status=202)
        except IntegrityError:
            logger.info("Duplicate activity detected (race): %s", activity_id)
            return HttpResponse(status=202)

    logger.info("Received %s for %s/%s", activity_type, actor_type, actor_identifier)

    # Route to appropriate handler
    handlers: dict[str, _InboxHandler] = {
        "Follow": handle_follow,
        "Undo": handle_undo,
        "Create": handle_create,
        "Update": handle_update,
        "Delete": handle_delete,
        "Offer": handle_offer,
        "Accept": handle_accept,
        "Reject": handle_reject,
    }

    handler = handlers.get(activity_type)
    if handler:
        try:
            handler(activity, actor_type, actor_identifier)
        except Exception as e:
            logger.error(f"Error handling {activity_type}: {e}")
            # Still return 202 - we received it, processing failed
    else:
        logger.warning(f"Unknown activity type: {activity_type}")

    # ActivityPub spec says to return 202 Accepted
    return HttpResponse(status=202)


class _InboxHandler(Protocol):
    def __call__(
        self, activity: dict[str, Any], actor_type: str, actor_identifier: str
    ) -> None: ...


def handle_follow(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle incoming Follow activity.

    Create a Follow record and optionally auto-accept.
    """
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Character, Follow
    from suddenly.games.models import Game
    from suddenly.users.models import User

    follower_id = activity.get("actor")
    if not follower_id:
        return

    # Get or create the remote follower
    result = get_or_create_remote_user(follower_id)
    if result is None:
        return
    follower, _ = result

    # Determine content type for the target
    content_type_map: dict[str, type[User | Game | Character]] = {
        "user": User,
        "game": Game,
        "character": Character,
    }

    model_class = content_type_map.get(actor_type)
    if not model_class:
        return

    content_type = ContentType.objects.get_for_model(model_class)

    # Get target
    target = get_local_actor(actor_type, actor_identifier)
    if not target:
        return

    # Create follow relationship
    Follow.objects.get_or_create(
        follower=follower,
        content_type=content_type,
        object_id=target.pk,
    )

    # Send Accept activity
    from .activities import get_context
    from .tasks import deliver_activity, get_actor_signing_keys

    accept_activity: dict[str, Any] = {
        "@context": get_context(),
        "type": "Accept",
        "actor": target.actor_url,
        "object": activity,
    }

    actor_key_id, private_key_pem = get_actor_signing_keys(target)

    deliver_activity.delay(
        activity=accept_activity,
        inbox_url=follower.inbox_url,
        actor_key_id=actor_key_id,
        private_key_pem=private_key_pem,
    )


def handle_undo(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle Undo activity (e.g., unfollow).
    """
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Character, Follow
    from suddenly.games.models import Game
    from suddenly.users.models import User

    inner = activity.get("object", {})
    inner_type = inner.get("type") if isinstance(inner, dict) else None

    if inner_type == "Follow":
        # Undo follow = unfollow
        follower_id = activity.get("actor")
        follower = get_remote_user(follower_id or "")
        if follower:
            target = get_local_actor(actor_type, actor_identifier)
            if target:
                # Get content type for the target model
                content_type_map: dict[str, type[User | Game | Character]] = {
                    "user": User,
                    "game": Game,
                    "character": Character,
                }
                model_class = content_type_map.get(actor_type)
                if model_class:
                    content_type = ContentType.objects.get_for_model(model_class)
                    Follow.objects.filter(
                        follower=follower,
                        content_type=content_type,
                        object_id=target.pk,
                    ).delete()


def handle_create(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle incoming Create activity.

    Supports Create(Character) — persists a remote Character to DB.
    Other object types are logged and ignored for now.
    """
    obj = activity.get("object", {})
    if not isinstance(obj, dict):
        return
    obj_type = obj.get("type")

    logger.info(f"Received Create({obj_type}) from {activity.get('actor')}")

    if obj_type == "Character":
        _handle_create_character(activity, obj)


def _handle_create_character(activity: dict[str, Any], obj: dict[str, Any]) -> None:
    """Persist an incoming remote Character."""
    from urllib.parse import urlparse

    from suddenly.characters.models import Character, CharacterStatus
    from suddenly.games.models import Game

    actor_url = activity.get("actor", "")
    ap_id = obj.get("id")
    if not ap_id:
        return

    # Skip if already known
    if Character.objects.filter(ap_id=ap_id).exists():
        return

    # Get or create the remote actor
    result = get_or_create_remote_user(actor_url)
    if result is None:
        return
    remote_user, _ = result

    # Get or create a remote Game representing the origin instance
    domain = urlparse(actor_url).netloc or "unknown"
    origin_game, _ = Game.objects.get_or_create(
        ap_id=f"https://{domain}",
        defaults={
            "title": f"Remote: {domain}",
            "owner": remote_user,
            "remote": True,
        },
    )

    Character.objects.create(
        name=obj.get("name", "Unknown"),
        description=obj.get("summary", ""),
        status=CharacterStatus.NPC,
        creator=remote_user,
        origin_game=origin_game,
        remote=True,
        ap_id=ap_id,
    )


def handle_update(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle Update activity.

    Supports Update(Character) — updates name and description of a remote Character.
    """
    obj = activity.get("object", {})
    if not isinstance(obj, dict):
        return
    obj_type = obj.get("type")

    logger.info(f"Received Update({obj_type}) from {activity.get('actor')}")

    if obj_type == "Character":
        _handle_update_character(obj)


def _handle_update_character(obj: dict[str, Any]) -> None:
    """Update fields on an existing remote Character."""
    from suddenly.characters.models import Character

    ap_id = obj.get("id")
    if not ap_id:
        return

    updated: dict[str, Any] = {}
    if "name" in obj:
        updated["name"] = obj["name"]
    if "summary" in obj:
        updated["description"] = obj["summary"]

    if updated:
        Character.objects.filter(ap_id=ap_id, remote=True).update(**updated)


def handle_delete(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle Delete activity.

    Deletes the remote object identified by the activity's ``object`` field.
    Supports Character and User (actor tombstone).
    """
    obj = activity.get("object")
    actor_url = activity.get("actor", "")

    logger.info(f"Received Delete from {actor_url}")

    if isinstance(obj, str):
        # object is a URL — determine the type by trying known models
        _handle_delete_by_url(obj, actor_url)
    elif isinstance(obj, dict):
        obj_id = obj.get("id", "")
        if obj_id:
            _handle_delete_by_url(obj_id, actor_url)


def _handle_delete_by_url(ap_id: str, actor_url: str) -> None:
    """Delete a remote entity matching ap_id, only if it belongs to the signer.

    The signature proves *who* sent the Delete and process_inbox already binds
    the actor domain to the signing domain. Here we additionally require the
    deleted object to live on the actor's own domain, so instance A cannot sign
    a Delete for an object hosted by instance B (SUD-F6).
    """
    from suddenly.characters.models import Character
    from suddenly.users.models import User

    actor_domain = urlparse(actor_url).hostname
    target_domain = urlparse(ap_id).hostname
    if not actor_domain or not target_domain or actor_domain != target_domain:
        logger.warning(
            "Rejected cross-domain Delete: actor=%s target=%s", actor_url, ap_id
        )
        return

    deleted, _ = Character.objects.filter(ap_id=ap_id, remote=True).delete()
    if deleted:
        logger.info(f"Deleted remote Character {ap_id}")
        return

    deleted, _ = User.objects.filter(ap_id=ap_id, remote=True).delete()
    if deleted:
        logger.info(f"Deleted remote User {ap_id}")


def handle_offer(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle Offer activity (claim/adopt/fork request from remote user).
    """
    from suddenly.characters.models import Character, LinkRequest, LinkType

    actor_url = activity.get("actor")
    obj = activity.get("object", {})

    if obj.get("type") != "Relationship":
        return

    relationship = obj.get("relationship")
    target_url = obj.get("object")  # The NPC being claimed

    # Map relationship to LinkType
    link_type = {
        "claim": LinkType.CLAIM,
        "adopt": LinkType.ADOPT,
        "fork": LinkType.FORK,
    }.get(relationship)

    if not link_type:
        return

    # Get remote requester
    if not actor_url:
        return
    result = get_or_create_remote_user(actor_url)
    if result is None:
        return
    requester, _ = result

    # Find local target character
    target_character = Character.objects.filter(
        ap_id=target_url,
        remote=False,
    ).first()

    if not target_character:
        return

    # Create link request
    LinkRequest.objects.create(
        type=link_type,
        requester=requester,
        target_character=target_character,
        message=activity.get("summary", ""),
    )

    logger.info(f"Created LinkRequest: {link_type} for {target_character.name}")


def _extract_link_request_id(offer_id: str) -> str | None:
    """
    Extract a LinkRequest PK from an Offer URL.

    Supports two formats:
    - .../link-requests/{pk}   (canonical format from serialize_link_request)
    - .../activities/offer/{pk}  (legacy format)
    """
    offer_str = str(offer_id)
    for segment in ("/link-requests/", "/activities/offer/"):
        if segment in offer_str:
            return offer_str.split(segment)[-1].rstrip("/") or None
    return None


def handle_accept(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle Accept activity (our offer was accepted).
    """
    from suddenly.characters.models import LinkRequest, LinkRequestStatus

    # The 'object' should be our original Offer activity ID
    offer_id = activity.get("object")
    if not offer_id:
        return

    request_id = _extract_link_request_id(str(offer_id))
    if request_id:
        try:
            link_request = LinkRequest.objects.get(id=request_id)
            link_request.status = LinkRequestStatus.ACCEPTED
            link_request.response_message = activity.get("summary", "")
            link_request.save()
            logger.info(f"LinkRequest {request_id} accepted")
        except (LinkRequest.DoesNotExist, ValueError):
            pass


def handle_reject(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle Reject activity (our offer was rejected).
    """
    from suddenly.characters.models import LinkRequest, LinkRequestStatus

    offer_id = activity.get("object")
    if not offer_id:
        return

    request_id = _extract_link_request_id(str(offer_id))
    if request_id:
        try:
            link_request = LinkRequest.objects.get(id=request_id)
            link_request.status = LinkRequestStatus.REJECTED
            link_request.response_message = activity.get("summary", "")
            link_request.save()
            logger.info(f"LinkRequest {request_id} rejected")
        except (LinkRequest.DoesNotExist, ValueError):
            pass


# =================================================================
# Helper functions
# =================================================================


def get_or_create_remote_user(
    actor_url: str,
) -> tuple[Any, bool] | None:
    """
    Return a remote User by actor URL, fetching from the remote server if not
    already in DB.

    Returns (user, created) on success, None if the actor cannot be resolved.
    The DB is checked first to avoid unnecessary HTTP requests during tests and
    when the actor was already fetched during signature verification.
    """
    from suddenly.users.models import User

    from ._http import fetch_ap_actor

    # Fast path: actor already known
    existing = User.objects.filter(ap_id=actor_url, remote=True).first()
    if existing:
        return existing, False

    # Slow path: fetch from remote
    actor_data = fetch_ap_actor(actor_url)
    if actor_data is None:
        return None

    username = actor_data.get("preferredUsername", actor_url.split("/")[-1])

    user, created = User.objects.update_or_create(
        ap_id=actor_url,
        defaults={
            "username": f"{username}@{actor_url.split('/')[2]}",
            "display_name": actor_data.get("name", username),
            "bio": actor_data.get("summary", ""),
            "remote": True,
            "inbox_url": actor_data.get("inbox"),
            "outbox_url": actor_data.get("outbox"),
            "public_key": actor_data.get("publicKey", {}).get("publicKeyPem", ""),
        },
    )

    return user, created


def get_remote_user(actor_url: str) -> Any:
    """
    Get an existing remote user by actor URL.
    """
    from suddenly.users.models import User

    return User.objects.filter(ap_id=actor_url, remote=True).first()


def get_local_actor(actor_type: str, identifier: str) -> Any:
    """
    Get a local actor (user, game, or character) by identifier.
    """
    from suddenly.characters.models import Character
    from suddenly.games.models import Game
    from suddenly.users.models import User

    if actor_type == "user":
        return User.objects.filter(username=identifier, remote=False).first()
    elif actor_type == "game":
        return Game.objects.filter(id=identifier, remote=False).first()
    elif actor_type == "character":
        return Character.objects.filter(id=identifier, remote=False).first()
    return None
