"""#155 — like / recommend buttons surfaced on the scene page (report_detail).

The buttons live on the scene reading page for authenticated viewers, only on a
released (publicly engageable) scene. Anonymous visitors and behind-the-wall
previews get no engagement bar.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from suddenly.games.models import Game, Report, ReportStatus
from suddenly.users.models import User
from tests.factories import GameFactory, UserFactory


def _released(author: User, game: Game) -> Report:
    return Report.objects.create(
        title="A released scene",
        content="Body.",
        game=game,
        author=author,
        status=ReportStatus.PUBLISHED,
        visibility="public",
        remote=False,
        released_at=timezone.now(),
    )


def _detail_url(report: Report) -> str:
    return reverse(
        "games:report_detail", kwargs={"game_pk": str(report.game_id), "pk": str(report.pk)}
    )


@pytest.mark.django_db
def test_authenticated_viewer_sees_like_and_recommend(client: Client) -> None:
    author = UserFactory()
    viewer = UserFactory()
    report = _released(author, GameFactory(owner=author))
    client.force_login(viewer)

    body = client.get(_detail_url(report)).content.decode()
    # Two toggles on the scene page: one like button + one recommend button.
    assert body.count("aria-pressed") == 2
    assert reverse("feed:like") in body
    assert reverse("feed:recommend") in body


@pytest.mark.django_db
def test_anonymous_viewer_gets_no_engagement_bar(client: Client) -> None:
    author = UserFactory()
    report = _released(author, GameFactory(owner=author))

    resp = client.get(_detail_url(report))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert reverse("feed:like") not in body
    assert reverse("feed:recommend") not in body


@pytest.mark.django_db
def test_behind_wall_preview_has_no_engagement_bar(client: Client) -> None:
    """An author previewing a published-but-unreleased scene sees the page but no
    like/recommend bar — the scene is not publicly engageable yet."""
    author = UserFactory()
    unreleased = Report.objects.create(
        title="Behind the wall",
        content="Body.",
        game=GameFactory(owner=author),
        author=author,
        status=ReportStatus.PUBLISHED,
        visibility="public",
        remote=False,
        released_at=None,
    )
    client.force_login(author)

    resp = client.get(_detail_url(unreleased))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert reverse("feed:like") not in body
    assert reverse("feed:recommend") not in body


@pytest.mark.django_db
def test_recommend_button_reflects_existing_state(client: Client, mocker: Any) -> None:
    from suddenly.games.models import Recommendation

    author = UserFactory()
    viewer = UserFactory()
    report = _released(author, GameFactory(owner=author))
    Recommendation.objects.create(user=viewer, report=report)
    client.force_login(viewer)

    body = client.get(_detail_url(report)).content.decode()
    # Already recommended → the recommend button renders pressed on load (state
    # persists). The viewer hasn't liked, so the one pressed toggle is the recommend.
    assert body.count("aria-pressed") == 2
    assert body.count('aria-pressed="true"') == 1
