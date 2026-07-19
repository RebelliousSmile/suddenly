"""
URL routes for the offers app (Epic B, #132, Phase 3).
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "offers"

urlpatterns = [
    path("<uuid:pk>/", views.offer_panel, name="panel"),
    path("<uuid:pk>/respond/", views.offer_respond, name="respond"),
    path("responses/<uuid:pk>/accept/", views.offer_accept, name="accept"),
    path("responses/<uuid:pk>/decline/", views.offer_decline, name="decline"),
]
