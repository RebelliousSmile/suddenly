"""Tests for the popular-scenes wall (#146) — the most-liked released scenes,
substitute for the retired citations wall.

Covers the ranking queryset (order, zero-like threshold, wall), the public
surface (anonymous 200, liked annotation, no N+1) and the infinite-scroll
sentinel pagination.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.cache import cache
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from suddenly.games.models import (
    Like,
    Rapport,
    RapportKind,
    Report,
    ReportStatus,
    ReportVisibility,
)
from suddenly.users.models import User
from tests.factories import ReportFactory, UserFactory


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


def _released(title: str = "Scene", **kwargs: Any) -> Report:
    """A released + published + public scene — the shape the wall ranks."""
    return ReportFactory(
        title=title,
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.PUBLIC,
        published_at=timezone.now(),
        released_at=timezone.now(),
        **kwargs,
    )


def _add_likes(report: Report, n: int) -> None:
    """Attach ``n`` likes, one per fresh user (unique_user_report_like)."""
    for _ in range(n):
        Like.objects.create(user=UserFactory(), report=report)


def _with_rapport(report: Report, i: int) -> Report:
    # NARRATION takes no actor — keeps the prefetch exercised without Character setup.
    Rapport.objects.create(report=report, kind=RapportKind.NARRATION, content=f"Beat {i}.")
    return report


# ---------------------------------------------------------------------------
# most_liked() — ranking queryset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_most_liked_orders_by_count_desc() -> None:
    one, three, two = _released("ONE"), _released("THREE"), _released("TWO")
    _add_likes(one, 1)
    _add_likes(three, 3)
    _add_likes(two, 2)

    ranked = list(Report.objects.most_liked())

    assert ranked == [three, two, one]
    assert ranked[0].like_count == 3  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_most_liked_excludes_zero_like_scene() -> None:
    cold = _released("COLD")
    assert cold not in Report.objects.most_liked()


@pytest.mark.django_db
def test_most_liked_excludes_unreleased_local_scene() -> None:
    """Local wall closed → even a heavily liked local scene does not rise."""
    walled = ReportFactory(
        title="WALLED",
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.PUBLIC,
        published_at=timezone.now(),
        released_at=None,
    )
    _add_likes(walled, 5)
    assert walled not in Report.objects.most_liked()


@pytest.mark.django_db
def test_most_liked_includes_liked_remote_scene() -> None:
    """Listing surface → remote-tolerant (feed_visible, not released).

    A remote scene never gets a local ``released_at``; ``released()`` would drop
    it. Since liking a remote scene is a first-class federated action (#138), a
    liked remote scene must surface on the popular wall.
    """
    remote = ReportFactory(
        title="REMOTE",
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.PUBLIC,
        published_at=timezone.now(),
        released_at=None,
        remote=True,
    )
    _add_likes(remote, 2)
    assert remote in Report.objects.most_liked()


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wall_200_anonymous(client: Client) -> None:
    liked = _released("HOT")
    _add_likes(liked, 2)
    resp = client.get(reverse("core:popular_scenes"))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "HOT" in body
    # Anonymous → no `liked` annotation → every like button reads unpressed.
    assert 'aria-pressed="true"' not in body
    assert 'aria-pressed="false"' in body


@pytest.mark.django_db
def test_wall_ranks_hottest_first(client: Client) -> None:
    for title, n in (("ONE", 1), ("THREE", 3), ("TWO", 2)):
        _add_likes(_released(title), n)

    body = client.get(reverse("core:popular_scenes")).content.decode()

    assert body.index("THREE") < body.index("TWO") < body.index("ONE")


@pytest.mark.django_db
def test_wall_excludes_zero_like_and_unreleased(client: Client) -> None:
    _add_likes(_released("SHOWN"), 1)
    _released("COLD")  # released but zero likes
    walled = ReportFactory(
        title="WALLED",
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.PUBLIC,
        published_at=timezone.now(),
        released_at=None,
    )
    _add_likes(walled, 3)

    body = client.get(reverse("core:popular_scenes")).content.decode()

    assert "SHOWN" in body
    assert "COLD" not in body
    assert "WALLED" not in body


@pytest.mark.django_db
def test_wall_shows_liked_state_for_authenticated(client: Client) -> None:
    viewer: User = UserFactory()
    scene = _released("MINE")
    Like.objects.create(user=viewer, report=scene)
    client.force_login(viewer)

    body = client.get(reverse("core:popular_scenes")).content.decode()

    # The viewer's own like is annotated → the button reads pressed.
    assert 'aria-pressed="true"' in body


@pytest.mark.django_db
def test_wall_has_no_n_plus_1(client: Client) -> None:
    for i in range(3):
        _add_likes(_with_rapport(_released(f"S{i}"), i), 1)
    with CaptureQueriesContext(connection) as small:
        client.get(reverse("core:popular_scenes"))

    for i in range(3, 8):
        _add_likes(_with_rapport(_released(f"S{i}"), i), 1)
    with CaptureQueriesContext(connection) as large:
        client.get(reverse("core:popular_scenes"))

    assert len(small) == len(large), (
        f"query count grew with card count ({len(small)} → {len(large)}): "
        "like count or liked state is not annotated — N+1 in the wall"
    )


# ---------------------------------------------------------------------------
# Infinite scroll — sentinel pagination
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_infinite_scroll_sentinel_paginates(client: Client) -> None:
    # One liker likes 21 scenes → 21 rows over the ≥1 threshold, 20 per page.
    liker: User = UserFactory()
    for i in range(21):
        Like.objects.create(
            user=liker,
            report=_released(f"Scene {i}"),
        )

    url = reverse("core:popular_scenes")
    page1 = client.get(url)
    b1 = page1.content.decode()
    # Full page: 20 cards + a sentinel pointing at page 2.
    assert b1.count("aria-pressed") == 20
    assert 'hx-get="?page=2"' in b1

    page2 = client.get(url, {"page": "2"}, HTTP_HX_REQUEST="true")
    b2 = page2.content.decode()
    # HTMX request → items partial alone (no base layout), last card, no sentinel.
    assert "<!DOCTYPE" not in b2 and "<html" not in b2
    assert b2.count("aria-pressed") == 1
    assert 'hx-get="?page=3"' not in b2
