"""Scene editor — the fil renders every rapport; the sidebar composer edits them."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.games.models import Rapport, RapportKind, RapportStatus, ReportStatus
from tests.factories import GameFactory, ReportFactory, UserFactory


@pytest.mark.django_db
def test_editor_fil_shows_all_rapports(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author, status=ReportStatus.PUBLISHED)
    for i, c in enumerate(["AAA-BEAT", "BBB-BEAT", "CCC-BEAT"]):
        Rapport.objects.create(
            report=report,
            kind=RapportKind.NARRATION,
            content=c,
            status=RapportStatus.PUBLISHED,
            order=i,
        )

    client.force_login(author)
    url = reverse("games:report_edit", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.get(url)

    assert resp.status_code == 200
    body = resp.content.decode()
    assert "AAA-BEAT" in body
    assert "BBB-BEAT" in body
    assert "CCC-BEAT" in body


# ---------------------------------------------------------------------------
# Composer edit mode — the Edit button reopens the sidebar composer hydrated
# ---------------------------------------------------------------------------


def _scene_with_post() -> tuple[object, object, object]:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author, status=ReportStatus.PUBLISHED)
    rapport = Rapport.objects.create(
        report=report,
        kind=RapportKind.NARRATION,
        content="EDIT-ME-BEAT",
        status=RapportStatus.PUBLISHED,
        order=0,
    )
    return author, report, rapport


@pytest.mark.django_db
def test_edit_button_loads_composer_in_edit_mode(client: Client) -> None:
    author, report, rapport = _scene_with_post()
    client.force_login(author)
    url = reverse(
        "games:rapport_edit",
        kwargs={"game_pk": report.game.pk, "pk": report.pk, "rapport_pk": rapport.pk},
    )

    resp = client.get(url, HTTP_HX_REQUEST="true")

    assert resp.status_code == 200
    body = resp.content.decode()
    # The composer comes back hydrated on the post…
    assert "EDIT-ME-BEAT" in body
    assert "Modification d&#x27;un post" in body or "Modification d'un post" in body
    # …and its send posts back to rapport_edit (Enregistrer), not scene_post_create.
    assert "Enregistrer" in body


@pytest.mark.django_db
def test_composer_edit_cancel_returns_fresh_composer(client: Client) -> None:
    author, report, rapport = _scene_with_post()
    client.force_login(author)
    url = reverse(
        "games:rapport_edit",
        kwargs={"game_pk": report.game.pk, "pk": report.pk, "rapport_pk": rapport.pk},
    )

    resp = client.get(url, {"cancel": "1"}, HTTP_HX_REQUEST="true")

    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Modification d&#x27;un post" not in body and "Modification d'un post" not in body


@pytest.mark.django_db
def test_composer_edit_post_updates_and_swaps_card_oob(client: Client) -> None:
    author, report, rapport = _scene_with_post()
    client.force_login(author)
    url = reverse(
        "games:rapport_edit",
        kwargs={"game_pk": report.game.pk, "pk": report.pk, "rapport_pk": rapport.pk},
    )

    resp = client.post(
        url,
        {"kind": RapportKind.NARRATION, "content": "REWRITTEN-BEAT", "actor": ""},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    rapport.refresh_from_db()
    assert rapport.content == "REWRITTEN-BEAT"
    body = resp.content.decode()
    # Fresh add-mode composer (no edit banner) + the updated card swapped OOB.
    assert f'hx-swap-oob="outerHTML:#rapport-{rapport.pk}"' in body
    assert "REWRITTEN-BEAT" in body
    assert "Modification d&#x27;un post" not in body and "Modification d'un post" not in body
