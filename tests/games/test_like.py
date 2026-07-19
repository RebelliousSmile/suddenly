"""Tests for the scene Like feature (#138, part 1) — toggle, uniqueness,
initial annotated state, and N+1 absence on the feed."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from suddenly.games.models import Game, Like, Rapport, RapportKind, Report, ReportStatus
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
    """A published, public, local scene — the shape the feeds surface."""
    return Report.objects.create(
        title=title,
        content="Scene body.",
        game=game,
        author=author,
        status=ReportStatus.PUBLISHED,
        visibility="public",
        remote=False,
    )


def _published_with_rapport(author: User, game: Game, i: int) -> Report:
    report = _published(author, game, title=f"Scene {i}")
    # NARRATION takes no actor — keeps the fixture free of Character setup.
    Rapport.objects.create(report=report, kind=RapportKind.NARRATION, content=f"Beat {i}.")
    return report


class TestLikeModel:
    def test_duplicate_like_raises_integrity_error(self, db: Any, user: User, game: Game) -> None:
        report = _published(user, game)
        Like.objects.create(user=user, report=report)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Like.objects.create(user=user, report=report)

    def test_same_report_liked_by_two_users_is_allowed(
        self, db: Any, user: User, other_user: User, game: Game
    ) -> None:
        report = _published(user, game)
        Like.objects.create(user=user, report=report)
        Like.objects.create(user=other_user, report=report)
        assert Like.objects.filter(report=report).count() == 2


class TestLikeToggleView:
    def test_toggle_creates_then_deletes(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        report = _published(user, game)
        client.force_login(user)
        url = reverse("feed:like")

        r1 = client.post(url, {"report_id": str(report.pk)})
        assert r1.status_code == 200
        assert Like.objects.filter(user=user, report=report).exists()
        assert 'aria-pressed="true"' in r1.content.decode()

        r2 = client.post(url, {"report_id": str(report.pk)})
        assert r2.status_code == 200
        assert not Like.objects.filter(user=user, report=report).exists()
        assert 'aria-pressed="false"' in r2.content.decode()

    def test_get_is_not_allowed(self, db: Any, client: Client, user: User) -> None:
        client.force_login(user)
        assert client.get(reverse("feed:like")).status_code == 405

    def test_anonymous_post_redirects_to_login(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        report = _published(user, game)
        resp = client.post(reverse("feed:like"), {"report_id": str(report.pk)})
        assert resp.status_code == 302
        assert not Like.objects.exists()

    def test_nonexistent_report_returns_404(self, db: Any, client: Client, user: User) -> None:
        client.force_login(user)
        resp = client.post(reverse("feed:like"), {"report_id": str(uuid.uuid4())})
        assert resp.status_code == 404

    def test_invalid_report_id_returns_404_not_500(
        self, db: Any, client: Client, user: User
    ) -> None:
        client.force_login(user)
        resp = client.post(reverse("feed:like"), {"report_id": "not-a-uuid"})
        assert resp.status_code == 404

    def test_draft_report_cannot_be_liked(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        draft = Report.objects.create(
            title="Draft", content="x", game=game, author=user, status=ReportStatus.DRAFT
        )
        client.force_login(user)
        resp = client.post(reverse("feed:like"), {"report_id": str(draft.pk)})
        assert resp.status_code == 404
        assert not Like.objects.exists()


class TestFeedInitialState:
    def test_feed_reflects_liked_state(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        liked = _published(user, game, title="Liked one")
        _published(user, game, title="Cold one")
        Like.objects.create(user=user, report=liked)
        client.force_login(user)

        body = client.get(reverse("feed:instance")).content.decode()
        # Both states rendered from the annotation, no per-card query.
        assert 'aria-pressed="true"' in body
        assert 'aria-pressed="false"' in body

    def test_anonymous_feed_renders_unliked_without_annotation(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        _published(user, game)
        resp = client.get(reverse("feed:instance"))
        assert resp.status_code == 200
        body = resp.content.decode()
        assert 'aria-pressed="false"' in body
        assert 'aria-pressed="true"' not in body

    def test_liked_annotation_has_no_n_plus_1(
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
            "the `liked` state is not annotated — N+1 in the feed loop"
        )
