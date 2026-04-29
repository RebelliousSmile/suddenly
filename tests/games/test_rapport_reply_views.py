"""Tests for rapport_reply and rapport_add_remote_parent views."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.games.models import Rapport, RapportKind, RapportLink
from tests.factories import (
    CharacterFactory,
    GameFactory,
    RapportFactory,
    ReportFactory,
    UserFactory,
)

# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def _reply_url(game_pk: object, report_pk: object, rapport_pk: object) -> str:
    return reverse(
        "games:rapport_reply",
        kwargs={
            "game_pk": str(game_pk),
            "pk": str(report_pk),
            "rapport_pk": str(rapport_pk),
        },
    )


def _remote_parent_url(game_pk: object, report_pk: object, rapport_pk: object) -> str:
    return reverse(
        "games:rapport_add_remote_parent",
        kwargs={
            "game_pk": str(game_pk),
            "pk": str(report_pk),
            "rapport_pk": str(rapport_pk),
        },
    )


# ---------------------------------------------------------------------------
# rapport_reply — authentication
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rapport_reply_unauthenticated_redirects(client: Client) -> None:
    """GET rapport_reply without login → 302 redirect to login."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    parent = RapportFactory(report=report)

    url = _reply_url(game.pk, report.pk, parent.pk)
    response = client.get(url)

    assert response.status_code == 302
    assert "login" in response["Location"]


@pytest.mark.django_db
def test_rapport_reply_user_without_character_in_game_forbidden(client: Client) -> None:
    """GET rapport_reply as authenticated user with no character in game → 403."""
    author = UserFactory()
    other_user = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    parent = RapportFactory(report=report)

    # other_user has no character in game
    client.force_login(other_user)
    url = _reply_url(game.pk, report.pk, parent.pk)
    response = client.get(url)

    assert response.status_code == 403


@pytest.mark.django_db
def test_rapport_reply_user_with_character_in_game_gets_form(client: Client) -> None:
    """GET rapport_reply as user with a character in game → 200, form rendered."""
    author = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    parent = RapportFactory(report=report)

    # player has a character originating from this game
    CharacterFactory(creator=player, origin_game=game)

    client.force_login(player)
    url = _reply_url(game.pk, report.pk, parent.pk)
    response = client.get(url)

    assert response.status_code == 200
    assert b"reply-form-slot-" in response.content


@pytest.mark.django_db
def test_rapport_reply_post_valid_creates_rapport_and_link(client: Client) -> None:
    """POST valid reply → 200, child Rapport + RapportLink created in DB."""
    author = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    parent = RapportFactory(report=report)

    CharacterFactory(creator=player, origin_game=game)

    client.force_login(player)
    url = _reply_url(game.pk, report.pk, parent.pk)
    response = client.post(
        url,
        data={"kind": RapportKind.DESCRIPTION, "content": "A child rapport."},
    )

    assert response.status_code == 200
    child = Rapport.objects.filter(report=report, content="A child rapport.").first()
    assert child is not None
    assert RapportLink.objects.filter(rapport=child, parent_rapport=parent).exists()


@pytest.mark.django_db
def test_rapport_reply_post_invalid_no_content_returns_422(client: Client) -> None:
    """POST reply with no content → 422, no Rapport inserted."""
    author = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    parent = RapportFactory(report=report)

    CharacterFactory(creator=player, origin_game=game)
    initial_count = Rapport.objects.filter(report=report).count()

    client.force_login(player)
    url = _reply_url(game.pk, report.pk, parent.pk)
    response = client.post(
        url,
        data={"kind": RapportKind.DESCRIPTION, "content": ""},
    )

    assert response.status_code == 422
    assert Rapport.objects.filter(report=report).count() == initial_count


# ---------------------------------------------------------------------------
# rapport_add_remote_parent
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rapport_add_remote_parent_as_author_creates_link(client: Client) -> None:
    """POST valid IRI as report author → 200, RapportLink with parent_iri created."""
    author = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    rapport = RapportFactory(report=report)

    client.force_login(author)
    url = _remote_parent_url(game.pk, report.pk, rapport.pk)
    response = client.post(url, data={"parent_iri": "https://example.com/rapports/abc"})

    assert response.status_code == 200
    expected_iri = "https://example.com/rapports/abc"
    assert RapportLink.objects.filter(rapport=rapport, parent_iri=expected_iri).exists()


@pytest.mark.django_db
def test_rapport_add_remote_parent_invalid_url_returns_422(client: Client) -> None:
    """POST invalid URL → 422, no RapportLink created."""
    author = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    rapport = RapportFactory(report=report)

    client.force_login(author)
    url = _remote_parent_url(game.pk, report.pk, rapport.pk)
    response = client.post(url, data={"parent_iri": "not-a-url"})

    assert response.status_code == 422
    assert not RapportLink.objects.filter(rapport=rapport).exists()


@pytest.mark.django_db
def test_rapport_add_remote_parent_non_author_forbidden(client: Client) -> None:
    """POST rapport_add_remote_parent as non-author → 403."""
    author = UserFactory()
    other_user = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    rapport = RapportFactory(report=report)

    client.force_login(other_user)
    url = _remote_parent_url(game.pk, report.pk, rapport.pk)
    response = client.post(url, data={"parent_iri": "https://example.com/r/1"})

    assert response.status_code == 403
