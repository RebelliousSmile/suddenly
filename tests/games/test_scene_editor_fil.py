"""Repro: the scene editor's fil must render ALL of the scene's rapports."""

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
