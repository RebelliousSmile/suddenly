"""
Front-end URL patterns for characters (DA-1: HTMX-first).

These serve HTML pages. The DRF API URLs remain in api_urls.py.
"""

from django.urls import path

from . import front_views

app_name = "characters"

urlpatterns = [
    path("", front_views.character_list, name="list"),
    path("search/", front_views.character_search, name="search"),
    path("<slug:slug>/", front_views.character_detail, name="detail"),
]
