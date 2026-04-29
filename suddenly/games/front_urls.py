"""Front-end URL patterns for games and reports (DA-1)."""

from django.urls import path

from . import front_views

app_name = "games"

urlpatterns = [
    path("", front_views.game_list, name="list"),
    path("search/", front_views.game_search, name="search"),
    path("compose/", front_views.report_compose, name="compose"),
    path("new/", front_views.game_create, name="create"),
    path("bulk-delete/", front_views.game_delete_bulk, name="delete_bulk"),
    path("systems/search/", front_views.game_system_search, name="system_search"),
    path("<uuid:pk>/", front_views.game_detail, name="detail"),
    path("<uuid:pk>/edit/", front_views.game_edit, name="edit"),
    path("<uuid:pk>/delete/", front_views.game_delete, name="delete"),
    path("<uuid:game_pk>/reports/<uuid:pk>/", front_views.report_detail, name="report_detail"),
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
]
