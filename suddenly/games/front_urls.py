"""Front-end URL patterns for games (DA-1)."""

from django.urls import path

from . import front_views

app_name = "games"

urlpatterns = [
    path("", front_views.game_list, name="list"),
    path("new/", front_views.game_create, name="create"),
    path("<uuid:pk>/", front_views.game_detail, name="detail"),
]
