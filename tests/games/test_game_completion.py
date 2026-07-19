"""Game.completed_at opens the temporal wall for all its reports (Epic D,
#134, DEC-D6/DEC-D7).

Criterion 4: closing a game makes every one of its PUBLISHED/PUBLIC reports
pass ``released()``, ``feed_visible()`` and ``Quote.promotable()`` regardless
of their own ``released_at`` — via the shared ``wall_open_q()`` helper.
Retro-compat: on data with no ``completed_at`` set, ``released()`` returns
exactly the pre-Epic-D set (the added disjunct is empty). ``close_game`` is
GM-only (403 otherwise) and idempotent.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from suddenly.characters.models import Quote, QuoteVisibility
from suddenly.games.models import Report, ReportStatus, ReportVisibility
from suddenly.games.services import close_game
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


def _published_unreleased(game: object, author: object, **kwargs: object) -> Report:
    fields: dict[str, object] = {
        "game": game,
        "author": author,
        "status": ReportStatus.PUBLISHED,
        "visibility": ReportVisibility.PUBLIC,
        "published_at": timezone.now(),
        "released_at": None,
    }
    fields.update(kwargs)  # a caller may override released_at (retro-compat case)
    return ReportFactory(**fields)


# ---------------------------------------------------------------------------
# released() / feed_visible() — completed_at as an alternate wall-open path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_released_excludes_unreleased_report_of_an_active_game() -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published_unreleased(game, author)

    assert report not in set(Report.objects.released())


@pytest.mark.django_db
def test_released_includes_unreleased_report_once_game_completed() -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published_unreleased(game, author)

    close_game(game=game, user=author)

    assert report in set(Report.objects.released())


@pytest.mark.django_db
def test_feed_visible_includes_unreleased_report_once_game_completed() -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published_unreleased(game, author)

    close_game(game=game, user=author)

    assert report in set(Report.objects.feed_visible())


@pytest.mark.django_db
def test_released_retro_compat_without_completed_at() -> None:
    """On data with no completed_at set anywhere, released() is exactly the
    old released_at-only set — the wall_open_q disjunct is empty."""
    author = UserFactory()
    game = GameFactory(owner=author)
    released = _published_unreleased(game, author, released_at=timezone.now())
    unreleased = _published_unreleased(game, author)

    visible = set(Report.objects.released())
    assert released in visible
    assert unreleased not in visible


@pytest.mark.django_db
def test_promotable_includes_quote_of_report_once_game_completed() -> None:
    """Quote.promotable() (characters/models.py) shares wall_open_q via the
    report__ prefix — DEC-D6, rule of three."""
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _published_unreleased(game, author)
    character = CharacterFactory(creator=author, origin_game=game)
    quote = Quote.objects.create(
        content="A line worth remembering.",
        character=character,
        report=report,
        author=author,
        visibility=QuoteVisibility.PUBLIC,
    )

    assert quote not in set(Quote.objects.promotable())

    close_game(game=game, user=author)

    assert quote in set(Quote.objects.promotable())


# ---------------------------------------------------------------------------
# close_game service — GM-only guard, idempotence, teardown trigger
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_close_game_sets_completed_at() -> None:
    author = UserFactory()
    game = GameFactory(owner=author)

    close_game(game=game, user=author)

    game.refresh_from_db()
    assert game.completed_at is not None


@pytest.mark.django_db
def test_close_game_non_gm_raises_permission_denied() -> None:
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)

    with pytest.raises(PermissionDenied):
        close_game(game=game, user=intruder)

    game.refresh_from_db()
    assert game.completed_at is None


@pytest.mark.django_db
def test_close_game_is_idempotent() -> None:
    author = UserFactory()
    game = GameFactory(owner=author)

    close_game(game=game, user=author)
    first_completed_at = game.completed_at

    close_game(game=game, user=author)  # second call: no-op
    game.refresh_from_db()

    assert game.completed_at == first_completed_at


@pytest.mark.django_db
def test_close_game_triggers_auto_follow_teardown() -> None:
    """Closing a game is the other teardown trigger besides cast removal
    (DEC-D4/D7) — an AUTO follow only justified by this game's active
    membership must be torn down once it closes."""
    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Follow
    from suddenly.games.models import GameCast

    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(status="pc", owner=player, creator=player, origin_game=game)
    GameCast.objects.create(game=game, character=pc, added_by=gm)
    user_ct = ContentType.objects.get_for_model(get_user_model())
    assert Follow.objects.filter(
        follower=player, content_type=user_ct, object_id=gm.pk, auto=True
    ).exists()

    close_game(game=game, user=gm)

    assert not Follow.objects.filter(
        follower=player, content_type=user_ct, object_id=gm.pk, auto=True
    ).exists()


# ---------------------------------------------------------------------------
# game_close view — owner-only 403, idempotent redirect
# ---------------------------------------------------------------------------


def _close_url(game: object) -> str:
    return reverse("games:game_close", kwargs={"pk": game.pk})  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_game_close_view_by_owner_sets_completed_at(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)

    client.force_login(author)
    response = client.post(_close_url(game))

    assert response.status_code == 302
    game.refresh_from_db()
    assert game.completed_at is not None


@pytest.mark.django_db
def test_game_close_view_by_non_owner_forbidden(client: Client) -> None:
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)

    client.force_login(intruder)
    response = client.post(_close_url(game))

    assert response.status_code == 403
    game.refresh_from_db()
    assert game.completed_at is None


@pytest.mark.django_db
def test_game_close_view_requires_post(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)

    client.force_login(author)
    response = client.get(_close_url(game))

    assert response.status_code == 405
