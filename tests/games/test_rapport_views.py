"""Tests for rapport_create, rapport_edit and rapport_delete views."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.games.models import Rapport, RapportKind
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory  # noqa: F401

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rapport_create_url(game_pk: object, report_pk: object) -> str:
    return reverse(
        "games:rapport_create",
        kwargs={"game_pk": str(game_pk), "pk": str(report_pk)},
    )


def _rapport_edit_url(game_pk: object, report_pk: object, rapport_pk: object) -> str:
    return reverse(
        "games:rapport_edit",
        kwargs={
            "game_pk": str(game_pk),
            "pk": str(report_pk),
            "rapport_pk": str(rapport_pk),
        },
    )


def _rapport_delete_url(game_pk: object, report_pk: object, rapport_pk: object) -> str:
    return reverse(
        "games:rapport_delete",
        kwargs={
            "game_pk": str(game_pk),
            "pk": str(report_pk),
            "rapport_pk": str(rapport_pk),
        },
    )


# ---------------------------------------------------------------------------
# Authentication & authorisation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rapport_create_unauthenticated(client: Client) -> None:
    """GET rapport_create without login → redirect to login page."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    url = _rapport_create_url(game.pk, report.pk)
    response = client.get(url)

    assert response.status_code == 302
    assert "/login/" in response["Location"] or "login" in response["Location"]


@pytest.mark.django_db
def test_rapport_create_non_author_forbidden(client: Client) -> None:
    """POST rapport_create as user who is not the report author → 403."""
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)

    client.force_login(intruder)
    url = _rapport_create_url(game.pk, report.pk)
    response = client.post(
        url,
        data={"kind": RapportKind.DESCRIPTION, "content": "Intrusion!"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_rapport_edit_non_author_forbidden(client: Client) -> None:
    """POST rapport_edit as a non-author → 403 (centralized scene-author gate)."""
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    rapport = Rapport.objects.create(report=report, kind=RapportKind.NARRATION, content="Mine.")

    client.force_login(intruder)
    url = _rapport_edit_url(game.pk, report.pk, rapport.pk)
    response = client.post(url, data={"kind": RapportKind.NARRATION, "content": "Hijack."})

    assert response.status_code == 403
    rapport.refresh_from_db()
    assert rapport.content == "Mine."


@pytest.mark.django_db
def test_rapport_delete_non_author_forbidden(client: Client) -> None:
    """POST rapport_delete as a non-author → 403, the rapport survives."""
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    rapport = Rapport.objects.create(report=report, kind=RapportKind.ACTION, content="Mine.")

    client.force_login(intruder)
    url = _rapport_delete_url(game.pk, report.pk, rapport.pk)
    response = client.post(url)

    assert response.status_code == 403
    assert Rapport.objects.filter(pk=rapport.pk).exists()


# ---------------------------------------------------------------------------
# Successful create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rapport_create_description_success(client: Client) -> None:
    """POST valid description rapport as author → 200, Rapport saved in DB."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    client.force_login(user)
    url = _rapport_create_url(game.pk, report.pk)
    response = client.post(
        url,
        data={"kind": RapportKind.DESCRIPTION, "content": "A vivid scene unfolds."},
    )

    assert response.status_code == 200
    assert Rapport.objects.filter(report=report, kind=RapportKind.DESCRIPTION).exists()


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rapport_create_discussion_without_actor_fails(client: Client) -> None:
    """POST discussion without actor → 422, no Rapport inserted."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    client.force_login(user)
    url = _rapport_create_url(game.pk, report.pk)
    response = client.post(
        url,
        data={"kind": RapportKind.DISCUSSION, "content": "Anyone there?", "actor": ""},
    )

    assert response.status_code == 422
    assert not Rapport.objects.filter(report=report).exists()


# ---------------------------------------------------------------------------
# Form actor queryset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rapport_actor_queryset_filtered_by_game(client: Client) -> None:
    """GET rapport_create: actor field queryset contains only characters from report's game."""
    user = UserFactory()
    game = GameFactory(owner=user)
    other_game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    char_in_game = CharacterFactory(origin_game=game, creator=user)
    CharacterFactory(origin_game=other_game, creator=user)  # must NOT appear

    client.force_login(user)
    url = _rapport_create_url(game.pk, report.pk)
    response = client.get(url)

    assert response.status_code == 200
    form = response.context["form"]
    qs = form.fields["actor"].queryset
    pks = list(qs.values_list("pk", flat=True))
    assert char_in_game.pk in pks
    assert len(pks) == 1


@pytest.mark.django_db
def test_rapport_create_empty_actor_queryset(client: Client) -> None:
    """GET rapport_create when game has no characters → response contains link to game detail."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    # No characters created for this game.

    client.force_login(user)
    url = _rapport_create_url(game.pk, report.pk)
    response = client.get(url)

    assert response.status_code == 200
    game_detail_url = reverse("games:detail", kwargs={"pk": str(game.pk)})
    assert game_detail_url.encode() in response.content


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rapport_delete_removes_object(client: Client) -> None:
    """POST rapport_delete as author → 200 empty response, Rapport deleted from DB."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    rapport = Rapport.objects.create(report=report, kind=RapportKind.ACTION, content="She strikes.")

    client.force_login(user)
    url = _rapport_delete_url(game.pk, report.pk, rapport.pk)
    response = client.post(url)

    assert response.status_code == 200
    assert response.content == b""
    assert not Rapport.objects.filter(pk=rapport.pk).exists()


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rapport_edit_updates_content(client: Client) -> None:
    """POST rapport_edit with new content → 200, Rapport.content updated in DB."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    rapport = Rapport.objects.create(
        report=report, kind=RapportKind.NARRATION, content="Old content."
    )

    client.force_login(user)
    url = _rapport_edit_url(game.pk, report.pk, rapport.pk)
    response = client.post(
        url,
        data={"kind": RapportKind.NARRATION, "content": "New content.", "actor": ""},
    )

    assert response.status_code == 200
    rapport.refresh_from_db()
    assert rapport.content == "New content."
