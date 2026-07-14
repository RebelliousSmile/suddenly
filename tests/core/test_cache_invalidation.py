"""
Tests for centralized cache invalidation handlers.

Pattern: pre-populate cache with sentinel, trigger model mutation, assert key cleared.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.cache import cache

from suddenly.activitypub.models import FederatedServer
from suddenly.characters.models import Character
from suddenly.core.cache_invalidation import (
    invalidate_explorer_tags_character,
    invalidate_explorer_tags_game,
)
from suddenly.core.models import Tag
from suddenly.core.services import RECENT_REPORTS_LIMITS
from suddenly.games.models import Game
from tests.factories import (
    CharacterFactory,
    GameFactory,
    ReportFactory,
    UserFactory,
)

SENTINEL = object()


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


@pytest.mark.django_db
def test_character_tag_change_invalidates_explorer_tags() -> None:
    key = f"explorer_tags:{Character._meta.label_lower}"
    cache.set(key, ["sentinel"], 600)
    character: Any = CharacterFactory()  # type: ignore[no-untyped-call]
    tag, _ = Tag.objects.get_or_create(name="combat")

    character.tags.add(tag)

    assert cache.get(key) is None


@pytest.mark.django_db
def test_game_tag_change_invalidates_explorer_tags() -> None:
    key = f"explorer_tags:{Game._meta.label_lower}"
    cache.set(key, ["sentinel"], 600)
    game: Any = GameFactory()  # type: ignore[no-untyped-call]
    tag, _ = Tag.objects.get_or_create(name="oneshot")

    game.tags.add(tag)

    assert cache.get(key) is None


@pytest.mark.django_db
def test_report_save_invalidates_recent_public_reports() -> None:
    keys = [f"recent_public_reports:{n}" for n in RECENT_REPORTS_LIMITS]
    for key in keys:
        cache.set(key, ["sentinel"], 600)

    ReportFactory()  # type: ignore[no-untyped-call]

    for key in keys:
        assert cache.get(key) is None


@pytest.mark.django_db
def test_report_delete_invalidates_recent_public_reports() -> None:
    report: Any = ReportFactory()  # type: ignore[no-untyped-call]
    keys = [f"recent_public_reports:{n}" for n in RECENT_REPORTS_LIMITS]
    for key in keys:
        cache.set(key, ["sentinel"], 600)

    report.delete()

    for key in keys:
        assert cache.get(key) is None


@pytest.mark.django_db
def test_user_save_invalidates_instance_stats() -> None:
    cache.set("instance_stats", {"users": 42}, 600)

    UserFactory()  # type: ignore[no-untyped-call]

    assert cache.get("instance_stats") is None


@pytest.mark.django_db
def test_character_save_invalidates_instance_stats() -> None:
    cache.set("instance_stats", {"characters": 42}, 600)

    CharacterFactory()  # type: ignore[no-untyped-call]

    assert cache.get("instance_stats") is None


@pytest.mark.django_db
def test_federated_server_save_invalidates_instance_stats() -> None:
    cache.set("instance_stats", {"instances": 42}, 600)

    FederatedServer.objects.create(server_name="example.org")

    assert cache.get("instance_stats") is None


@pytest.mark.django_db
def test_m2m_action_filter_skips_pre_add() -> None:
    """pre_add must NOT invalidate — only post_* actions should fire."""
    key = f"explorer_tags:{Character._meta.label_lower}"
    cache.set(key, ["sentinel"], 600)

    invalidate_explorer_tags_character(sender=Character.tags.through, action="pre_add")

    assert cache.get(key) == ["sentinel"]


@pytest.mark.django_db
def test_m2m_action_filter_skips_pre_clear() -> None:
    key = f"explorer_tags:{Game._meta.label_lower}"
    cache.set(key, ["sentinel"], 600)

    invalidate_explorer_tags_game(sender=Game.tags.through, action="pre_clear")

    assert cache.get(key) == ["sentinel"]
