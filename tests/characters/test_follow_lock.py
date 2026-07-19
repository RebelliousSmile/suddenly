"""Unfollow lock between active co-members of a game (Epic D, #134, DEC-D5).

Criterion 3: unfollowing a User is refused while ``active_comembership_exists``
holds between the requester and the target (AUTO or MANUAL alike — the lock
covers any Follow, not just cast-generated ones). It becomes unfollowable
again once every shared game is closed, and teardown never deletes a MANUAL
follow on its own (already covered by ``test_cast_auto_follow.py``; the
end-to-end "still there after close" case is re-verified here).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import Follow
from suddenly.games.models import GameCast
from tests.factories import CharacterFactory, GameFactory, UserFactory


def _user_ct() -> ContentType:
    from django.contrib.auth import get_user_model

    return ContentType.objects.get_for_model(get_user_model())


def _toggle(client: Client, target: Any) -> Any:
    return client.post(
        reverse("characters:follow_toggle"),
        data={"target_type": "user", "target_id": str(target.pk)},
    )


def _make_co_members() -> tuple[Any, Any, Any]:
    """A GM and a player, mutually AUTO-followed via an active game's cast."""
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(status="pc", owner=player, creator=player, origin_game=game)
    GameCast.objects.create(game=game, character=pc, added_by=gm)
    return gm, player, game


@pytest.mark.django_db
def test_unfollow_refused_between_active_co_members(client: Client) -> None:
    gm, player, _game = _make_co_members()

    client.force_login(player)
    response = _toggle(client, gm)

    assert response.status_code == 200
    assert b"Verrouill" in response.content
    follow = Follow.objects.filter(
        follower=player, content_type=_user_ct(), object_id=gm.pk
    ).first()
    assert follow is not None  # still there — not deleted


@pytest.mark.django_db
def test_unfollow_allowed_once_game_closed(client: Client) -> None:
    gm, player, game = _make_co_members()
    from suddenly.games.services import close_game

    close_game(game=game, user=gm)

    client.force_login(player)
    response = _toggle(client, gm)

    assert response.status_code == 200
    follow = Follow.objects.filter(
        follower=player, content_type=_user_ct(), object_id=gm.pk
    ).first()
    assert follow is None  # unfollow went through


@pytest.mark.django_db
def test_unfollow_lock_also_freezes_a_manual_follow(client: Client) -> None:
    """DEC-D5: the lock is scoped to "active co-membership", not to the AUTO
    flag — a MANUAL follow between two active co-members is frozen too."""
    gm, player, _game = _make_co_members()
    Follow.objects.filter(follower=player, content_type=_user_ct(), object_id=gm.pk).update(
        auto=False
    )

    client.force_login(player)
    response = _toggle(client, gm)

    assert response.status_code == 200
    follow = Follow.objects.filter(
        follower=player, content_type=_user_ct(), object_id=gm.pk
    ).first()
    assert follow is not None
    assert follow.auto is False  # untouched, still MANUAL


@pytest.mark.django_db
def test_manual_follow_survives_teardown_after_cast_removal() -> None:
    """A MANUAL follow between two users who stop being co-members (cast entry
    removed) is never deleted by the teardown — it just stops being locked."""
    gm, player, game = _make_co_members()
    Follow.objects.filter(follower=player, content_type=_user_ct(), object_id=gm.pk).update(
        auto=False
    )

    GameCast.objects.get(game=game).delete()

    follow = Follow.objects.filter(
        follower=player, content_type=_user_ct(), object_id=gm.pk
    ).first()
    assert follow is not None
    assert follow.auto is False


@pytest.mark.django_db
def test_unfollow_between_non_co_members_is_not_locked(client: Client) -> None:
    """Sanity check: the lock never fires between two users sharing no active
    game — a plain MANUAL follow toggles off normally."""
    a = UserFactory()
    b = UserFactory()
    Follow.objects.create(follower=a, content_type=_user_ct(), object_id=b.pk, auto=False)

    client.force_login(a)
    response = _toggle(client, b)

    assert response.status_code == 200
    assert (
        Follow.objects.filter(follower=a, content_type=_user_ct(), object_id=b.pk).first() is None
    )


@pytest.mark.django_db
def test_follow_itself_stays_permitted_between_active_co_members(client: Client) -> None:
    """DEC-D5 only locks *unfollow* — following (the other toggle direction)
    is never blocked."""
    gm, player, _game = _make_co_members()
    # gm -> player has no Follow yet in this direction beyond the auto-sync,
    # which already created one; delete it to exercise a fresh follow.
    Follow.objects.filter(follower=gm, content_type=_user_ct(), object_id=player.pk).delete()

    client.force_login(gm)
    response = _toggle(client, player)

    assert response.status_code == 200
    assert Follow.objects.filter(follower=gm, content_type=_user_ct(), object_id=player.pk).exists()
