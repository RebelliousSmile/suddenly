"""Front-end URL patterns for games and reports (DA-1)."""

from django.urls import path

from . import front_views

app_name = "games"

urlpatterns = [
    path("", front_views.game_list, name="list"),
    path("search/", front_views.game_search, name="search"),
    path("compose/", front_views.report_compose, name="compose"),
    # Unified post composer (level Rapport) — the single _composer.html surface,
    # opened from the feed with two selectors (personnage, partie).
    path("compose/post/", front_views.composer, name="composer"),
    path(
        "<uuid:game_pk>/cast/npc/",
        front_views.cast_npc_create,
        name="cast_npc_create",
    ),
    path(
        "<uuid:game_pk>/scene/open/",
        front_views.scene_open,
        name="scene_open",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/post/",
        front_views.scene_post_create,
        name="scene_post_create",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/rapports/<uuid:rapport_pk>/media/add/",
        front_views.rapport_media_add,
        name="rapport_media_add",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/rapports/<uuid:rapport_pk>/media/remove/",
        front_views.rapport_media_remove,
        name="rapport_media_remove",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/rapports/<uuid:rapport_pk>/move/",
        front_views.rapport_move,
        name="rapport_move",
    ),
    # Stories — public reading surface for released content (SUD-V3)
    path("stories/", front_views.stories_index, name="stories"),
    path("stories/<uuid:pk>/", front_views.story_detail, name="story_detail"),
    path("new/", front_views.game_create, name="create"),
    path("bulk-delete/", front_views.game_delete_bulk, name="delete_bulk"),
    path("<uuid:pk>/", front_views.game_detail, name="detail"),
    path("<uuid:pk>/edit/", front_views.game_edit, name="edit"),
    path("<uuid:pk>/delete/", front_views.game_delete, name="delete"),
    path("<uuid:pk>/close/", front_views.game_close, name="game_close"),
    path("<uuid:game_pk>/reports/<uuid:pk>/", front_views.report_detail, name="report_detail"),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/release/",
        front_views.report_release,
        name="report_release",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/close/",
        front_views.scene_close,
        name="scene_close",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/reopen/",
        front_views.scene_reopen,
        name="scene_reopen",
    ),
    path("<uuid:game_pk>/reports/new/", front_views.report_create, name="report_create"),
    path("<uuid:game_pk>/reports/<uuid:pk>/edit/", front_views.report_edit, name="report_edit"),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/rapports/new/",
        front_views.rapport_create,
        name="rapport_create",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/rapports/<uuid:rapport_pk>/edit/",
        front_views.rapport_edit,
        name="rapport_edit",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/rapports/<uuid:rapport_pk>/delete/",
        front_views.rapport_delete,
        name="rapport_delete",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/rapports/<uuid:rapport_pk>/markers/new/",
        front_views.marker_create,
        name="marker_create",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/rapports/<uuid:rapport_pk>/markers/<uuid:marker_pk>/delete/",
        front_views.marker_delete,
        name="marker_delete",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/rapports/<uuid:rapport_pk>/reply/",
        front_views.rapport_reply,
        name="rapport_reply",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/rapports/<uuid:rapport_pk>/add-remote-parent/",
        front_views.rapport_add_remote_parent,
        name="rapport_add_remote_parent",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/cast/add/",
        front_views.cast_add,
        name="cast_add",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/cast/<uuid:cast_pk>/remove/",
        front_views.cast_remove,
        name="cast_remove",
    ),
    path(
        "<uuid:game_pk>/cast/search/",
        front_views.cast_character_search,
        name="cast_character_search",
    ),
    path(
        "<uuid:game_pk>/reports/<uuid:pk>/cast/mentions/",
        front_views.cast_mention_search,
        name="cast_mention_search",
    ),
]
