"""URL configuration for users app."""

from django.urls import path

from . import settings_views, views

app_name = "users"

urlpatterns = [
    # Settings (before username catch-all)
    path("settings/preferences/", settings_views.settings_preferences, name="settings_preferences"),
    path("settings/federation/", settings_views.settings_federation, name="settings_federation"),
    path("settings/data/", settings_views.settings_data, name="settings_data"),
    path("settings/export-follows/", settings_views.export_follows_csv, name="export_follows"),
    path("settings/import-follows/", settings_views.import_follows_csv, name="import_follows"),
    path("settings/export-games/", settings_views.export_games, name="export_games"),
    path("settings/export-characters/", settings_views.export_characters, name="export_characters"),
    path("settings/import-games/", settings_views.import_games, name="import_games"),
    path("settings/import-characters/", settings_views.import_characters, name="import_characters"),
    # Profile
    path("<str:username>/", views.ProfileView.as_view(), name="profile"),
    path("<str:username>/edit/", views.ProfileEditView.as_view(), name="profile_edit"),
]
