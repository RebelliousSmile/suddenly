"""
Character services — link workflows and queryset builders.
"""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.db.models.query import QuerySet
from django.utils import timezone

from suddenly.core.models import Notification, NotificationType
from suddenly.users.models import User

from .models import (
    Character,
    CharacterLink,
    CharacterLinkStatus,
    CharacterStatus,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
    SharedSequence,
    SharedSequenceStatus,
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


def build_character_queryset(
    q: str = "",
    status: str = "",
    system: str = "",
    tag: str = "",
) -> QuerySet[Character]:
    """Build filtered character queryset from explicit params."""
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

    if system.strip():
        qs = qs.filter(origin_game__game_system__icontains=system.strip())

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
