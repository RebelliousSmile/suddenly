"""
ActivityPub inbox views for receiving federated activities.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol
from urllib.parse import urlparse

from django.conf import settings
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

    Supports Create(Character) — persists a remote Character to DB — and
    Create(Article) — persists a remote Report (scene) with its fiction-order links.
    Other object types are logged and ignored for now.
    """
    obj = activity.get("object", {})
    if not isinstance(obj, dict):
        return
    obj_type = obj.get("type")

    logger.info(f"Received Create({obj_type}) from {activity.get('actor')}")

    if obj_type == "Character":
        _handle_create_character(activity, obj)
    elif obj_type == "Article":
        _handle_create_report(activity, obj)


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

    character = Character.objects.create(
        name=obj.get("name", "Unknown"),
        description=obj.get("summary", ""),
        status=CharacterStatus.NPC,
        creator=remote_user,
        origin_game=origin_game,
        remote=True,
        ap_id=ap_id,
    )

    # Narrative meta-model extension (issue F) — tolerant: absent block is fine.
    _ingest_trait_sets(character, obj)


def _read_ap_term(obj: dict[str, Any], term: str) -> str | None:
    """Read a Suddenly extension term, tolerating the compact and expanded forms.

    ``previousReport`` is emitted compact (the ``@context`` maps it to
    ``suddenly:previousReport``); a stricter peer may deliver it expanded. Mirrors
    the fallback in :func:`_ingest_trait_sets`. Non-string / empty → ``None``.
    """
    value = obj.get(term)
    if value is None:
        value = obj.get(f"suddenly:{term}")
    return value if isinstance(value, str) and value else None


def _resolve_fiction_links(report: Any, obj: dict[str, Any]) -> None:
    """Resolve the incoming fiction-order block onto a freshly ingested Report.

    Tolerant and deferred (fiction-order spec): read ``previousReport`` /
    ``temporalAnchor`` soft IRIs — if an IRI matches a Report already known by
    ``ap_id``, wire the FK **and clear the IRI** (XOR CheckConstraint); otherwise
    store the IRI alone (resolved later when the anchor scene arrives). Absent block
    is a no-op; malformed terms are ignored.
    """
    from suddenly.games.models import Report, ReportTemporalKind

    update_fields: list[str] = []

    previous_iri = _read_ap_term(obj, "previousReport")
    if previous_iri:
        match = Report.objects.filter(ap_id=previous_iri).first()
        if match is not None:
            report.previous_report = match
            report.previous_report_iri = None
        else:
            report.previous_report_iri = previous_iri[:500]
        update_fields += ["previous_report", "previous_report_iri"]

    anchor_iri = _read_ap_term(obj, "temporalAnchor")
    if anchor_iri:
        match = Report.objects.filter(ap_id=anchor_iri).first()
        if match is not None:
            report.temporal_anchor = match
            report.temporal_anchor_iri = None
        else:
            report.temporal_anchor_iri = anchor_iri[:500]
        update_fields += ["temporal_anchor", "temporal_anchor_iri"]

    temporal_kind = _read_ap_term(obj, "temporalKind")
    if temporal_kind in (ReportTemporalKind.FLASHBACK, ReportTemporalKind.FLASHFORWARD):
        report.temporal_kind = temporal_kind
        update_fields.append("temporal_kind")

    temporal_label = _read_ap_term(obj, "temporalLabel")
    if temporal_label:
        report.temporal_label = temporal_label[:120]
        update_fields.append("temporal_label")

    if update_fields:
        report.save(update_fields=[*update_fields, "updated_at"])


def _infer_visibility(obj: dict[str, Any]) -> str:
    """Infer a Report visibility from AS2 ``to``/``cc`` addressing (default public)."""
    from suddenly.games.models import ReportVisibility

    public = "https://www.w3.org/ns/activitystreams#Public"
    to = obj.get("to") or []
    cc = obj.get("cc") or []
    to = [to] if isinstance(to, str) else list(to)
    cc = [cc] if isinstance(cc, str) else list(cc)
    if public in to:
        return ReportVisibility.PUBLIC
    if public in cc:
        return ReportVisibility.UNLISTED
    if to:  # addressed to followers only, Public nowhere
        return ReportVisibility.FOLLOWERS
    return ReportVisibility.PUBLIC


def _handle_create_report(activity: dict[str, Any], obj: dict[str, Any]) -> None:
    """Persist an incoming remote Report (AP ``Article``), with its fiction links.

    Calqued on :func:`_handle_create_character`: idempotent by ``ap_id`` (a double
    POST creates exactly one Report), remote author via ``get_or_create_remote_user``,
    remote Game via the Article ``context``. The fiction-order block is resolved by
    :func:`_resolve_fiction_links` (soft IRI → FK when the anchor is already known).
    """
    from urllib.parse import urlparse

    from django.utils.dateparse import parse_datetime

    from suddenly.games.models import Game, Report, ReportStatus

    ap_id = obj.get("id")
    if not ap_id:
        return

    # Idempotence (business dedup by ap_id — transport dedup is ProcessedActivity).
    if Report.objects.filter(ap_id=ap_id).exists():
        return

    actor_url = activity.get("actor") or obj.get("attributedTo") or ""
    if not actor_url:
        return
    result = get_or_create_remote_user(actor_url)
    if result is None:
        return
    remote_user, _ = result

    # Remote Game via the Article's context IRI; fall back to a per-domain game.
    game_iri = obj.get("context")
    if isinstance(game_iri, str) and game_iri:
        game, _ = Game.objects.get_or_create(
            ap_id=game_iri,
            defaults={"title": "Remote game", "owner": remote_user, "remote": True},
        )
    else:
        domain = urlparse(actor_url).netloc or "unknown"
        game, _ = Game.objects.get_or_create(
            ap_id=f"https://{domain}",
            defaults={"title": f"Remote: {domain}", "owner": remote_user, "remote": True},
        )

    published_raw = obj.get("published")
    published_at = parse_datetime(published_raw) if isinstance(published_raw, str) else None

    report = Report.objects.create(
        game=game,
        author=remote_user,
        title=str(obj.get("name") or "")[:200],
        content=str(obj.get("content") or ""),
        status=ReportStatus.PUBLISHED,
        visibility=_infer_visibility(obj),
        published_at=published_at,
        remote=True,
        ap_id=ap_id,
    )

    _resolve_fiction_links(report, obj)


def _ingest_trait_sets(character: Any, obj: dict[str, Any]) -> None:
    """Ingest the ``traitSet`` AP extension onto a remote Character.

    Tolerant by design: a remote sheet with traits is displayed; one without
    traits stays valid (no-op); malformed entries are skipped. A third-party
    server that never emits this vocabulary is simply ignored here. Nothing is
    evaluated — traits are stored for display only.

    Idempotent for updates: existing trait sets are replaced wholesale.
    """
    from suddenly.characters.models import Action, Trait, TraitSet

    raw = obj.get("traitSet")
    if raw is None:
        raw = obj.get("suddenly:traitSet")  # tolerate expanded term
    if not isinstance(raw, list):
        return

    character.trait_sets.all().delete()

    for set_order, ts in enumerate(raw):
        if not isinstance(ts, dict):
            continue
        label = str(ts.get("label") or "Traits")[:100]
        trait_set = TraitSet.objects.create(character=character, label=label, order=set_order)

        name_to_trait: dict[str, Any] = {}
        raw_traits = ts.get("traits")
        if isinstance(raw_traits, list):
            for trait_order, item in enumerate(raw_traits):
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()[:200]
                if not name:
                    continue
                value = item.get("value")
                # Only accept genuine integers; anything else → valueless tag.
                if isinstance(value, bool) or not isinstance(value, int):
                    value = None
                trait = Trait.objects.create(
                    trait_set=trait_set,
                    name=name,
                    value=value,
                    note=str(item.get("note") or ""),
                    order=trait_order,
                )
                name_to_trait[name] = trait

        raw_actions = ts.get("actions")
        if isinstance(raw_actions, list):
            for action_order, item in enumerate(raw_actions):
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()[:200]
                if not name:
                    continue
                action = Action.objects.create(
                    trait_set=trait_set,
                    character=character,
                    name=name,
                    condition=str(item.get("condition") or ""),
                    outcome=str(item.get("outcome") or ""),
                    order=action_order,
                )
                linked_names = item.get("traits")
                if isinstance(linked_names, list):
                    linked = [
                        name_to_trait[n]
                        for n in linked_names
                        if isinstance(n, str) and n in name_to_trait
                    ]
                    if linked:
                        action.traits.set(linked)


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
    elif obj_type == "Person":
        # A remote actor announcing an updated profile may have rotated its
        # signing key. Drop the cached key so the next verification re-fetches
        # it, instead of failing once against the stale key (08-activitypub §4b).
        _invalidate_actor_key(activity.get("actor"))


def _invalidate_actor_key(actor_url: object) -> None:
    """Drop the cached public key for a remote actor (key rotation via Update(Person))."""
    from .models import PublicKeyCache

    if isinstance(actor_url, str) and actor_url:
        PublicKeyCache.objects.filter(actor_url=actor_url).delete()


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

    # Refresh the traitSet extension if present (issue F). Absent → left as-is.
    if "traitSet" in obj or "suddenly:traitSet" in obj:
        character = Character.objects.filter(ap_id=ap_id, remote=True).first()
        if character is not None:
            _ingest_trait_sets(character, obj)


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
        logger.warning("Rejected cross-domain Delete: actor=%s target=%s", actor_url, ap_id)
        return

    deleted, _ = Character.objects.filter(ap_id=ap_id, remote=True).delete()
    if deleted:
        logger.info(f"Deleted remote Character {ap_id}")
        return

    deleted, _ = User.objects.filter(ap_id=ap_id, remote=True).delete()
    if deleted:
        logger.info(f"Deleted remote User {ap_id}")


def _resolve_character_by_actor_url(actor_url: str | None) -> Any:
    """
    Resolve a Character from its ActivityPub actor URL.

    Remote characters are matched on their stored ``ap_id``. Local characters
    expose a computed actor URL (``{AP_BASE_URL}/characters/{pk}``) and store no
    ``ap_id``, so they are resolved by parsing the trailing primary key.
    """
    from django.core.exceptions import ValidationError

    from suddenly.characters.models import Character

    if not actor_url:
        return None

    remote = Character.objects.filter(ap_id=actor_url).first()
    if remote:
        return remote

    prefix = f"{settings.AP_BASE_URL}/characters/"
    if actor_url.startswith(prefix):
        pk = actor_url[len(prefix) :].strip("/")
        try:
            return Character.objects.filter(pk=pk, remote=False).first()
        except (ValueError, ValidationError):
            return None
    return None


def handle_offer(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle Offer activity (claim/adopt/fork request from a remote user).

    Parses the canonical Suddenly Offer emitted by
    ``serializers.serialize_link_request``:
    - ``object.type`` = ``suddenly:Claim`` / ``suddenly:Adopt`` / ``suddenly:Fork``
    - target NPC actor URL in the top-level ``target``
    - proposed PC actor URL in ``object.proposedCharacter`` (Claim only)
    - narrative message in ``object.content``
    """
    from suddenly.characters.models import LinkRequest, LinkRequestStatus, LinkType

    actor_url = activity.get("actor")
    obj = activity.get("object")
    if not actor_url or not isinstance(obj, dict):
        return

    link_type = {
        "suddenly:Claim": LinkType.CLAIM,
        "suddenly:Adopt": LinkType.ADOPT,
        "suddenly:Fork": LinkType.FORK,
    }.get(obj.get("type", ""))
    if not link_type:
        return

    # Resolve the remote requester (may fetch the actor if unknown)
    result = get_or_create_remote_user(actor_url)
    if result is None:
        return
    requester, _ = result

    # The targeted NPC is local on this instance (top-level `target`)
    target_character = _resolve_character_by_actor_url(activity.get("target"))
    if target_character is None or target_character.remote:
        return

    # A Claim carries the proposed PC (remote here) — resolve locally first, then
    # fall back to fetching the remote actor (DEC-038 Part 3). A CLAIM whose
    # proposed PC stays null would crash at acceptance on the non-null
    # CharacterLink.source, so resolving it here is a hard prerequisite for CLAIM.
    proposed_url = obj.get("proposedCharacter")
    proposed_character = _resolve_character_by_actor_url(proposed_url)
    if proposed_character is None and isinstance(proposed_url, str) and proposed_url:
        proposed_character = get_or_create_remote_character(proposed_url)

    # Preserve the one-PENDING-at-a-time invariant (mirrors LinkService.create_request)
    has_pending = LinkRequest.objects.filter(
        target_character=target_character, status=LinkRequestStatus.PENDING
    ).exists()
    status = LinkRequestStatus.QUEUED if has_pending else LinkRequestStatus.PENDING

    LinkRequest.objects.create(
        type=link_type,
        requester=requester,
        target_character=target_character,
        proposed_character=proposed_character,
        message=obj.get("content", ""),
        status=status,
        # Correlate a future Accept back to the requester's own LinkRequest (Part 1).
        origin_offer_id=activity.get("id") or None,
    )

    logger.info("Created LinkRequest: %s for %s", link_type, target_character.name)


def get_or_create_remote_character(actor_url: str) -> Any:
    """Resolve a remote Character actor URL to a local mirror, fetching if unknown.

    Used when an inbound Offer's ``proposedCharacter`` points at a Character this
    instance has never seen (DEC-038 Part 3). Mirrors the synthesis done in
    :func:`_handle_create_character`: a per-domain remote ``Game`` provides the
    non-null ``origin_game`` (08-characters), the actor's ``creator``/``owner``
    resolves the remote author. Tolerant: any fetch failure returns ``None`` so
    the caller degrades to a null proposed PC rather than dropping the Offer.

    The remote GET goes through ``fetch_ap_actor`` → ``fetch_ap_json`` (SSRF
    hardening, ap-pivots §9) — never raw httpx.
    """
    from urllib.parse import urlparse

    from suddenly.characters.models import Character, CharacterStatus
    from suddenly.games.models import Game

    from ._http import fetch_ap_actor

    if not actor_url:
        return None

    existing = Character.objects.filter(ap_id=actor_url).first()
    if existing:
        return existing

    data = fetch_ap_actor(actor_url)
    if data is None:
        return None

    # The character actor advertises its author via `creator` (see
    # serialize_character). `owner` is the PC's player when set. NOT `attributedTo`:
    # for a Character that field is the origin Game actor URL, never the author —
    # feeding it to get_or_create_remote_user would mint a bogus User from a Group.
    creator_url = data.get("creator") or data.get("owner")
    if not isinstance(creator_url, str) or not creator_url:
        return None
    result = get_or_create_remote_user(creator_url)
    if result is None:
        return None
    remote_user, _ = result

    domain = urlparse(actor_url).netloc or "unknown"
    origin_game, _ = Game.objects.get_or_create(
        ap_id=f"https://{domain}",
        defaults={
            "title": f"Remote: {domain}",
            "owner": remote_user,
            "remote": True,
        },
    )

    character, _ = Character.objects.get_or_create(
        ap_id=actor_url,
        defaults={
            "name": data.get("name", "Unknown"),
            "description": data.get("summary", ""),
            "status": CharacterStatus.NPC,
            "creator": remote_user,
            "origin_game": origin_game,
            "remote": True,
        },
    )
    return character


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


def _offer_id_from_activity(activity: dict[str, Any]) -> str | None:
    """Extract the Offer id an Accept/Reject references.

    The canonical Accept carries ``object`` as the string ``origin_offer_id`` of
    the requester's own Offer (DEC-038 Part 1). By robustness we also tolerate an
    embedded dict, reading its ``id`` before parsing (a raw ``str(dict)`` would
    yield a noisy Python repr from which no valid PK can be extracted).
    """
    offer_id = activity.get("object")
    if isinstance(offer_id, dict):
        offer_id = offer_id.get("id")
    if not isinstance(offer_id, str) or not offer_id:
        return None
    return offer_id


def handle_accept(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle Accept activity (our offer was accepted).

    Correlates the Accept back to our own LinkRequest by the Offer id (Part 1),
    then replays the full state reconstruction on the requester side —
    CharacterLink, SharedSequence, status, notification (Part 2) — via
    ``LinkService.reconstruct_remote_accept`` (idempotent on replay).
    """
    from suddenly.characters.models import LinkRequest
    from suddenly.characters.services import LinkService

    offer_id = _offer_id_from_activity(activity)
    if not offer_id:
        return

    request_id = _extract_link_request_id(offer_id)
    if not request_id:
        return
    try:
        link_request = LinkRequest.objects.get(id=request_id)
    except (LinkRequest.DoesNotExist, ValueError):
        return

    LinkService.reconstruct_remote_accept(link_request, activity.get("summary", ""))
    logger.info("LinkRequest %s accepted (remote)", request_id)


def handle_reject(activity: dict[str, Any], actor_type: str, actor_identifier: str) -> None:
    """
    Handle Reject activity (our offer was rejected).
    """
    from suddenly.characters.models import LinkRequest, LinkRequestStatus

    offer_id = _offer_id_from_activity(activity)
    if not offer_id:
        return

    request_id = _extract_link_request_id(offer_id)
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
