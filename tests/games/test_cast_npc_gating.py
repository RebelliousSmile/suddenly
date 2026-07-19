"""Only the game master may introduce a brand-new NPC via the cast.

Covers both entry points that write a ``ReportCast`` with ``new_character_name``:
the HTMX ``cast_add`` view and the DRF ``report-cast`` action. Adding an existing
character stays open to the scene author.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.games.models import ReportCast, ReportStatus
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


def _cast_add_url(game_pk: object, report_pk: object) -> str:
    return reverse("games:cast_add", kwargs={"game_pk": str(game_pk), "pk": str(report_pk)})


def _api_cast_url(report_pk: object) -> str:
    return reverse("report-cast", kwargs={"pk": str(report_pk)})


# ---------------------------------------------------------------------------
# HTMX cast_add
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cast_add_new_npc_by_non_gm_forbidden(client: Client) -> None:
    """A non-GM author cannot create a new NPC through the cast → 403, no row."""
    gm = UserFactory()
    author = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=author, status=ReportStatus.DRAFT)

    client.force_login(author)
    response = client.post(
        _cast_add_url(game.pk, report.pk),
        data={"new_character_name": "Ghost", "role": "mentioned"},
    )

    assert response.status_code == 403
    assert not ReportCast.objects.filter(report=report).exists()


@pytest.mark.django_db
def test_cast_add_new_npc_by_gm_allowed(client: Client) -> None:
    """The GM (also author) may create a new NPC through the cast → row created."""
    gm = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=gm, status=ReportStatus.DRAFT)

    client.force_login(gm)
    response = client.post(
        _cast_add_url(game.pk, report.pk),
        data={"new_character_name": "Ghost", "role": "mentioned"},
    )

    assert response.status_code == 200
    assert ReportCast.objects.filter(report=report, new_character_name="Ghost").exists()


@pytest.mark.django_db
def test_cast_add_existing_character_by_non_gm_allowed(client: Client) -> None:
    """A non-GM author may add an existing character to the cast → row created."""
    gm = UserFactory()
    author = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=author, status=ReportStatus.DRAFT)
    character = CharacterFactory(origin_game=game, creator=gm)

    client.force_login(author)
    response = client.post(
        _cast_add_url(game.pk, report.pk),
        data={"character_slug": character.slug, "role": "mentioned"},
    )

    assert response.status_code == 200
    assert ReportCast.objects.filter(report=report, character=character).exists()


# ---------------------------------------------------------------------------
# DRF report-cast action
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_api_cast_new_npc_by_non_gm_forbidden(client: Client) -> None:
    """A non-GM author cannot create a new NPC via the API → 403, no row."""
    gm = UserFactory()
    author = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=author, status=ReportStatus.DRAFT)

    client.force_login(author)
    response = client.post(_api_cast_url(report.pk), data={"new_character_name": "Ghost"})

    assert response.status_code == 403
    assert not ReportCast.objects.filter(report=report).exists()


@pytest.mark.django_db
def test_api_cast_new_npc_by_gm_allowed(client: Client) -> None:
    """The GM (also author) may create a new NPC via the API → 201, row created."""
    gm = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=gm, status=ReportStatus.DRAFT)

    client.force_login(gm)
    response = client.post(
        _api_cast_url(report.pk),
        data={"new_character_name": "Ghost", "report": str(report.pk), "role": "mentioned"},
    )

    assert response.status_code == 201
    assert ReportCast.objects.filter(report=report, new_character_name="Ghost").exists()
