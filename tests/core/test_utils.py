"""
Tests for suddenly.core.utils actor-type resolution helpers.
"""

from __future__ import annotations

import pytest

from suddenly.characters.models import Character
from suddenly.core.utils import actor_model_for, content_type_for_actor, get_local_actor
from suddenly.games.models import Game
from suddenly.users.models import User
from tests.factories import CharacterFactory, GameFactory, UserFactory


@pytest.mark.django_db
class TestActorModelFor:
    @pytest.mark.parametrize(
        ("type_key", "expected_model"),
        [
            ("user", User),
            ("User", User),
            ("USER", User),
            ("game", Game),
            ("Game", Game),
            ("character", Character),
            ("Character", Character),
        ],
    )
    def test_resolves_known_keys_any_casing(self, type_key: str, expected_model: type) -> None:
        assert actor_model_for(type_key) is expected_model

    def test_unknown_key_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown actor type"):
            actor_model_for("report")


@pytest.mark.django_db
class TestContentTypeForActor:
    @pytest.mark.parametrize(
        ("type_key", "expected_model"),
        [
            ("user", User),
            ("game", Game),
            ("character", Character),
        ],
    )
    def test_resolves_known_keys(self, type_key: str, expected_model: type) -> None:
        from django.contrib.contenttypes.models import ContentType

        assert content_type_for_actor(type_key) == ContentType.objects.get_for_model(expected_model)

    def test_unknown_key_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown actor type"):
            content_type_for_actor("report")


@pytest.mark.django_db
class TestGetLocalActor:
    def test_finds_local_user_by_username(self) -> None:
        user = UserFactory(remote=False)
        assert get_local_actor("user", user.username) == user

    def test_finds_local_game_by_id(self) -> None:
        game = GameFactory(remote=False)
        assert get_local_actor("game", str(game.pk)) == game

    def test_finds_local_character_by_id(self) -> None:
        character = CharacterFactory(remote=False)
        assert get_local_actor("character", str(character.pk)) == character

    def test_excludes_remote_actor(self) -> None:
        user = UserFactory(remote=True, ap_id="https://remote.example/users/alice")
        assert get_local_actor("user", user.username) is None

    def test_missing_actor_returns_none(self) -> None:
        assert get_local_actor("user", "does-not-exist") is None

    def test_unknown_type_returns_none(self) -> None:
        assert get_local_actor("report", "anything") is None
