"""Front-end URL patterns for games and reports (DA-1)."""

from django.urls import path

from . import front_views

app_name = "games"

urlpatterns = [
    path("", front_views.game_list, name="list"),
    path("new/", front_views.game_create, name="create"),
    path("bulk-delete/", front_views.game_delete_bulk, name="delete_bulk"),
    path("systems/search/", front_views.game_system_search, name="system_search"),
    path("<uuid:pk>/", front_views.game_detail, name="detail"),
    path("<uuid:pk>/edit/", front_views.game_edit, name="edit"),
    path("<uuid:pk>/delete/", front_views.game_delete, name="delete"),
    path("<uuid:game_pk>/reports/<uuid:pk>/", front_views.report_detail, name="report_detail"),
    path("<uuid:game_pk>/reports/new/", front_views.report_create, name="report_create"),
]
