"""
API URL patterns.
"""

from django.urls import path, include

urlpatterns = [
    path("games/", include("suddenly.games.api_urls")),
    path("characters/", include("suddenly.characters.api_urls")),
]
