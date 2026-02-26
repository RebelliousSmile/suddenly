"""
Character link services.

Business logic for claim, adopt, and fork workflows.
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    Character,
    CharacterStatus,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
    CharacterLink,
    SharedSequence,
)


class LinkService:
    """
    Service for managing character links (claim, adopt, fork).
    """

    @staticmethod
    def validate_claim(requester, target_character, proposed_character):
        """
        Validate a claim request.
        
        Rules:
        - Target must be an available NPC
        - Proposed character must be a PC owned by requester
        - No pending requests on target
        """
        if target_character.status != CharacterStatus.NPC:
            raise ValidationError(
                f"{target_character.name} n'est plus disponible (statut: {target_character.get_status_display()})"
            )
        
        if not proposed_character:
            raise ValidationError("Un claim nécessite un PJ existant")
        
        if proposed_character.owner != requester:
            raise ValidationError("Vous ne pouvez claim qu'avec un de vos propres PJ")
        
        if proposed_character.status != CharacterStatus.PC:
            raise ValidationError(f"{proposed_character.name} n'est pas un PJ")
        
        # Check for pending requests
        pending = LinkRequest.objects.filter(
            target_character=target_character,
            status=LinkRequestStatus.PENDING
        ).exists()
        
        if pending:
            raise ValidationError(
                f"Une demande est déjà en cours pour {target_character.name}"
            )

    @staticmethod
    def validate_adopt(requester, target_character):
        """
        Validate an adopt request.
        
        Rules:
        - Target must be an available NPC
        - No pending requests on target
        """
        if target_character.status != CharacterStatus.NPC:
            raise ValidationError(
                f"{target_character.name} n'est plus disponible"
            )
        
        pending = LinkRequest.objects.filter(
            target_character=target_character,
            status=LinkRequestStatus.PENDING
        ).exists()
        
        if pending:
            raise ValidationError(
                f"Une demande est déjà en cours pour {target_character.name}"
            )

    @staticmethod
    def validate_fork(requester, target_character):
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
    def create_request(cls, requester, target_character, link_type, message, proposed_character=None):
        """
        Create a link request after validation.
        
        Returns the created LinkRequest.
        """
        # Validate based on type
        if link_type == LinkType.CLAIM:
            cls.validate_claim(requester, target_character, proposed_character)
        elif link_type == LinkType.ADOPT:
            cls.validate_adopt(requester, target_character)
        elif link_type == LinkType.FORK:
            cls.validate_fork(requester, target_character)
        else:
            raise ValidationError(f"Type de lien inconnu: {link_type}")
        
        # Create the request
        request = LinkRequest.objects.create(
            type=link_type,
            requester=requester,
            target_character=target_character,
            proposed_character=proposed_character,
            message=message,
            status=LinkRequestStatus.PENDING,
        )
        
        # TODO: Send notification to target character's creator
        # TODO: Send ActivityPub Offer activity
        
        return request

    @classmethod
    @transaction.atomic
    def accept_request(cls, request, response_message=""):
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
        if request.type == LinkType.CLAIM:
            source = request.proposed_character
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
                CharacterStatus.CLAIMED if request.type == LinkType.CLAIM
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
        
        # TODO: Send ActivityPub Accept activity
        # TODO: Notify both parties
        
        return link

    @classmethod
    def reject_request(cls, request, response_message=""):
        """
        Reject a link request.
        """
        if request.status != LinkRequestStatus.PENDING:
            raise ValidationError("Cette demande n'est plus en attente")
        
        request.status = LinkRequestStatus.REJECTED
        request.response_message = response_message
        request.resolved_at = timezone.now()
        request.save()
        
        # TODO: Send ActivityPub Reject activity
        # TODO: Notify requester
        
        return request

    @classmethod
    def cancel_request(cls, request):
        """
        Cancel a pending request (by requester).
        """
        if request.status != LinkRequestStatus.PENDING:
            raise ValidationError("Cette demande n'est plus en attente")
        
        request.status = LinkRequestStatus.CANCELLED
        request.resolved_at = timezone.now()
        request.save()
        
        return request
