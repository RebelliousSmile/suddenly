"""Tests for the scene lifecycle dock: draft → closed → released, + closure kind."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from suddenly.games.models import (
    Rapport,
    RapportKind,
    ReportStatus,
    ReportVisibility,
)
from suddenly.games.services import close_scene, move_rapport, reopen_scene
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


def _beats(report, n):
    """n narration rapports in explicit order 0..n-1."""
    return [
        Rapport.objects.create(
            report=report, kind=RapportKind.NARRATION, content=f"beat-{i}", order=i
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# close_scene / reopen_scene (service)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_close_scene_publishes() -> None:
    user = UserFactory()
    report = ReportFactory(author=user, status=ReportStatus.DRAFT)
    close_scene(report=report, user=user)
    report.refresh_from_db()
    assert report.status == ReportStatus.PUBLISHED
    assert report.released_at is None  # closed, not shared


@pytest.mark.django_db
def test_close_scene_with_closure_writes_compte_rendu() -> None:
    user = UserFactory()
    report = ReportFactory(author=user, status=ReportStatus.DRAFT)
    close_scene(report=report, user=user, closure_content="Et la ville se tut.")
    closure = Rapport.objects.get(report=report, kind=RapportKind.CLOSURE)
    assert closure.content == "Et la ville se tut."
    report.refresh_from_db()
    assert report.status == ReportStatus.PUBLISHED


@pytest.mark.django_db
def test_close_and_release_crosses_the_wall() -> None:
    user = UserFactory()
    report = ReportFactory(author=user, status=ReportStatus.DRAFT)
    close_scene(report=report, user=user, release=True)
    report.refresh_from_db()
    assert report.status == ReportStatus.PUBLISHED
    assert report.released_at is not None


@pytest.mark.django_db
def test_reopen_scene_back_to_draft() -> None:
    report = ReportFactory(status=ReportStatus.PUBLISHED, released_at=None)
    reopen_scene(report=report)
    report.refresh_from_db()
    assert report.status == ReportStatus.DRAFT
    assert report.released_at is None


@pytest.mark.django_db
def test_reopen_federated_released_rejected() -> None:
    report = ReportFactory(
        status=ReportStatus.PUBLISHED,
        released_at=timezone.now(),
        ap_id="https://example.test/reports/1",
    )
    with pytest.raises(ValidationError):
        reopen_scene(report=report)


# ---------------------------------------------------------------------------
# closure kind — no actor (model clean)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_closure_forbids_actor() -> None:
    report = ReportFactory()
    pc = CharacterFactory()
    rapport = Rapport(report=report, kind=RapportKind.CLOSURE, content="x", actor=pc)
    with pytest.raises(ValidationError):
        rapport.clean()


@pytest.mark.django_db
def test_closure_without_actor_valid() -> None:
    report = ReportFactory()
    Rapport(report=report, kind=RapportKind.CLOSURE, content="Fin.").clean()  # must not raise


# ---------------------------------------------------------------------------
# Endpoints + dock
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_scene_close_endpoint_by_author(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user, status=ReportStatus.DRAFT)

    client.force_login(user)
    url = reverse("games:scene_close", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(url, {"mode": "release", "closure": "Rideau."})

    assert resp.status_code == 302
    report.refresh_from_db()
    assert report.status == ReportStatus.PUBLISHED
    assert report.released_at is not None
    assert Rapport.objects.filter(report=report, kind=RapportKind.CLOSURE).exists()


@pytest.mark.django_db
def test_scene_close_non_author_404(client: Client) -> None:
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author, status=ReportStatus.DRAFT)

    client.force_login(intruder)
    url = reverse("games:scene_close", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(url, {})
    assert resp.status_code == 404
    report.refresh_from_db()
    assert report.status == ReportStatus.DRAFT


@pytest.mark.django_db
def test_scene_edit_dock_shows_state(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(
        game=game,
        author=user,
        status=ReportStatus.PUBLISHED,
        released_at=None,
        visibility=ReportVisibility.PUBLIC,
    )
    client.force_login(user)
    resp = client.get(reverse("games:report_edit", kwargs={"game_pk": game.pk, "pk": report.pk}))
    assert resp.status_code == 200
    # Closed phase → Reopen + Share affordances.
    assert (
        reverse("games:scene_reopen", kwargs={"game_pk": game.pk, "pk": report.pk}).encode()
        in resp.content
    )
    assert (
        reverse("games:report_release", kwargs={"game_pk": game.pk, "pk": report.pk}).encode()
        in resp.content
    )


# ---------------------------------------------------------------------------
# Rapport reordering + cast box (#4)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_move_rapport_up_renumbers() -> None:
    report = ReportFactory()
    a, b, c = _beats(report, 3)
    move_rapport(report=report, rapport=c, direction="up")
    order = list(report.rapports.values_list("content", flat=True))
    assert order == ["beat-0", "beat-2", "beat-1"]


@pytest.mark.django_db
def test_move_rapport_at_edge_is_noop() -> None:
    report = ReportFactory()
    a, b = _beats(report, 2)
    move_rapport(report=report, rapport=a, direction="up")  # already first
    assert list(report.rapports.values_list("content", flat=True)) == ["beat-0", "beat-1"]


@pytest.mark.django_db
def test_rapport_move_endpoint_reorders(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user, status=ReportStatus.DRAFT)
    a, b = _beats(report, 2)

    client.force_login(user)
    url = reverse(
        "games:rapport_move",
        kwargs={"game_pk": game.pk, "pk": report.pk, "rapport_pk": b.pk},
    )
    resp = client.post(url, {"direction": "up"}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert list(report.rapports.values_list("content", flat=True)) == ["beat-1", "beat-0"]


@pytest.mark.django_db
def test_rapport_move_frozen_when_released(client: Client) -> None:
    from django.utils import timezone as tz

    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(
        game=game, author=user, status=ReportStatus.PUBLISHED, released_at=tz.now()
    )
    a, b = _beats(report, 2)

    client.force_login(user)
    url = reverse(
        "games:rapport_move",
        kwargs={"game_pk": game.pk, "pk": report.pk, "rapport_pk": b.pk},
    )
    resp = client.post(url, {"direction": "up"}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 400
    assert list(report.rapports.values_list("content", flat=True)) == ["beat-0", "beat-1"]


@pytest.mark.django_db
def test_new_post_appends_at_end() -> None:
    from suddenly.games.services import create_scene_post

    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    _beats(report, 2)  # order 0,1
    rapport = create_scene_post(report=report, kind=RapportKind.NARRATION, content="last")
    assert rapport.order == 2
    assert list(report.rapports.values_list("content", flat=True)) == ["beat-0", "beat-1", "last"]


@pytest.mark.django_db
def test_scene_edit_shows_cast_box(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    npc = CharacterFactory(name="Le-Passeur", origin_game=game)
    Rapport.objects.create(
        report=report, kind=RapportKind.DISCUSSION, content="Hail", actor=npc, order=0
    )

    client.force_login(user)
    resp = client.get(reverse("games:report_edit", kwargs={"game_pk": game.pk, "pk": report.pk}))
    assert resp.status_code == 200
    # The cast box lists the character who spoke.
    assert b"Le-Passeur" in resp.content
