"""
Tests for Suddenly models.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from suddenly.characters.models import (
    Character,
    CharacterLink,
    CharacterStatus,
    Follow,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
    Quote,
    QuoteVisibility,
)
from suddenly.games.models import Game, Report, ReportCast
from suddenly.users.models import User


class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, db: Any) -> None:
        user = User.objects.create_user(
            username="newuser", email="new@example.com", password="testpass"
        )
        assert user.username == "newuser"
        assert user.remote is False
        actor_url = user.actor_url
        assert actor_url is not None
        assert actor_url.endswith("/users/newuser")

    def test_display_name_fallback(self, user: User) -> None:
        assert user.get_display_name() == "Test User"
        user.display_name = ""
        assert user.get_display_name() == "testuser"


class TestGameModel:
    """Tests for Game model."""

    def test_create_game(self, game: Game) -> None:
        assert game.title == "Test Game"
        assert game.is_public is True
        assert game.remote is False

    def test_actor_url(self, game: Game) -> None:
        assert f"/games/{game.id}" in str(game.actor_url)


class TestReportModel:
    """Tests for Report model."""

    def test_create_report(self, report: Report) -> None:
        assert report.status == "draft"
        assert report.published_at is None
        assert report.is_published is False

    def test_publish_report(self, report: Report) -> None:
        report.status = "published"
        report.published_at = timezone.now()
        report.save()

        assert report.is_published is True


class TestReportCastModel:
    """Tests for ReportCast model."""

    def test_cast_with_existing_character(
        self, db: Any, report: Report, character: Character
    ) -> None:
        cast = ReportCast.objects.create(report=report, character=character, role="main")
        assert cast.is_new_character() is False

    def test_cast_with_new_character(self, db: Any, report: Report) -> None:
        cast = ReportCast.objects.create(
            report=report,
            new_character_name="New NPC",
            new_character_description="A brand new NPC",
            role="supporting",
        )
        assert cast.is_new_character() is True


class TestCharacterModel:
    """Tests for Character model."""

    def test_create_npc(self, character: Character) -> None:
        assert character.status == CharacterStatus.NPC
        assert character.is_available is True
        assert character.owner is None

    def test_create_pc(self, pc_character: Character) -> None:
        assert pc_character.status == CharacterStatus.PC
        assert pc_character.is_available is False
        assert pc_character.owner is not None

    def test_actor_url(self, character: Character) -> None:
        assert f"/characters/{character.id}" in str(character.actor_url)

    def test_claimed_is_not_available(self, db: Any, user: User, game: Game) -> None:
        claimed = Character.objects.create(
            name="Claimed", status=CharacterStatus.CLAIMED, creator=user, origin_game=game
        )
        assert claimed.is_available is False

    def test_adopted_is_not_available(self, db: Any, user: User, game: Game) -> None:
        adopted = Character.objects.create(
            name="Adopted", status=CharacterStatus.ADOPTED, creator=user, origin_game=game
        )
        assert adopted.is_available is False

    def test_forked_is_not_available(self, db: Any, user: User, game: Game) -> None:
        forked = Character.objects.create(
            name="Forked", status=CharacterStatus.FORKED, creator=user, origin_game=game
        )
        assert forked.is_available is False


class TestQuoteModel:
    """Tests for Quote model."""

    def test_create_quote(self, db: Any, user: User, character: Character) -> None:
        quote = Quote.objects.create(
            content="I'll be back!",
            character=character,
            author=user,
            visibility=QuoteVisibility.PUBLIC,
        )
        assert "I'll be back" in str(quote)

    def test_ephemeral_quote_expiration(self, db: Any, user: User, character: Character) -> None:
        past = timezone.now() - timedelta(hours=1)
        quote = Quote.objects.create(
            content="Temporary",
            character=character,
            author=user,
            visibility=QuoteVisibility.EPHEMERAL,
            expires_at=past,
        )
        assert quote.is_expired is True

    def test_public_quote_not_expired(self, db: Any, user: User, character: Character) -> None:
        quote = Quote.objects.create(
            content="Permanent", character=character, author=user, visibility=QuoteVisibility.PUBLIC
        )
        assert quote.is_expired is False


class TestLinkRequestModel:
    """Tests for LinkRequest model."""

    def test_create_claim_request(
        self, db: Any, user: User, other_user: User, character: Character, game: Game
    ) -> None:
        # Create a PC for the claim
        pc = Character.objects.create(
            name="Claimer PC",
            status=CharacterStatus.PC,
            owner=other_user,
            creator=other_user,
            origin_game=game,
        )

        request = LinkRequest.objects.create(
            type=LinkType.CLAIM,
            requester=other_user,
            target_character=character,
            proposed_character=pc,
            message="This NPC was actually my PC!",
        )

        assert request.status == LinkRequestStatus.PENDING
        assert request.proposed_character == pc

    def test_create_adopt_request(self, db: Any, other_user: User, character: Character) -> None:
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other_user,
            target_character=character,
            message="I want to adopt this character",
        )

        assert request.type == LinkType.ADOPT
        assert request.proposed_character is None

    def test_create_fork_request(self, db: Any, other_user: User, character: Character) -> None:
        request = LinkRequest.objects.create(
            type=LinkType.FORK,
            requester=other_user,
            target_character=character,
            message="I want to create a sibling of this character",
        )

        assert request.type == LinkType.FORK


class TestCharacterLinkModel:
    """Tests for CharacterLink model."""

    def test_create_link(self, db: Any, character: Character, pc_character: Character) -> None:
        link = CharacterLink.objects.create(
            type=LinkType.CLAIM,
            source=pc_character,
            target=character,
            description="They were the same person all along",
        )

        assert link.source == pc_character
        assert link.target == character


class TestFollowModel:
    """Tests for Follow model."""

    def test_follow_user(self, db: Any, user: User, other_user: User) -> None:
        ct = ContentType.objects.get_for_model(User)
        follow = Follow.objects.create(follower=user, content_type=ct, object_id=other_user.id)

        assert follow.follower == user

    def test_follow_character(self, db: Any, user: User, character: Character) -> None:
        ct = ContentType.objects.get_for_model(Character)
        follow = Follow.objects.create(follower=user, content_type=ct, object_id=character.id)

        assert follow.content_type == ct
