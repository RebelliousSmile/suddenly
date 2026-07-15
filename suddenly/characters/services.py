"""
Character services — link workflows and queryset builders.
"""

from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.utils import timezone

from suddenly.core.models import Notification, NotificationType
from suddenly.games.models import Game
from suddenly.users.models import User

from .models import (
    Action,
    Character,
    CharacterLink,
    CharacterLinkStatus,
    CharacterStatus,
    Follow,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
    SharedSequence,
    SharedSequenceStatus,
    Trait,
    TraitSet,
)


class LinkService:
    """
    Service for managing character links (claim, adopt, fork).
    """

    @staticmethod
    def validate_claim(
        requester: User, target_character: Character, proposed_character: Character | None
    ) -> None:
        """
        Validate a claim request.

        Rules:
        - Target must be an available NPC
        - Proposed character must be a PC owned by requester
        """
        if target_character.status != CharacterStatus.NPC:
            raise ValidationError(
                f"{target_character.name} n'est plus disponible "
                f"(statut: {target_character.get_status_display()})"
            )

        if not proposed_character:
            raise ValidationError("Un claim nécessite un PJ existant")

        if proposed_character.status != CharacterStatus.PC:
            raise ValidationError(f"{proposed_character.name} n'est pas un PJ")

        if proposed_character.owner != requester:
            raise ValidationError("Vous ne pouvez claim qu'avec un de vos propres PJ")

    @staticmethod
    def validate_adopt(requester: User, target_character: Character) -> None:
        """
        Validate an adopt request.

        Rules:
        - Target must be an available NPC
        """
        if target_character.status != CharacterStatus.NPC:
            raise ValidationError(f"{target_character.name} n'est plus disponible")

    @staticmethod
    def validate_fork(requester: User, target_character: Character) -> None:
        """
        Validate a fork request.

        Rules:
        - Target can be any character (NPC, PC, or already linked)
        - Forks are always allowed (they create new characters)
        """
        # Forks are more permissive - just check target exists
        if not target_character:
            raise ValidationError("Personnage cible introuvable")

    @classmethod
    @transaction.atomic
    def create_request(
        cls,
        requester: User,
        target_character: Character,
        link_type: str,
        message: str,
        proposed_character: Character | None = None,
    ) -> LinkRequest:
        """
        Create a link request after validation.

        Returns the created LinkRequest.
        """
        locked_char = Character.objects.select_for_update().get(pk=target_character.pk)

        # Validate based on type
        if link_type == LinkType.CLAIM:
            cls.validate_claim(requester, locked_char, proposed_character)
        elif link_type == LinkType.ADOPT:
            cls.validate_adopt(requester, locked_char)
        elif link_type == LinkType.FORK:
            cls.validate_fork(requester, locked_char)
        else:
            raise ValidationError(f"Type de lien inconnu: {link_type}")

        has_pending = LinkRequest.objects.filter(
            target_character=locked_char, status=LinkRequestStatus.PENDING
        ).exists()
        status = LinkRequestStatus.QUEUED if has_pending else LinkRequestStatus.PENDING

        # Create the request
        request = LinkRequest.objects.create(
            type=link_type,
            requester=requester,
            target_character=locked_char,
            proposed_character=proposed_character,
            message=message,
            status=status,
        )

        # TODO: Send ActivityPub Offer activity

        return request

    @classmethod
    @transaction.atomic
    def accept_request(cls, request: LinkRequest, response_message: str = "") -> CharacterLink:
        """
        Accept a link request and create the link.

        This:
        1. Updates the request status
        2. Creates the CharacterLink
        3. Updates character statuses
        4. Creates a SharedSequence draft
        5. Triggers ActivityPub Accept
        """
        if request.status != LinkRequestStatus.PENDING:
            raise ValidationError("Cette demande n'est plus en attente")

        # Determine source character
        source: Character
        if request.type == LinkType.CLAIM:
            source = request.proposed_character  # type: ignore[assignment]
        elif request.type == LinkType.ADOPT:
            # Create new PC from NPC for adopter
            source = request.target_character
        elif request.type == LinkType.FORK:
            # Create a new character as fork
            source = Character.objects.create(
                name=f"{request.target_character.name} (fork)",
                description=request.target_character.description,
                status=CharacterStatus.PC,
                owner=request.requester,
                creator=request.requester,
                origin_game=request.target_character.origin_game,
                parent=request.target_character,
            )
        else:
            raise ValidationError(f"Type inconnu: {request.type}")

        # Update request
        request.status = LinkRequestStatus.ACCEPTED
        request.response_message = response_message
        request.resolved_at = timezone.now()
        request.save()

        # Update target character status
        if request.type in (LinkType.CLAIM, LinkType.ADOPT):
            request.target_character.status = (
                CharacterStatus.CLAIMED
                if request.type == LinkType.CLAIM
                else CharacterStatus.ADOPTED
            )
            if request.type == LinkType.ADOPT:
                request.target_character.owner = request.requester
            request.target_character.save()
        elif request.type == LinkType.FORK:
            # Mark original as forked (but it stays available)
            # Actually, for fork the original doesn't change status
            pass

        # Create the link
        link = CharacterLink.objects.create(
            type=request.type,
            source=source,
            target=request.target_character,
            link_request=request,
        )

        # Create shared sequence draft
        SharedSequence.objects.create(
            link=link,
            title=f"Séquence: {source.name} ↔ {request.target_character.name}",
            content="",  # To be filled by players
        )

        if request.type in [LinkType.CLAIM, LinkType.ADOPT]:
            LinkRequest.objects.filter(
                target_character=request.target_character,
                status=LinkRequestStatus.QUEUED,
            ).update(status=LinkRequestStatus.CANCELLED, resolved_at=timezone.now())

        # TODO: Send ActivityPub Accept activity
        # TODO: Notify both parties

        return link

    @staticmethod
    def get_queue_position(request: LinkRequest) -> int | None:
        """
        Return 1-indexed queue position for a QUEUED request, or None if not QUEUED.
        """
        if request.status != LinkRequestStatus.QUEUED:
            return None
        count = LinkRequest.objects.filter(
            target_character=request.target_character,
            status=LinkRequestStatus.QUEUED,
            created_at__lt=request.created_at,
        ).count()
        return count + 1

    @classmethod
    def _promote_next_queued(cls, target_character: Character) -> None:
        """
        Promote the oldest QUEUED request on a character to PENDING and notify its requester.
        """
        next_queued = (
            LinkRequest.objects.select_related("requester")
            .filter(target_character=target_character, status=LinkRequestStatus.QUEUED)
            .order_by("created_at")
            .first()
        )
        if next_queued:
            next_queued.status = LinkRequestStatus.PENDING
            next_queued.save(update_fields=["status", "updated_at"])
            Notification.objects.create(
                recipient=target_character.creator,
                type=NotificationType.LINK_REQUEST,
                actor=next_queued.requester,
                target_content_type=ContentType.objects.get_for_model(LinkRequest),
                target_object_id=next_queued.pk,
                message=(
                    f"{next_queued.requester} a une nouvelle demande"
                    f" en attente sur {target_character.name}"
                ),
            )

    @classmethod
    @transaction.atomic
    def reject_request(cls, request: LinkRequest, response_message: str = "") -> LinkRequest:
        """
        Reject a link request.
        """
        if request.status != LinkRequestStatus.PENDING:
            raise ValidationError("Cette demande n'est plus en attente")

        target_character = Character.objects.select_related("creator").get(
            pk=request.target_character_id
        )

        request.status = LinkRequestStatus.REJECTED
        request.response_message = response_message
        request.resolved_at = timezone.now()
        request.save()

        cls._promote_next_queued(target_character)

        return request

    @classmethod
    @transaction.atomic
    def cancel_request(cls, request: LinkRequest) -> LinkRequest:
        """
        Cancel a pending or queued request (by requester).
        """
        if request.status not in [LinkRequestStatus.PENDING, LinkRequestStatus.QUEUED]:
            raise ValidationError("Cette demande n'est plus en attente")

        if request.status == LinkRequestStatus.PENDING:
            target_character = Character.objects.select_related("creator").get(
                pk=request.target_character_id
            )
            cls._promote_next_queued(target_character)

        request.status = LinkRequestStatus.CANCELLED
        request.resolved_at = timezone.now()
        request.save()

        return request

    @classmethod
    @transaction.atomic
    def publish_sequence(cls, sequence: SharedSequence, actor: User) -> None:
        """
        Publish a shared sequence draft and notify both parties.

        Character status and link activation already happen at acceptance
        (see ``accept_request`` / DEC-035); publication finalizes the co-created
        content and notifies the participants. Raises ``ValidationError`` if the
        sequence is not a draft.
        """
        if sequence.status != SharedSequenceStatus.DRAFT:
            raise ValidationError("Cette séquence n'est plus en brouillon")

        sequence.status = SharedSequenceStatus.PUBLISHED
        sequence.save(update_fields=["status", "updated_at"])

        cls._notify_sequence_published(sequence, actor)

    @staticmethod
    def _notify_sequence_published(sequence: SharedSequence, actor: User) -> None:
        """Notify both link participants (except the actor) that a sequence is published."""
        link = sequence.link
        requester = link.link_request.requester if link.link_request else None
        creator = link.target.creator
        recipients = {u for u in (requester, creator) if u is not None and u != actor}
        if not recipients:
            return

        ct = ContentType.objects.get_for_model(SharedSequence)
        message = (
            f"La séquence « {sequence.title} » a été publiée"
            if sequence.title
            else "Une séquence partagée a été publiée"
        )
        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                type=NotificationType.SHARED_SEQUENCE,
                actor=actor,
                target_content_type=ct,
                target_object_id=sequence.pk,
                message=message,
            )

    @classmethod
    @transaction.atomic
    def revoke_link(cls, link: CharacterLink, reason: str, actor: User) -> None:
        """
        Revoke an established character link.

        If the associated SharedSequence is published, the link is marked REVOKED
        (the sequence remains visible). Otherwise the draft sequence and the link
        itself are deleted.

        In both cases the target character is reverted to NPC status and a
        REVOCATION notification is sent to the other party.
        """
        ss = getattr(link, "shared_sequence", None)
        if ss and ss.status == SharedSequenceStatus.PUBLISHED:
            link.status = CharacterLinkStatus.REVOKED
            link.save(update_fields=["status", "updated_at"])
        else:
            if ss:
                ss.delete()
            link.delete()

        link.target.status = CharacterStatus.NPC
        link.target.owner = None
        link.target.save(update_fields=["status", "owner", "updated_at"])

        recipient = (
            link.link_request.requester
            if link.link_request and actor == link.target.creator
            else link.target.creator
        )
        Notification.objects.create(
            recipient=recipient,
            type=NotificationType.REVOCATION,
            actor=actor,
            target_content_type=ContentType.objects.get_for_model(Character),
            target_object_id=link.target.pk,
            message=f"{actor} a révoqué le lien sur {link.target.name}",
        )


@transaction.atomic
def create_character_with_sheet(
    *,
    user: User,
    name: str,
    description: str,
    origin_game: Game,
    sheet_url: str,
    avatar: object | None,
    cover_alt: str,
    cover_tone: str,
    trait_sets: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> Character:
    """Create a full PC (identity + multi-concept traits + cross-concept actions) atomically.

    Backs the single-gesture ``characters:create`` flow: the caller (Phase 3's
    view) has already ``json.loads``-ed the payload into plain Python objects —
    this function only builds the domain graph and never touches ``HttpRequest``.

    ``trait_sets`` — ``[{"label": str, "traits": [{"name": str, "value": int|None,
    "note": str}]}]``, created in order (``order=index`` on both ``TraitSet`` and
    ``Trait``).

    ``actions`` — ``[{"name": str, "trait_refs": [[set_index, trait_index]],
    "condition": str, "outcome": str}]``. Every action is created with
    ``trait_set=None`` (cross-concept, per ``Action.character`` widening in
    Phase 1) and its ``trait_refs`` resolved against the ``Trait`` instances
    just created in this same call, by ``(set_index, trait_index)`` position.

    An out-of-bounds ``trait_refs`` entry raises ``KeyError`` naturally (lookup
    against the ``(set_index, trait_index)`` map built while creating traits) —
    deliberately not wrapped into ``ValidationError``, so Phase 3's view must
    catch ``KeyError`` (alongside ``ValidationError`` from ``full_clean()``)
    around its call to this service. Being inside ``@transaction.atomic``, any
    such exception rolls back the whole call — no orphaned ``Character``/
    ``TraitSet``/``Trait``/``Action`` rows survive a failed create.

    ``slug`` is excluded from ``full_clean()`` — it is still blank at this
    point and auto-generated inside ``Character.save()``'s override (same
    defensive precedent as ``create_scene_post``'s
    ``rapport.full_clean(exclude=["report"])`` in ``games/services.py``).
    """
    character = Character(
        name=name,
        description=description,
        status=CharacterStatus.PC,
        owner=user,
        creator=user,
        origin_game=origin_game,
        sheet_url=sheet_url,
        avatar=avatar,
        cover_alt=cover_alt,
        cover_tone=cover_tone,
    )
    character.full_clean(exclude=["slug"])
    character.save()

    traits_by_ref: dict[tuple[int, int], Trait] = {}
    for set_index, trait_set_data in enumerate(trait_sets):
        trait_set = TraitSet(
            character=character,
            label=trait_set_data["label"],
            order=set_index,
        )
        trait_set.full_clean()
        trait_set.save()

        for trait_index, trait_data in enumerate(trait_set_data["traits"]):
            trait = Trait(
                trait_set=trait_set,
                name=trait_data["name"],
                value=trait_data.get("value"),
                note=trait_data.get("note", ""),
                order=trait_index,
            )
            trait.full_clean()
            trait.save()
            traits_by_ref[(set_index, trait_index)] = trait

    for action_index, action_data in enumerate(actions):
        action = Action(
            character=character,
            trait_set=None,
            name=action_data["name"],
            condition=action_data.get("condition", ""),
            outcome=action_data.get("outcome", ""),
            order=action_index,
        )
        action.full_clean()
        action.save()

        resolved_traits = [
            traits_by_ref[(set_index, trait_index)]
            for set_index, trait_index in action_data.get("trait_refs", [])
        ]
        action.traits.set(resolved_traits)

    return character


def build_transverse_actions_queryset(character: Character) -> QuerySet[Action]:
    """Cross-concept actions on a character — ``trait_set=None`` (span multiple concepts).

    Shared by ``character_detail`` ("Actions transverses" block) and
    ``traits_editor`` — both need the same "actions not scoped to a single
    ``TraitSet``" queryset (DEC: shared queryset builders live in services.py
    as soon as 2+ callers need them).
    """
    return character.actions.filter(trait_set__isnull=True).prefetch_related("traits")


def build_owned_pc_queryset(user: User) -> QuerySet[Character]:
    """A player's own player-characters — ``owner=user, status=pc``.

    This is the actor vivier of the post composer when the writer acts as a
    *player* (they may only make their own PCs speak). It is distinct from
    :func:`build_character_queryset`, which never filters by ``owner``, and from
    the GM-owned filter of ``report_compose`` (parties I own).
    """
    return Character.objects.filter(owner=user, status=CharacterStatus.PC)


def suggested_characters_to_link(user: User, limit: int = 8) -> list[Character]:
    """Candidates a new PC could claim/adopt/fork, blended by relevance.

    A claim/adopt/fork always targets *another* player's character (you link your
    PC to someone else's NPC), so candidates exclude anything the caller created
    or owns, and anything remote (local linking only). Only linkable statuses
    survive: NPC (claim/adopt/fork) or PC (fork only) — CLAIMED/ADOPTED/FORKED
    expose no action, so they are dropped.

    Sources are unioned in priority order and de-duplicated:
      1. characters the user follows directly,
      2. characters created/owned by accounts the user follows,
      3. characters that have appeared in the user's own games (co-play),
      4. most-recent linkable characters (filler).

    Each returned Character carries a transient ``available_actions`` list (subset
    of ``["claim", "adopt", "fork"]``) so the template renders only the actions
    the link views will actually accept.
    """
    base = (
        Character.objects.filter(
            remote=False,
            status__in=[CharacterStatus.NPC, CharacterStatus.PC],
        )
        .exclude(creator=user)
        .exclude(owner=user)
        .select_related("creator", "owner", "origin_game")
        .prefetch_related("tags")
        .order_by("-created_at")
    )

    char_ct = ContentType.objects.get_for_model(Character)
    followed_char_ids = list(
        Follow.objects.filter(follower=user, content_type=char_ct).values_list(
            "object_id", flat=True
        )
    )

    user_ct = ContentType.objects.get_for_model(User)
    followed_user_ids = list(
        Follow.objects.filter(follower=user, content_type=user_ct).values_list(
            "object_id", flat=True
        )
    )

    buckets: list[QuerySet[Character]] = [
        base.filter(pk__in=followed_char_ids),
        base.filter(Q(creator_id__in=followed_user_ids) | Q(owner_id__in=followed_user_ids)),
        base.filter(appearances__report__game__owner=user).distinct(),
        # Recent NPCs first (claim/adopt/fork all apply), then any linkable filler.
        base.filter(status=CharacterStatus.NPC),
        base,
    ]

    seen: set[Any] = set()
    ordered: list[Character] = []
    for bucket in buckets:
        for character in bucket[: limit * 2]:
            if character.pk in seen:
                continue
            seen.add(character.pk)
            ordered.append(character)
            if len(ordered) >= limit:
                break
        if len(ordered) >= limit:
            break

    for character in ordered:
        # Transient view-model attribute read by templates/characters/_link_suggestions.html;
        # setattr keeps mypy from flagging an attribute the model does not declare.
        setattr(
            character,
            "available_actions",
            ["claim", "adopt", "fork"] if character.status == CharacterStatus.NPC else ["fork"],
        )

    return ordered


def build_character_queryset(
    q: str = "",
    status: str = "",
    tag: str = "",
) -> QuerySet[Character]:
    """Build filtered character queryset from explicit params.

    US-07: characters are discovered by name (FTS) and tags. There is no
    game-system filter — Suddenly has no system catalogue.
    """
    qs = (
        Character.objects.filter(remote=False)
        .select_related("creator", "owner", "origin_game")
        .annotate(
            report_count=Count("appearances__report", distinct=True),
            quote_count=Count("quotes", distinct=True),
        )
        .order_by("-created_at")
    )

    if status and status in CharacterStatus.values:
        qs = qs.filter(status=status)

    if tag.strip():
        qs = qs.filter(tags__name=tag.strip())

    # FTS search (uses GIN index from T13)
    if q.strip():
        search_query = SearchQuery(q.strip(), config="french")
        search_vector = SearchVector("name", weight="A", config="french") + SearchVector(
            "description", weight="B", config="french"
        )
        qs = (
            qs.annotate(rank=SearchRank(search_vector, search_query))
            .filter(rank__gt=0.01)
            .order_by("-rank")
        )

    return qs
