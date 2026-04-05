"""URL configuration for users app."""

from django.urls import path

from . import settings_views, views

app_name = "users"

urlpatterns = [
    # Settings (before username catch-all)
    path("settings/federation/", settings_views.settings_federation, name="settings_federation"),
    path("settings/data/", settings_views.settings_data, name="settings_data"),
    path("settings/export-follows/", settings_views.export_follows_csv, name="export_follows"),
    path("settings/import-follows/", settings_views.import_follows_csv, name="import_follows"),
    # Profile
    path("<str:username>/", views.ProfileView.as_view(), name="profile"),
    path("<str:username>/edit/", views.ProfileEditView.as_view(), name="profile_edit"),
]
