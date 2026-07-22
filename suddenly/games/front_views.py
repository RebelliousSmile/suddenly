"""
HTMX-first views for games and reports (DA-1).

This module is a thin re-export shim. The actual view functions live in domain
modules (``game_views``, ``report_views``, ``rapport_views``,
``composer_views``); shared underscore-prefixed helpers live in
``_view_helpers``. This shim exists solely so that ``front_urls.py``'s
``from . import front_views`` + ``front_views.<view_name>`` keeps resolving
without any URL-configuration change.
"""

from __future__ import annotations

from .composer_views import cast_npc_create, composer
from .game_views import (
    game_close,
    game_create,
    game_delete,
    game_delete_bulk,
    game_detail,
    game_edit,
    game_list,
    game_search,
    stories_index,
    story_detail,
)
from .rapport_views import (
    marker_create,
    marker_delete,
    rapport_add_remote_parent,
    rapport_create,
    rapport_delete,
    rapport_edit,
    rapport_media_add,
    rapport_media_remove,
    rapport_move,
    rapport_reply,
)
from .report_views import (
    cast_add,
    cast_character_search,
    cast_mention_search,
    cast_remove,
    report_compose,
    report_create,
    report_detail,
    report_edit,
    report_release,
    scene_close,
    scene_open,
    scene_post_create,
    scene_reopen,
)

__all__ = [
    "cast_add",
    "cast_character_search",
    "cast_mention_search",
    "cast_npc_create",
    "cast_remove",
    "composer",
    "game_close",
    "game_create",
    "game_delete",
    "game_delete_bulk",
    "game_detail",
    "game_edit",
    "game_list",
    "game_search",
    "marker_create",
    "marker_delete",
    "rapport_add_remote_parent",
    "rapport_create",
    "rapport_delete",
    "rapport_edit",
    "rapport_media_add",
    "rapport_media_remove",
    "rapport_move",
    "rapport_reply",
    "report_compose",
    "report_create",
    "report_detail",
    "report_edit",
    "report_release",
    "scene_close",
    "scene_open",
    "scene_post_create",
    "scene_reopen",
    "stories_index",
    "story_detail",
]
