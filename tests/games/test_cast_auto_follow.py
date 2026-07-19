"""Cast <-> follow auto-sync (Epic D, #134).

Covers criterion 1 (adding a GameCast entry creates mutual AUTO follows
between players and the GM, idempotent, NPCs introduce no follow) and
criterion 2 (removing a cast entry — or closing the game — tears down only
the AUTO follows no longer justified by an active co-membership; a MANUAL
follow always survives; overlapping active games are respected).

Exercised through the real signal wiring (``GameCast.objects.create()`` /
``.delete()``), not by calling ``cast_follow`` functions directly — the
signal connection in ``GamesConfig.ready()`` is itself part of what's under
test (DEC-D2).
"""

from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType

import pytest

from suddenly.characters.models import Follow
from suddenly.games.models import GameCast
from tests.factories import CharacterFactory, GameFactory, UserFactory


def _user_ct() -> ContentType:
    from django.contrib.auth import get_user_model

    return ContentType.objects.get_for_model(get_user_model())


def _follows(a: Any, b: Any) -> Follow | None:
    """The Follow row a -> b, if any."""
    return Follow.objects.filter(follower=a, content_type=_user_ct(), object_id=b.pk).first()


# ---------------------------------------------------------------------------
# Criterion 1 — adding a cast entry
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cast_add_creates_mutual_auto_follows_player_and_gm() -> None:
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(status="pc", owner=player, creator=player, origin_game=game)

    GameCast.objects.create(game=game, character=pc, added_by=gm)

    gm_to_player = _follows(gm, player)
    player_to_gm = _follows(player, gm)
    assert gm_to_player is not None and gm_to_player.auto is True
    assert player_to_gm is not None and player_to_gm.auto is True


@pytest.mark.django_db
def test_cast_add_second_pc_creates_mutual_follows_between_all_players() -> None:
    gm = UserFactory()
    p1 = UserFactory()
    p2 = UserFactory()
    game = GameFactory(owner=gm)
    pc1 = CharacterFactory(status="pc", owner=p1, creator=p1, origin_game=game)
    pc2 = CharacterFactory(status="pc", owner=p2, creator=p2, origin_game=game)

    GameCast.objects.create(game=game, character=pc1, added_by=gm)
    GameCast.objects.create(game=game, character=pc2, added_by=gm)

    for a, b in [(gm, p1), (p1, gm), (gm, p2), (p2, gm), (p1, p2), (p2, p1)]:
        follow = _follows(a, b)
        assert follow is not None and follow.auto is True


@pytest.mark.django_db
def test_cast_add_is_idempotent_on_replay() -> None:
    """Re-running the sync (e.g. a second GameCast create touching the same
    game) never duplicates a Follow row — get_or_create only."""
    from suddenly.games.cast_follow import sync_cast_follows

    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(status="pc", owner=player, creator=player, origin_game=game)
    GameCast.objects.create(game=game, character=pc, added_by=gm)

    sync_cast_follows(game)
    sync_cast_follows(game)

    assert Follow.objects.filter(content_type=_user_ct(), auto=True).count() == 2


@pytest.mark.django_db
def test_cast_add_npc_introduces_no_follow() -> None:
    """An NPC (owner=None) casted alone introduces no player — no follow at
    all, since the GM is then the sole member."""
    gm = UserFactory()
    game = GameFactory(owner=gm)
    npc = CharacterFactory(status="npc", owner=None, creator=gm, origin_game=game)

    GameCast.objects.create(game=game, character=npc, added_by=gm)

    assert Follow.objects.filter(content_type=_user_ct(), auto=True).count() == 0


@pytest.mark.django_db
def test_cast_add_npc_alongside_pc_does_not_introduce_npc_as_member() -> None:
    """Casting an NPC alongside a real PC doesn't make the NPC (no owner) a
    follow participant — only the PC's owner and the GM are linked."""
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(status="pc", owner=player, creator=player, origin_game=game)
    npc = CharacterFactory(status="npc", owner=None, creator=gm, origin_game=game)

    GameCast.objects.create(game=game, character=pc, added_by=gm)
    GameCast.objects.create(game=game, character=npc, added_by=gm)

    assert Follow.objects.filter(content_type=_user_ct(), auto=True).count() == 2
    assert _follows(gm, player) is not None
    assert _follows(player, gm) is not None


@pytest.mark.django_db
def test_cast_add_preserves_preexisting_manual_follow() -> None:
    """A MANUAL follow between two soon-to-be co-members is never mutated by
    the sync — get_or_create only touches rows it creates."""
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(status="pc", owner=player, creator=player, origin_game=game)
    manual = Follow.objects.create(
        follower=player, content_type=_user_ct(), object_id=gm.pk, auto=False
    )

    GameCast.objects.create(game=game, character=pc, added_by=gm)

    manual.refresh_from_db()
    assert manual.auto is False


# ---------------------------------------------------------------------------
# Criterion 2 — removing a cast entry (teardown)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cast_remove_deletes_unjustified_auto_follow() -> None:
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(status="pc", owner=player, creator=player, origin_game=game)
    cast_row = GameCast.objects.create(game=game, character=pc, added_by=gm)
    assert _follows(gm, player) is not None

    cast_row.delete()

    assert _follows(gm, player) is None
    assert _follows(player, gm) is None


@pytest.mark.django_db
def test_cast_remove_preserves_manual_follow_between_same_pair() -> None:
    """A MANUAL follow between the same two users is never deleted by
    teardown, even though the AUTO justification just disappeared."""
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(status="pc", owner=player, creator=player, origin_game=game)
    cast_row = GameCast.objects.create(game=game, character=pc, added_by=gm)
    Follow.objects.create(follower=player, content_type=_user_ct(), object_id=gm.pk, auto=False)

    cast_row.delete()

    manual = _follows(player, gm)
    assert manual is not None
    assert manual.auto is False
    # The other direction (gm -> player) had no MANUAL counterpart: it's gone.
    assert _follows(gm, player) is None


@pytest.mark.django_db
def test_cast_remove_keeps_auto_follow_justified_by_another_active_game() -> None:
    """Two overlapping games share the same two players — removing the cast
    entry in one game must not tear down the follow still justified by the
    other (still-active) game."""
    gm = UserFactory()
    player = UserFactory()
    game_a = GameFactory(owner=gm)
    game_b = GameFactory(owner=gm)
    pc_a = CharacterFactory(status="pc", owner=player, creator=player, origin_game=game_a)
    pc_b = CharacterFactory(status="pc", owner=player, creator=player, origin_game=game_b)
    cast_a = GameCast.objects.create(game=game_a, character=pc_a, added_by=gm)
    GameCast.objects.create(game=game_b, character=pc_b, added_by=gm)

    cast_a.delete()

    follow = _follows(gm, player)
    assert follow is not None and follow.auto is True


@pytest.mark.django_db
def test_cast_remove_only_deletes_the_pair_no_longer_co_members() -> None:
    """Three-player cast, one leaves: the two remaining players (and the GM)
    keep their mutual AUTO follows; only pairs involving the leaver lose theirs."""
    gm = UserFactory()
    p1 = UserFactory()
    p2 = UserFactory()
    game = GameFactory(owner=gm)
    pc1 = CharacterFactory(status="pc", owner=p1, creator=p1, origin_game=game)
    pc2 = CharacterFactory(status="pc", owner=p2, creator=p2, origin_game=game)
    cast1 = GameCast.objects.create(game=game, character=pc1, added_by=gm)
    GameCast.objects.create(game=game, character=pc2, added_by=gm)

    cast1.delete()

    assert _follows(gm, p2) is not None
    assert _follows(p2, gm) is not None
    assert _follows(gm, p1) is None
    assert _follows(p1, gm) is None
