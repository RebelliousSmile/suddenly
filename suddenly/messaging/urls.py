"""
Front-end URL patterns for federated direct messages (Epic E, #135, DA-1).
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("new/", views.compose, name="compose"),
    path("send/", views.send_message, name="send"),
    path("<uuid:pk>/", views.thread, name="thread"),
]
