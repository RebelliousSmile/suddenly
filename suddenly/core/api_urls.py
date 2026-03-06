"""
API URL patterns.
"""

from django.urls import include, path

urlpatterns = [
    path("games/", include("suddenly.games.api_urls")),
    path("characters/", include("suddenly.characters.api_urls")),
]
