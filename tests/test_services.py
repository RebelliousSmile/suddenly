"""
Tests for character link services (claim, adopt, fork).
"""

import pytest
from django.core.exceptions import ValidationError

from suddenly.users.models import User
from suddenly.games.models import Game
from suddenly.characters.models import (
    Character, CharacterStatus, LinkRequest, LinkRequestStatus, 
    LinkType, CharacterLink, SharedSequence
)
from suddenly.characters.services import LinkService


class TestLinkServiceValidation:
    """Tests for link request validation."""
    
    def test_claim_requires_available_npc(self, db, user, other_user, game):
        """Cannot claim a character that's not an NPC."""
        target = Character.objects.create(
            name="Already Adopted",
            status=CharacterStatus.ADOPTED,
            creator=user,
            origin_game=game
        )
        
        pc = Character.objects.create(
            name="My PC",
            status=CharacterStatus.PC,
            owner=other_user,
            creator=other_user,
            origin_game=game
        )
        
        with pytest.raises(ValidationError) as exc:
            LinkService.validate_claim(other_user, target, pc)
        
        assert "n'est plus disponible" in str(exc.value)
    
    def test_claim_requires_pc(self, db, user, other_user, character, game):
        """Claim requires an actual PC, not an NPC."""
        npc = Character.objects.create(
            name="Another NPC",
            status=CharacterStatus.NPC,
            creator=other_user,
            origin_game=game
        )
        
        with pytest.raises(ValidationError) as exc:
            LinkService.validate_claim(other_user, character, npc)
        
        assert "n'est pas un PJ" in str(exc.value)
    
    def test_claim_requires_own_pc(self, db, user, other_user, character, game):
        """Can only claim with your own PC."""
        someone_elses_pc = Character.objects.create(
            name="Not Mine",
            status=CharacterStatus.PC,
            owner=user,  # Owned by user, not other_user
            creator=user,
            origin_game=game
        )
        
        with pytest.raises(ValidationError) as exc:
            LinkService.validate_claim(other_user, character, someone_elses_pc)
        
        assert "vos propres PJ" in str(exc.value)
    
    def test_claim_blocked_by_pending_request(self, db, user, other_user, character, game):
        """Cannot claim a character with a pending request."""
        pc = Character.objects.create(
            name="My PC",
            status=CharacterStatus.PC,
            owner=other_user,
            creator=other_user,
            origin_game=game
        )
        
        # Create pending request from someone else
        third_user = User.objects.create_user(
            username="third", email="third@test.com", password="test"
        )
        LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=third_user,
            target_character=character,
            message="I want it"
        )
        
        with pytest.raises(ValidationError) as exc:
            LinkService.validate_claim(other_user, character, pc)
        
        assert "demande est déjà en cours" in str(exc.value)
    
    def test_adopt_requires_available_npc(self, db, user, other_user, game):
        """Cannot adopt a character that's not available."""
        target = Character.objects.create(
            name="Already PC",
            status=CharacterStatus.PC,
            owner=user,
            creator=user,
            origin_game=game
        )
        
        with pytest.raises(ValidationError) as exc:
            LinkService.validate_adopt(other_user, target)
        
        assert "n'est plus disponible" in str(exc.value)
    
    def test_adopt_blocked_by_pending_request(self, db, user, other_user, character, game):
        """Cannot adopt a character with an existing pending request."""
        third_user = User.objects.create_user(
            username="third", email="third@test.com", password="test"
        )
        LinkRequest.objects.create(
            type=LinkType.CLAIM,
            requester=third_user,
            target_character=character,
            message="I want it first"
        )

        with pytest.raises(ValidationError) as exc:
            LinkService.validate_adopt(other_user, character)

        assert "demande est déjà en cours" in str(exc.value)

    def test_fork_always_valid(self, db, user, other_user, game):
        """Fork can target any character."""
        # Even an already adopted character can be forked
        target = Character.objects.create(
            name="Adopted PC",
            status=CharacterStatus.ADOPTED,
            owner=user,
            creator=user,
            origin_game=game
        )
        
        # Should not raise
        LinkService.validate_fork(other_user, target)


class TestLinkServiceCreateRequest:
    """Tests for creating link requests."""
    
    def test_create_claim_request(self, db, user, other_user, character, game):
        """Create a claim request."""
        pc = Character.objects.create(
            name="My PC",
            status=CharacterStatus.PC,
            owner=other_user,
            creator=other_user,
            origin_game=game
        )
        
        request = LinkService.create_request(
            requester=other_user,
            target_character=character,
            link_type=LinkType.CLAIM,
            message="This was my character!",
            proposed_character=pc
        )
        
        assert request.type == LinkType.CLAIM
        assert request.status == LinkRequestStatus.PENDING
        assert request.proposed_character == pc
    
    def test_create_adopt_request(self, db, other_user, character):
        """Create an adopt request."""
        request = LinkService.create_request(
            requester=other_user,
            target_character=character,
            link_type=LinkType.ADOPT,
            message="I want to play this character"
        )
        
        assert request.type == LinkType.ADOPT
        assert request.proposed_character is None
    
    def test_create_fork_request(self, db, other_user, character):
        """Create a fork request."""
        request = LinkService.create_request(
            requester=other_user,
            target_character=character,
            link_type=LinkType.FORK,
            message="I want to create a sibling"
        )
        
        assert request.type == LinkType.FORK


class TestLinkServiceAccept:
    """Tests for accepting link requests."""
    
    def test_accept_claim_creates_link(self, db, user, other_user, character, game):
        """Accepting a claim creates a link and updates statuses."""
        pc = Character.objects.create(
            name="Claimer PC",
            status=CharacterStatus.PC,
            owner=other_user,
            creator=other_user,
            origin_game=game
        )
        
        request = LinkRequest.objects.create(
            type=LinkType.CLAIM,
            requester=other_user,
            target_character=character,
            proposed_character=pc,
            message="Claim!"
        )
        
        link = LinkService.accept_request(request, "Approved!")
        
        # Refresh from DB
        request.refresh_from_db()
        character.refresh_from_db()
        
        assert request.status == LinkRequestStatus.ACCEPTED
        assert character.status == CharacterStatus.CLAIMED
        assert link.source == pc
        assert link.target == character
        
        # SharedSequence should be created
        assert SharedSequence.objects.filter(link=link).exists()
    
    def test_accept_adopt_transfers_ownership(self, db, user, other_user, character, game):
        """Accepting an adopt transfers ownership."""
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other_user,
            target_character=character,
            message="I'll adopt!"
        )
        
        link = LinkService.accept_request(request)
        
        character.refresh_from_db()
        
        assert character.status == CharacterStatus.ADOPTED
        assert character.owner == other_user
    
    def test_accept_fork_creates_new_character(self, db, user, other_user, character, game):
        """Accepting a fork creates a new derived character."""
        request = LinkRequest.objects.create(
            type=LinkType.FORK,
            requester=other_user,
            target_character=character,
            message="Forking!"
        )
        
        initial_count = Character.objects.count()
        link = LinkService.accept_request(request)
        
        # New character created
        assert Character.objects.count() == initial_count + 1
        
        # The new character is linked to original
        assert link.source.parent == character
        assert link.source.owner == other_user
        assert link.source.status == CharacterStatus.PC
    
    def test_cannot_accept_non_pending(self, db, other_user, character):
        """Cannot accept an already resolved request."""
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other_user,
            target_character=character,
            status=LinkRequestStatus.REJECTED,
            message="Rejected one"
        )
        
        with pytest.raises(ValidationError) as exc:
            LinkService.accept_request(request)
        
        assert "n'est plus en attente" in str(exc.value)


class TestLinkServiceReject:
    """Tests for rejecting link requests."""
    
    def test_reject_request(self, db, other_user, character):
        """Reject a request."""
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other_user,
            target_character=character,
            message="Please?"
        )
        
        result = LinkService.reject_request(request, "Not a good fit")
        
        assert result.status == LinkRequestStatus.REJECTED
        assert result.response_message == "Not a good fit"
        assert result.resolved_at is not None
    
    def test_cannot_reject_non_pending(self, db, other_user, character):
        """Cannot reject an already resolved request."""
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other_user,
            target_character=character,
            status=LinkRequestStatus.ACCEPTED,
            message="Already accepted"
        )
        
        with pytest.raises(ValidationError):
            LinkService.reject_request(request)


class TestLinkServiceCancel:
    """Tests for canceling link requests."""
    
    def test_cancel_request(self, db, other_user, character):
        """Cancel own request."""
        request = LinkRequest.objects.create(
            type=LinkType.FORK,
            requester=other_user,
            target_character=character,
            message="Changed my mind"
        )
        
        result = LinkService.cancel_request(request)
        
        assert result.status == LinkRequestStatus.CANCELLED
        assert result.resolved_at is not None
