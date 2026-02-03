"""
Tests for Suddenly models.
"""

import pytest
from django.utils import timezone

from suddenly.users.models import User
from suddenly.games.models import Game, Report, ReportCast
from suddenly.characters.models import (
    Character, CharacterStatus, Quote, QuoteVisibility,
    CharacterAppearance, LinkRequest, LinkType, LinkRequestStatus,
    CharacterLink, SharedSequence, Follow
)


class TestUserModel:
    """Tests for User model."""
    
    def test_create_user(self, db):
        user = User.objects.create_user(
            username="newuser",
            email="new@example.com",
            password="testpass"
        )
        assert user.username == "newuser"
        assert user.remote is False
        assert user.actor_url.endswith("/users/newuser")
    
    def test_display_name_fallback(self, user):
        assert user.get_display_name() == "Test User"
        user.display_name = ""
        assert user.get_display_name() == "testuser"


class TestGameModel:
    """Tests for Game model."""
    
    def test_create_game(self, game):
        assert game.title == "Test Game"
        assert game.is_public is True
        assert game.remote is False
    
    def test_actor_url(self, game):
        assert f"/games/{game.id}" in game.actor_url


class TestReportModel:
    """Tests for Report model."""
    
    def test_create_report(self, report):
        assert report.status == "draft"
        assert report.published_at is None
        assert report.is_published is False
    
    def test_publish_report(self, report):
        report.status = "published"
        report.published_at = timezone.now()
        report.save()
        
        assert report.is_published is True


class TestReportCastModel:
    """Tests for ReportCast model."""
    
    def test_cast_with_existing_character(self, db, report, character):
        cast = ReportCast.objects.create(
            report=report,
            character=character,
            role="main"
        )
        assert cast.is_new_character() is False
    
    def test_cast_with_new_character(self, db, report):
        cast = ReportCast.objects.create(
            report=report,
            new_character_name="New NPC",
            new_character_description="A brand new NPC",
            role="supporting"
        )
        assert cast.is_new_character() is True


class TestCharacterModel:
    """Tests for Character model."""
    
    def test_create_npc(self, character):
        assert character.status == CharacterStatus.NPC
        assert character.is_available is True
        assert character.owner is None
    
    def test_create_pc(self, pc_character):
        assert pc_character.status == CharacterStatus.PC
        assert pc_character.is_available is False
        assert pc_character.owner is not None
    
    def test_actor_url(self, character):
        assert f"/characters/{character.id}" in character.actor_url


class TestQuoteModel:
    """Tests for Quote model."""
    
    def test_create_quote(self, db, user, character):
        quote = Quote.objects.create(
            content="I'll be back!",
            character=character,
            author=user,
            visibility=QuoteVisibility.PUBLIC
        )
        assert "I'll be back" in str(quote)
    
    def test_ephemeral_quote_expiration(self, db, user, character):
        past = timezone.now() - timezone.timedelta(hours=1)
        quote = Quote.objects.create(
            content="Temporary",
            character=character,
            author=user,
            visibility=QuoteVisibility.EPHEMERAL,
            expires_at=past
        )
        assert quote.is_expired is True
    
    def test_public_quote_not_expired(self, db, user, character):
        quote = Quote.objects.create(
            content="Permanent",
            character=character,
            author=user,
            visibility=QuoteVisibility.PUBLIC
        )
        assert quote.is_expired is False


class TestLinkRequestModel:
    """Tests for LinkRequest model."""
    
    def test_create_claim_request(self, db, user, other_user, character, game):
        # Create a PC for the claim
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
            message="This NPC was actually my PC!"
        )
        
        assert request.status == LinkRequestStatus.PENDING
        assert request.proposed_character == pc
    
    def test_create_adopt_request(self, db, other_user, character):
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other_user,
            target_character=character,
            message="I want to adopt this character"
        )
        
        assert request.type == LinkType.ADOPT
        assert request.proposed_character is None
    
    def test_create_fork_request(self, db, other_user, character):
        request = LinkRequest.objects.create(
            type=LinkType.FORK,
            requester=other_user,
            target_character=character,
            message="I want to create a sibling of this character"
        )
        
        assert request.type == LinkType.FORK


class TestCharacterLinkModel:
    """Tests for CharacterLink model."""
    
    def test_create_link(self, db, character, pc_character):
        link = CharacterLink.objects.create(
            type=LinkType.CLAIM,
            source=pc_character,
            target=character,
            description="They were the same person all along"
        )
        
        assert link.source == pc_character
        assert link.target == character


class TestFollowModel:
    """Tests for Follow model."""
    
    def test_follow_user(self, db, user, other_user):
        follow = Follow.objects.create(
            follower=user,
            target_type="user",
            target_id=other_user.id
        )
        
        assert follow.follower == user
    
    def test_follow_character(self, db, user, character):
        follow = Follow.objects.create(
            follower=user,
            target_type="character",
            target_id=character.id
        )
        
        assert follow.target_type == "character"
