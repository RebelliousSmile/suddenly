"""Tests for the game create/edit form: tags (Mastodon-style) + game_system guard.

Covers:
  - tag normalization (case-insensitive, accent-preserving, deduped) on create/edit
  - visibility default (private unless is_public=on)
  - title requirement
  - game_system near-duplicate confirmation guard (server enforcement)
  - known_game_systems suggestion ordering
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.core.models import Tag
from suddenly.games.models import Game
from suddenly.games.services import known_game_systems, near_duplicate_system
from tests.factories import GameFactory, UserFactory


@pytest.mark.django_db
def test_tag_resolve_names_is_case_insensitive_and_dedupes() -> None:
    """ "Enquête", "enquête" and "  ENQUÊTE " collapse to one lowercased tag."""
    tags = Tag.resolve_names("Enquête, enquête,  ENQUÊTE , Horreur")

    names = sorted(t.name for t in tags)
    assert names == ["enquête", "horreur"]
    assert Tag.objects.filter(name="enquête").count() == 1


@pytest.mark.django_db
def test_game_create_persists_title_visibility_and_tags() -> None:
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("games:create"),
        {
            "title": "City of Mist",
            "description": "",
            "game_system": "Mist Engine",
            "is_public": "on",
            "tags": "Enquête, enquête, Horreur",
        },
    )

    assert response.status_code == 302
    game = Game.objects.get(title="City of Mist")
    assert game.owner == user
    assert game.is_public is True
    assert sorted(game.tags.values_list("name", flat=True)) == ["enquête", "horreur"]


@pytest.mark.django_db
def test_game_create_defaults_to_private_without_is_public() -> None:
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.post(reverse("games:create"), {"title": "Solo Journal"})

    assert response.status_code == 302
    assert Game.objects.get(title="Solo Journal").is_public is False


@pytest.mark.django_db
def test_game_create_requires_title() -> None:
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.post(reverse("games:create"), {"title": "   "})

    assert response.status_code == 200  # re-render, not a redirect
    assert not Game.objects.filter(owner=user).exists()


@pytest.mark.django_db
def test_game_create_blocks_near_duplicate_system_without_confirmation() -> None:
    owner = UserFactory()
    GameFactory(owner=owner, game_system="Appel de Cthulhu")

    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("games:create"),
        {"title": "Ma partie", "game_system": "L'appel de cthulhu"},
    )

    # Re-rendered with the warning; the game is NOT created yet.
    assert response.status_code == 200
    assert response.context["system_warning"] == "Appel de Cthulhu"
    assert not Game.objects.filter(title="Ma partie").exists()


@pytest.mark.django_db
def test_game_create_accepts_near_duplicate_system_once_confirmed() -> None:
    owner = UserFactory()
    GameFactory(owner=owner, game_system="Appel de Cthulhu")

    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("games:create"),
        {
            "title": "Ma partie",
            "game_system": "L'appel de cthulhu",
            "system_confirmed": "1",
        },
    )

    assert response.status_code == 302
    assert Game.objects.get(title="Ma partie").game_system == "L'appel de cthulhu"


@pytest.mark.django_db
def test_game_edit_updates_tags() -> None:
    user = UserFactory()
    game = GameFactory(owner=user, game_system="FATE")
    game.tags.set(Tag.resolve_names("old"))

    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("games:edit", kwargs={"pk": game.pk}),
        {
            "title": game.title,
            "game_system": game.game_system,
            "is_public": "on",
            "tags": "New, new, Fresh",
        },
    )

    assert response.status_code == 302
    game.refresh_from_db()
    assert sorted(game.tags.values_list("name", flat=True)) == ["fresh", "new"]


@pytest.mark.django_db
def test_known_game_systems_orders_by_usage() -> None:
    owner = UserFactory()
    GameFactory(owner=owner, game_system="FATE")
    GameFactory(owner=owner, game_system="FATE")
    GameFactory(owner=owner, game_system="PbtA")

    assert known_game_systems()[:2] == ["FATE", "PbtA"]


def test_near_duplicate_system_is_pure() -> None:
    """Unit check on the shared metric — no DB, mirrors the client JS."""
    known = ["Appel de Cthulhu", "FATE"]
    assert near_duplicate_system("L'appel de cthulhu", known) == "Appel de Cthulhu"
    assert near_duplicate_system("Appel de Cthulhu", known) is None  # exact match
    assert near_duplicate_system("Vampire", known) is None  # not close
