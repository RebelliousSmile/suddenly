"""Tests for the liberation axis: the temporal wall, Stories, and release.

Covers SUD-V1 (released_at / is_released), SUD-V2 (report_detail wall),
SUD-V3 (stories_index / story_detail) and SUD-V4 (report_release action).
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from suddenly.games.models import (
    Rapport,
    RapportKind,
    RapportStatus,
    Report,
    ReportStatus,
    ReportVisibility,
)
from tests.factories import GameFactory, ReportFactory, UserFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _published(game: object, author: object, *, released: bool = False, **kwargs: object) -> Report:
    """Create a published report, optionally released."""
    return ReportFactory(
        game=game,
        author=author,
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.PUBLIC,
        published_at=timezone.now(),
        released_at=timezone.now() if released else None,
        **kwargs,
    )


def _detail_url(report: Report) -> str:
    kwargs = {"game_pk": str(report.game_id), "pk": str(report.pk)}
    return reverse("games:report_detail", kwargs=kwargs)


def _release_url(report: Report) -> str:
    kwargs = {"game_pk": str(report.game_id), "pk": str(report.pk)}
    return reverse("games:report_release", kwargs=kwargs)


# ---------------------------------------------------------------------------
# SUD-V1 — model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_is_released_defaults_false() -> None:
    report = ReportFactory()
    assert report.is_released is False


@pytest.mark.django_db
def test_is_released_true_when_dated() -> None:
    report = ReportFactory(released_at=timezone.now())
    assert report.is_released is True


@pytest.mark.django_db
def test_release_axis_orthogonal_to_publish() -> None:
    """A report can be published without being released."""
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published(game, author, released=False)
    assert report.is_published is True
    assert report.is_released is False


# ---------------------------------------------------------------------------
# SUD-V2 — report_detail wall
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_detail_published_unreleased_hidden_from_anonymous(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published(game, author, released=False)

    response = client.get(_detail_url(report))
    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_published_unreleased_hidden_from_non_author(client: Client) -> None:
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)
    report = _published(game, author, released=False)

    client.force_login(intruder)
    response = client.get(_detail_url(report))
    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_author_sees_own_unreleased(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published(game, author, released=False)

    client.force_login(author)
    response = client.get(_detail_url(report))
    assert response.status_code == 200


@pytest.mark.django_db
def test_detail_released_visible_to_anonymous(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published(game, author, released=True)

    response = client.get(_detail_url(report))
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# SUD-V3 — Stories
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_stories_index_public_no_login(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author, title="Released Game")
    _published(game, author, released=True)

    response = client.get(reverse("games:stories"))
    assert response.status_code == 200
    assert b"Released Game" in response.content


@pytest.mark.django_db
def test_stories_index_excludes_unreleased_games(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author, title="Hidden Game")
    _published(game, author, released=False)

    response = client.get(reverse("games:stories"))
    assert response.status_code == 200
    assert b"Hidden Game" not in response.content


@pytest.mark.django_db
def test_story_detail_aggregates_only_released(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    released = _published(game, author, released=True, title="Released Report")
    unreleased = _published(game, author, released=False, title="Unreleased Report")

    response = client.get(reverse("games:story_detail", kwargs={"pk": str(game.pk)}))
    assert response.status_code == 200
    context_reports = list(response.context["reports"])
    assert released in context_reports
    assert unreleased not in context_reports


@pytest.mark.django_db
def test_story_detail_404_when_no_released_content(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    _published(game, author, released=False)

    response = client.get(reverse("games:story_detail", kwargs={"pk": str(game.pk)}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_story_detail_excludes_non_public_released(client: Client) -> None:
    """A released report that is not PUBLIC must not surface in a story."""
    author = UserFactory()
    game = GameFactory(owner=author)
    ReportFactory(
        game=game,
        author=author,
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.FOLLOWERS,
        published_at=timezone.now(),
        released_at=timezone.now(),
    )

    response = client.get(reverse("games:story_detail", kwargs={"pk": str(game.pk)}))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# SUD-V4 — release action
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_release_by_author_sets_released_at(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published(game, author, released=False)

    client.force_login(author)
    response = client.post(_release_url(report))
    assert response.status_code == 302
    report.refresh_from_db()
    assert report.released_at is not None


@pytest.mark.django_db
def test_release_non_author_forbidden(client: Client) -> None:
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)
    report = _published(game, author, released=False)

    client.force_login(intruder)
    response = client.post(_release_url(report))
    assert response.status_code == 404
    report.refresh_from_db()
    assert report.released_at is None


@pytest.mark.django_db
def test_release_draft_rejected(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author, status=ReportStatus.DRAFT)

    client.force_login(author)
    response = client.post(_release_url(report))
    assert response.status_code == 400
    report.refresh_from_db()
    assert report.released_at is None


@pytest.mark.django_db
def test_release_reversible_when_not_federated(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published(game, author, released=True)  # no ap_id

    client.force_login(author)
    client.post(_release_url(report))
    report.refresh_from_db()
    assert report.released_at is None  # re-closed the wall


@pytest.mark.django_db
def test_release_irreversible_when_federated(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published(game, author, released=True)
    report.ap_id = "https://remote.example/reports/1"
    report.save(update_fields=["ap_id"])

    client.force_login(author)
    client.post(_release_url(report))
    report.refresh_from_db()
    assert report.released_at is not None  # stays released, wall is final


@pytest.mark.django_db
def test_released_report_appears_in_stories(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author, title="Now Public")
    report = _published(game, author, released=False)

    client.force_login(author)
    client.post(_release_url(report))

    client.logout()
    response = client.get(reverse("games:stories"))
    assert b"Now Public" in response.content


@pytest.mark.django_db
def test_story_detail_renders_rapports(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published(game, author, released=True)
    Rapport.objects.create(
        report=report,
        kind=RapportKind.NARRATION,
        content="The wall falls.",
        status=RapportStatus.PUBLISHED,
    )

    response = client.get(reverse("games:story_detail", kwargs={"pk": str(game.pk)}))
    assert response.status_code == 200
    assert b"The wall falls." in response.content


# ---------------------------------------------------------------------------
# SUD-V2 — feed_visible (the wall also gates reading feeds, not just detail)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_feed_visible_excludes_local_unreleased() -> None:
    """A local published-but-unreleased report is behind the wall — it must not
    surface in a reading feed (regression: it used to leak into the feed)."""
    author = UserFactory()
    game = GameFactory(owner=author)
    released = _published(game, author, released=True)
    unreleased = _published(game, author, released=False)

    visible = set(Report.objects.feed_visible())
    assert released in visible
    assert unreleased not in visible


@pytest.mark.django_db
def test_feed_visible_keeps_remote_unreleased() -> None:
    """A remote report never carries a local ``released_at`` (set nowhere on
    ingest). The wall is local, so remote content passes on published/public
    alone — otherwise the Fediverse feed would be permanently empty."""
    author = UserFactory()
    game = GameFactory(owner=author)
    remote_report = ReportFactory(
        game=game,
        author=author,
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.PUBLIC,
        published_at=timezone.now(),
        released_at=None,
        remote=True,
    )

    assert remote_report in set(Report.objects.feed_visible())


@pytest.mark.django_db
def test_feed_home_excludes_unreleased_from_followed_game(client: Client) -> None:
    """End-to-end: following a game whose only report is behind the wall yields a
    feed without that report."""
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Follow
    from suddenly.games.models import Game

    viewer = UserFactory()
    author = UserFactory()
    game = GameFactory(owner=author)
    Follow.objects.create(
        follower=viewer,
        content_type=ContentType.objects.get_for_model(Game),
        object_id=game.pk,
    )
    _published(game, author, released=False)

    client.force_login(viewer)
    response = client.get(reverse("feed:home"))
    assert response.status_code == 200
    report_items = [it for it in response.context["feed_items"] if it["type"] == "report"]
    assert report_items == []
