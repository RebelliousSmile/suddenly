"""Tests for the game create/edit form: tags (Mastodon-style) + game_system guard.

Covers:
  - tag normalization (case-insensitive, accent-preserving, deduped) on create/edit
  - visibility default (private unless is_public=on)
  - title requirement
  - game_system near-duplicate confirmation guard (server enforcement)
  - known_game_systems suggestion ordering
"""

from __future__ import annotations

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from suddenly.core.models import Tag
from suddenly.games.models import Game
from suddenly.games.services import (
    known_game_systems,
    near_duplicate_system,
    normalize_system,
)
from tests.factories import GameFactory, UserFactory

# Smallest valid 1x1 GIF — lets ImageField/Pillow accept the upload without a real asset.
SMALL_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04"
    b"\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44"
    b"\x01\x00\x3b"
)


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


# ---------------------------------------------------------------------------
# game_edit — the near-mirror of game_create, largely uncovered.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_game_edit_blocks_near_duplicate_system_without_confirmation() -> None:
    """The near-dup guard exists on edit too — an unconfirmed close label re-renders."""
    owner = UserFactory()
    GameFactory(owner=owner, game_system="Appel de Cthulhu")
    game = GameFactory(owner=owner, game_system="FATE")

    client = Client()
    client.force_login(owner)

    response = client.post(
        reverse("games:edit", kwargs={"pk": game.pk}),
        {"title": game.title, "game_system": "L'appel de cthulhu", "is_public": "on"},
    )

    assert response.status_code == 200
    assert response.context["system_warning"] == "Appel de Cthulhu"
    game.refresh_from_db()
    assert game.game_system == "FATE"  # not persisted yet


@pytest.mark.django_db
def test_game_edit_accepts_near_duplicate_system_once_confirmed() -> None:
    owner = UserFactory()
    GameFactory(owner=owner, game_system="Appel de Cthulhu")
    game = GameFactory(owner=owner, game_system="FATE")

    client = Client()
    client.force_login(owner)

    response = client.post(
        reverse("games:edit", kwargs={"pk": game.pk}),
        {
            "title": game.title,
            "game_system": "L'appel de cthulhu",
            "is_public": "on",
            "system_confirmed": "1",
        },
    )

    assert response.status_code == 302
    game.refresh_from_db()
    assert game.game_system == "L'appel de cthulhu"


@pytest.mark.django_db
def test_game_edit_by_non_owner_returns_404() -> None:
    """Editing is owner-scoped — a non-owner gets 404 and cannot mutate the game."""
    game = GameFactory(title="Keep me")
    intruder = UserFactory()

    client = Client()
    client.force_login(intruder)

    response = client.post(
        reverse("games:edit", kwargs={"pk": game.pk}),
        {"title": "Hijacked"},
    )

    assert response.status_code == 404
    game.refresh_from_db()
    assert game.title == "Keep me"


@pytest.mark.django_db
def test_game_edit_persists_core_fields_and_toggles_visibility_off() -> None:
    user = UserFactory()
    game = GameFactory(
        owner=user,
        title="Old",
        description="old desc",
        game_system="FATE",
        is_public=True,
    )

    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("games:edit", kwargs={"pk": game.pk}),
        {
            "title": "New title",
            "description": "new desc",
            "game_system": "PbtA",
            "started_at": "2023-06-01",
            # no is_public field -> visibility toggles off
        },
    )

    assert response.status_code == 302
    game.refresh_from_db()
    assert game.title == "New title"
    assert game.description == "new desc"
    assert game.game_system == "PbtA"
    assert game.is_public is False
    assert game.started_at == datetime.date(2023, 6, 1)


@pytest.mark.django_db
def test_game_edit_requires_title() -> None:
    user = UserFactory()
    game = GameFactory(owner=user, title="Keep me")

    client = Client()
    client.force_login(user)

    response = client.post(reverse("games:edit", kwargs={"pk": game.pk}), {"title": "  "})

    assert response.status_code == 200  # re-render, not a redirect
    game.refresh_from_db()
    assert game.title == "Keep me"


@pytest.mark.django_db
def test_game_edit_cover_clear_removes_it(settings, tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings.MEDIA_ROOT = str(tmp_path)
    user = UserFactory()
    game = GameFactory(owner=user)
    game.cover = SimpleUploadedFile("cover.gif", SMALL_GIF, content_type="image/gif")
    game.save()
    assert bool(game.cover)

    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("games:edit", kwargs={"pk": game.pk}),
        {"title": game.title, "game_system": game.game_system, "cover-clear": "1"},
    )

    assert response.status_code == 302
    game.refresh_from_db()
    assert not game.cover


@pytest.mark.django_db
def test_game_edit_replaces_cover(settings, tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings.MEDIA_ROOT = str(tmp_path)
    user = UserFactory()
    game = GameFactory(owner=user)
    game.cover = SimpleUploadedFile("old.gif", SMALL_GIF, content_type="image/gif")
    game.save()
    old_name = game.cover.name

    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("games:edit", kwargs={"pk": game.pk}),
        {
            "title": game.title,
            "game_system": game.game_system,
            "cover": SimpleUploadedFile("new.gif", SMALL_GIF, content_type="image/gif"),
        },
    )

    assert response.status_code == 302
    game.refresh_from_db()
    assert bool(game.cover)
    assert game.cover.name != old_name


# ---------------------------------------------------------------------------
# game_create — residual edges (cover, started_at parsing, auth).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_game_create_persists_cover(settings, tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings.MEDIA_ROOT = str(tmp_path)
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("games:create"),
        {
            "title": "With cover",
            "cover": SimpleUploadedFile("c.gif", SMALL_GIF, content_type="image/gif"),
        },
    )

    assert response.status_code == 302
    assert bool(Game.objects.get(title="With cover").cover)


@pytest.mark.django_db
def test_game_create_persists_started_at() -> None:
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("games:create"),
        {"title": "Dated", "started_at": "2024-01-15"},
    )

    assert response.status_code == 302
    assert Game.objects.get(title="Dated").started_at == datetime.date(2024, 1, 15)


@pytest.mark.django_db
def test_game_create_invalid_started_at_is_ignored() -> None:
    """A malformed date must not 500 — it falls back to None."""
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("games:create"),
        {"title": "Bad date", "started_at": "not-a-date"},
    )

    assert response.status_code == 302
    assert Game.objects.get(title="Bad date").started_at is None


@pytest.mark.django_db
def test_game_create_requires_login() -> None:
    """An anonymous POST is redirected by @login_required — no game is created."""
    client = Client()

    response = client.post(reverse("games:create"), {"title": "Anon game"})

    assert response.status_code == 302
    assert not Game.objects.filter(title="Anon game").exists()


# ---------------------------------------------------------------------------
# game_system metric (services) — the crux, mirrored client-side.
# ---------------------------------------------------------------------------


def test_normalize_system_strips_accents_punctuation_and_case() -> None:
    assert normalize_system("L'Appel de Cthulhu") == "l appel de cthulhu"
    assert normalize_system("Écryme !!") == "ecryme"
    assert normalize_system("  FATE   Core  ") == "fate core"


def test_near_duplicate_system_threshold_and_empty_inputs() -> None:
    known = ["Appel de Cthulhu"]
    # One-letter typo on a long label -> above threshold, flagged.
    assert near_duplicate_system("Appel de Cthulou", known) == "Appel de Cthulhu"
    # A short fragment of the label -> below threshold, not flagged.
    assert near_duplicate_system("Cthulhu", known) is None
    # Empty / punctuation-only entries never trigger a warning.
    assert near_duplicate_system("", known) is None
    assert near_duplicate_system("!!!", known) is None


@pytest.mark.django_db
def test_known_game_systems_excludes_empty_and_respects_limit() -> None:
    owner = UserFactory()
    GameFactory(owner=owner, game_system="FATE")
    GameFactory(owner=owner, game_system="")
    GameFactory(owner=owner, game_system="PbtA")

    systems = known_game_systems()
    assert "" not in systems
    assert set(systems) == {"FATE", "PbtA"}
    # Tie on usage (1 each) -> alphabetical; limit caps the list.
    assert known_game_systems(limit=1) == ["FATE"]


# ---------------------------------------------------------------------------
# Tag model — normalization guarantees relied on by the form.
# ---------------------------------------------------------------------------


def test_tag_normalize_name_unifies_nfc_and_collapses_whitespace() -> None:
    # Decomposed (NFD, "e" + combining acute) and composed (NFC) forms collapse to one key.
    decomposed = "café"  # e + U+0301
    composed = "café"  # e-acute
    assert decomposed != composed  # distinct input byte sequences
    assert Tag.normalize_name(decomposed) == Tag.normalize_name(composed) == "café"
    assert Tag.normalize_name("  jeu   de   rôle  ") == "jeu de rôle"


@pytest.mark.django_db
def test_resolve_names_preserves_order_and_drops_empty_parts() -> None:
    tags = Tag.resolve_names("Horreur, , Enquête,,Aventure")

    assert [t.name for t in tags] == ["horreur", "enquête", "aventure"]
