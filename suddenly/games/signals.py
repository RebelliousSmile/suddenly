"""
Signal receivers wiring ``GameCast`` mutations to the cast auto-follow sync
(Epic D, #134).

Plain functions, connected explicitly in ``GamesConfig.ready()`` with
``sender=GameCast`` (the real model class, imported lazily to dodge
app-loading order) and an explicit ``dispatch_uid`` — not the string-sender
``@receiver`` decorator pattern used elsewhere in this codebase
(``activitypub/signals.py``), which matches senders by ``id()`` identity and
so does not reliably match a string literal against the class object used at
``.send(sender=...)`` time. Kept deliberately thin: all actual logic lives in
``games/cast_follow.py``, which is directly unit-testable without going
through Django's signal dispatch at all.
"""

from __future__ import annotations

from typing import Any


def gamecast_post_save(sender: type[Any], instance: Any, created: bool, **kwargs: Any) -> None:
    """On a new GameCast row (any creation path — add_to_cast, NPC, seed/admin)."""
    if not created:
        return
    from suddenly.games.cast_follow import sync_cast_follows

    sync_cast_follows(instance.game)


def gamecast_post_delete(sender: type[Any], instance: Any, **kwargs: Any) -> None:
    """On a GameCast row removal — recompute, never blind-delete (DEC-D4)."""
    from suddenly.games.cast_follow import teardown_cast_follows_for_game

    teardown_cast_follows_for_game(instance.game)
