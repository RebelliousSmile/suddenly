"""URL configuration for users app."""

from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("<str:username>/", views.ProfileView.as_view(), name="profile"),
    path("<str:username>/edit/", views.ProfileEditView.as_view(), name="profile_edit"),
]
