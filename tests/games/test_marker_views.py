"""Tests for marker_create and marker_delete views."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.games.models import (
    MarkerKind,
    Rapport,
    RapportKind,
    RapportMarker,
)
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory  # noqa: F401

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _marker_create_url(game_pk: object, report_pk: object, rapport_pk: object) -> str:
    return reverse(
        "games:marker_create",
        kwargs={
            "game_pk": str(game_pk),
            "pk": str(report_pk),
            "rapport_pk": str(rapport_pk),
        },
    )


def _marker_delete_url(
    game_pk: object, report_pk: object, rapport_pk: object, marker_pk: object
) -> str:
    return reverse(
        "games:marker_delete",
        kwargs={
            "game_pk": str(game_pk),
            "pk": str(report_pk),
            "rapport_pk": str(rapport_pk),
            "marker_pk": str(marker_pk),
        },
    )


def _make_rapport(user: object, game: object = None, report: object = None) -> Rapport:
    if game is None:
        game = GameFactory(owner=user)
    if report is None:
        report = ReportFactory(game=game, author=user)
    return Rapport.objects.create(report=report, kind=RapportKind.ACTION, content="An action.")


# ---------------------------------------------------------------------------
# marker_create — authentication & authorisation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_marker_create_unauthenticated_redirects(client: Client) -> None:
    """GET marker_create without login → redirect to login."""
    user = UserFactory()
    rapport = _make_rapport(user)
    url = _marker_create_url(rapport.report.game.pk, rapport.report.pk, rapport.pk)

    response = client.get(url)

    assert response.status_code == 302
    assert "login" in response["Location"]


@pytest.mark.django_db
def test_marker_create_non_author_forbidden(client: Client) -> None:
    """POST marker_create as non-author → 403."""
    author = UserFactory()
    intruder = UserFactory()
    rapport = _make_rapport(author)
    url = _marker_create_url(rapport.report.game.pk, rapport.report.pk, rapport.pk)

    client.force_login(intruder)
    response = client.post(url, data={"kind": MarkerKind.START})

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# marker_create — GET
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_marker_create_get_returns_form(client: Client) -> None:
    """GET marker_create as author → 200 with form in context."""
    user = UserFactory()
    rapport = _make_rapport(user)
    url = _marker_create_url(rapport.report.game.pk, rapport.report.pk, rapport.pk)

    client.force_login(user)
    response = client.get(url)

    assert response.status_code == 200
    assert "form" in response.context
    assert "rapport" in response.context


# ---------------------------------------------------------------------------
# marker_create — POST success
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_marker_create_start_success(client: Client) -> None:
    """POST start marker (no character required) → 200, RapportMarker saved."""
    user = UserFactory()
    rapport = _make_rapport(user)
    url = _marker_create_url(rapport.report.game.pk, rapport.report.pk, rapport.pk)

    client.force_login(user)
    response = client.post(url, data={"kind": MarkerKind.START, "character": ""})

    assert response.status_code == 200
    assert RapportMarker.objects.filter(rapport=rapport, kind=MarkerKind.START).exists()


@pytest.mark.django_db
def test_marker_create_character_appears_success(client: Client) -> None:
    """POST character_appears with a valid character → 200, marker saved."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    rapport = _make_rapport(user, game=game, report=report)
    character = CharacterFactory(origin_game=game, creator=user)
    url = _marker_create_url(game.pk, report.pk, rapport.pk)

    client.force_login(user)
    response = client.post(
        url, data={"kind": MarkerKind.CHARACTER_APPEARS, "character": str(character.pk)}
    )

    assert response.status_code == 200
    assert RapportMarker.objects.filter(
        rapport=rapport, kind=MarkerKind.CHARACTER_APPEARS, character=character
    ).exists()


# ---------------------------------------------------------------------------
# marker_create — POST validation failure
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_marker_create_character_appears_without_character_fails(client: Client) -> None:
    """POST character_appears without character → 422, no marker inserted."""
    user = UserFactory()
    rapport = _make_rapport(user)
    url = _marker_create_url(rapport.report.game.pk, rapport.report.pk, rapport.pk)

    client.force_login(user)
    response = client.post(url, data={"kind": MarkerKind.CHARACTER_APPEARS, "character": ""})

    assert response.status_code == 422
    assert not RapportMarker.objects.filter(rapport=rapport).exists()


# ---------------------------------------------------------------------------
# marker_create — character queryset scoped to game
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_marker_create_character_queryset_scoped_to_game(client: Client) -> None:
    """GET marker_create: character field only contains characters from the rapport's game."""
    user = UserFactory()
    game = GameFactory(owner=user)
    other_game = GameFactory(owner=user)
    rapport = _make_rapport(user, game=game)
    char_in_game = CharacterFactory(origin_game=game, creator=user)
    CharacterFactory(origin_game=other_game, creator=user)
    url = _marker_create_url(game.pk, rapport.report.pk, rapport.pk)

    client.force_login(user)
    response = client.get(url)

    assert response.status_code == 200
    qs = response.context["form"].fields["character"].queryset
    pks = list(qs.values_list("pk", flat=True))
    assert char_in_game.pk in pks
    assert len(pks) == 1


# ---------------------------------------------------------------------------
# marker_delete — authentication & authorisation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_marker_delete_unauthenticated_redirects(client: Client) -> None:
    """POST marker_delete without login → redirect to login."""
    user = UserFactory()
    rapport = _make_rapport(user)
    marker = RapportMarker.objects.create(rapport=rapport, kind=MarkerKind.END)
    url = _marker_delete_url(rapport.report.game.pk, rapport.report.pk, rapport.pk, marker.pk)

    response = client.post(url)

    assert response.status_code == 302
    assert "login" in response["Location"]


@pytest.mark.django_db
def test_marker_delete_non_author_forbidden(client: Client) -> None:
    """POST marker_delete as non-author → 403."""
    author = UserFactory()
    intruder = UserFactory()
    rapport = _make_rapport(author)
    marker = RapportMarker.objects.create(rapport=rapport, kind=MarkerKind.ORACLE)
    url = _marker_delete_url(rapport.report.game.pk, rapport.report.pk, rapport.pk, marker.pk)

    client.force_login(intruder)
    response = client.post(url)

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# marker_delete — success
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_marker_delete_removes_marker(client: Client) -> None:
    """POST marker_delete as author → 200 empty response, marker deleted."""
    user = UserFactory()
    rapport = _make_rapport(user)
    marker = RapportMarker.objects.create(rapport=rapport, kind=MarkerKind.END)
    url = _marker_delete_url(rapport.report.game.pk, rapport.report.pk, rapport.pk, marker.pk)

    client.force_login(user)
    response = client.post(url)

    assert response.status_code == 200
    assert response.content == b""
    assert not RapportMarker.objects.filter(pk=marker.pk).exists()
