"""Front-end federation URLs (DA-1)."""

from django.urls import path

from . import federation_views

app_name = "federation"

urlpatterns = [
    path("search/", federation_views.federated_search, name="search"),
    path("remote/", federation_views.remote_profile, name="remote_profile"),
    path("remote/follow/", federation_views.remote_follow_toggle, name="remote_follow_toggle"),
]
