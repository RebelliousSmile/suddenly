"""Tests for the scene Recommend feature (#155) — a real persistent toggle,
mirroring Like (#138): uniqueness, initial annotated state, N+1 absence, revert.

Recommend was a stub (fire-and-forget Announce, inert ``<span>``, no revert);
these lock in the toggle semantics that resolve #155.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from suddenly.games.models import (
    Game,
    Rapport,
    RapportKind,
    Recommendation,
    Report,
    ReportStatus,
)
from suddenly.users.models import User


@pytest.fixture(autouse=True)
def _isolated_env(settings: Any) -> Any:
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    cache.clear()
    yield
    cache.clear()


def _published(author: User, game: Game, title: str = "Scene") -> Report:
    """A released, public, local scene — the shape the feeds surface."""
    return Report.objects.create(
        title=title,
        content="Scene body.",
        game=game,
        author=author,
        status=ReportStatus.PUBLISHED,
        visibility="public",
        remote=False,
        released_at=timezone.now(),
    )


def _published_with_rapport(author: User, game: Game, i: int) -> Report:
    report = _published(author, game, title=f"Scene {i}")
    Rapport.objects.create(report=report, kind=RapportKind.NARRATION, content=f"Beat {i}.")
    return report


class TestRecommendationModel:
    def test_duplicate_recommendation_raises_integrity_error(
        self, db: Any, user: User, game: Game
    ) -> None:
        report = _published(user, game)
        Recommendation.objects.create(user=user, report=report)
        with pytest.raises(IntegrityError), transaction.atomic():
            Recommendation.objects.create(user=user, report=report)

    def test_same_report_recommended_by_two_users_is_allowed(
        self, db: Any, user: User, other_user: User, game: Game
    ) -> None:
        report = _published(user, game)
        Recommendation.objects.create(user=user, report=report)
        Recommendation.objects.create(user=other_user, report=report)
        assert Recommendation.objects.filter(report=report).count() == 2


class TestRecommendToggleView:
    def test_toggle_creates_then_deletes(
        self, db: Any, client: Client, user: User, game: Game, mocker: Any
    ) -> None:
        # Broadcast is fire-and-forget — don't hit federation in a unit test.
        mocker.patch("suddenly.activitypub.signals._safe_delay")
        report = _published(user, game)
        client.force_login(user)
        url = reverse("feed:recommend")

        r1 = client.post(url, {"report_id": str(report.pk)})
        assert r1.status_code == 200
        assert Recommendation.objects.filter(user=user, report=report).exists()
        assert 'aria-pressed="true"' in r1.content.decode()

        r2 = client.post(url, {"report_id": str(report.pk)})
        assert r2.status_code == 200
        assert not Recommendation.objects.filter(user=user, report=report).exists()
        # Revert restores an *interactive* button (the #155 bug: it was an inert span).
        body = r2.content.decode()
        assert 'aria-pressed="false"' in body
        assert "hx-post" in body

    def test_get_is_not_allowed(self, db: Any, client: Client, user: User) -> None:
        client.force_login(user)
        assert client.get(reverse("feed:recommend")).status_code == 405

    def test_anonymous_post_redirects_to_login(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        report = _published(user, game)
        resp = client.post(reverse("feed:recommend"), {"report_id": str(report.pk)})
        assert resp.status_code == 302
        assert not Recommendation.objects.exists()

    def test_nonexistent_report_returns_404(self, db: Any, client: Client, user: User) -> None:
        client.force_login(user)
        resp = client.post(reverse("feed:recommend"), {"report_id": str(uuid.uuid4())})
        assert resp.status_code == 404

    def test_invalid_report_id_returns_404_not_500(
        self, db: Any, client: Client, user: User
    ) -> None:
        client.force_login(user)
        resp = client.post(reverse("feed:recommend"), {"report_id": "not-a-uuid"})
        assert resp.status_code == 404

    def test_draft_report_cannot_be_recommended(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        draft = Report.objects.create(
            title="Draft", content="x", game=game, author=user, status=ReportStatus.DRAFT
        )
        client.force_login(user)
        resp = client.post(reverse("feed:recommend"), {"report_id": str(draft.pk)})
        assert resp.status_code == 404
        assert not Recommendation.objects.exists()


class TestFeedInitialState:
    def test_feed_reflects_recommended_state(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        recommended = _published(user, game, title="Boosted one")
        _published(user, game, title="Cold one")
        Recommendation.objects.create(user=user, report=recommended)
        client.force_login(user)

        body = client.get(reverse("feed:instance")).content.decode()
        # 2 scenes × 2 toggles (like + recommend) = 4 aria-pressed. Neither scene is
        # liked, so the single pressed toggle is the recommend on the boosted scene:
        # the `recommended` annotation surfaced and survives reload (#155 revert works).
        assert body.count('aria-pressed="true"') == 1
        assert body.count('aria-pressed="false"') == 3

    def test_recommended_annotation_has_no_n_plus_1(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        client.force_login(user)
        for i in range(3):
            _published_with_rapport(user, game, i)
        with CaptureQueriesContext(connection) as ctx_small:
            client.get(reverse("feed:instance"))

        for i in range(3, 8):
            _published_with_rapport(user, game, i)
        with CaptureQueriesContext(connection) as ctx_large:
            client.get(reverse("feed:instance"))

        assert len(ctx_small) == len(ctx_large), (
            f"query count grew with card count ({len(ctx_small)} → {len(ctx_large)}): "
            "the `recommended` state is not annotated — N+1 in the feed loop"
        )
