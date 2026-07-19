"""
Cast <-> follow synchronization (Epic D, #134).

A character entering a game's ``GameCast`` makes its owner (a player) and the
game's GM (``game.owner``) mutual AUTO followers of every other member of that
cast. Pure logic, no signal wiring here (see ``games/signals.py``) — every
function below is directly testable without going through a signal.

"Member" of a game (DEC-D3) = the owner of a character casted into it
(``GameCast.character.owner``, when set — an NPC has no owner and introduces
no player) union the game's GM (``game.owner``). AUTO follows are recomputed
from this live definition (DEC-D4) rather than stored as a trace: a boolean
``Follow.auto`` flag is enough (DEC-D1) — no ``AutoFollow(follow, game)``
linking table is needed.
"""

from __future__ import annotations

from itertools import permutations
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from .models import Game, GameCast

if TYPE_CHECKING:
    from suddenly.users.models import User


def _user_content_type() -> ContentType:
    return ContentType.objects.get_for_model(get_user_model())


def members_of(game: Game) -> set[User]:
    """Players (character owners) casted into ``game``, plus its GM.

    Two bounded queries regardless of cast size (ids, then instances) — no
    N+1. A character without an owner (an NPC) introduces no player.
    """
    player_ids = set(
        GameCast.objects.filter(game=game, character__owner__isnull=False)
        .values_list("character__owner_id", flat=True)
        .distinct()
    )
    member_ids = player_ids | {game.owner_id}
    return set(get_user_model().objects.filter(pk__in=member_ids))


def sync_cast_follows(game: Game) -> None:
    """Create mutual AUTO follows between every pair of ``game``'s members.

    Idempotent: ``get_or_create`` never touches a preexisting row, so a MANUAL
    follow (``auto=False``) between two members is always preserved
    (DEC-D1/D3) — only follows freshly *created* here are marked AUTO.
    """
    from suddenly.characters.models import Follow

    members = members_of(game)
    if len(members) < 2:
        return
    user_ct = _user_content_type()
    for follower, target in permutations(members, 2):
        Follow.objects.get_or_create(
            follower=follower,
            content_type=user_ct,
            object_id=target.pk,
            defaults={"auto": True, "accepted": True},
        )


def active_comembership_exists(a: User, b: User) -> bool:
    """Do ``a`` and ``b`` still share an active (not completed) game as members?

    Recomputed from current state (DEC-D4), never a stored trace — correct
    across overlapping games and safe to call repeatedly. The two ``filter()``
    calls each span the ``cast`` relation independently, so a game only
    matches when *each* side is separately satisfied (owner or cast-owner),
    never by a single shared cast row satisfying both at once.
    """
    if a.pk == b.pk:
        return False
    return (
        Game.objects.filter(completed_at__isnull=True)
        .filter(Q(owner_id=a.pk) | Q(cast__character__owner_id=a.pk))
        .filter(Q(owner_id=b.pk) | Q(cast__character__owner_id=b.pk))
        .exists()
    )


def teardown_cast_follows_for_game(game: Game) -> None:
    """Remove AUTO follows no longer justified by any active co-membership.

    Called after a cast entry is removed (``post_delete(GameCast)``) or a game
    is closed (``close_game``) — in both cases ``game``'s member set (or its
    ``completed_at``) has just changed. The candidate pairs are the game's
    *current* members plus everyone who still holds an AUTO follow to or from
    one of them — this also catches a player who just dropped out of the cast
    entirely (so they are no longer in ``members_of``) but still carries a
    stale AUTO follow from when they were. Recomputed via
    :func:`active_comembership_exists`, so a follow still justified by another
    active game (multi-game overlap) is left untouched. Never touches a MANUAL
    follow (``auto=False``).
    """
    from suddenly.characters.models import Follow

    user_ct = _user_content_type()
    current_members = members_of(game)
    member_ids = {u.pk for u in current_members}
    if not member_ids:
        return

    related_ids = set(
        Follow.objects.filter(
            auto=True, content_type=user_ct, object_id__in=member_ids
        ).values_list("follower_id", flat=True)
    ) | set(
        Follow.objects.filter(
            auto=True, content_type=user_ct, follower_id__in=member_ids
        ).values_list("object_id", flat=True)
    )

    candidates = list(get_user_model().objects.filter(pk__in=member_ids | related_ids))

    for a, b in permutations(candidates, 2):
        if active_comembership_exists(a, b):
            continue
        Follow.objects.filter(follower=a, content_type=user_ct, object_id=b.pk, auto=True).delete()
