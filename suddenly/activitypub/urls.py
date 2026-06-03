"""
ActivityPub actor URL patterns.
"""

from django.urls import path

from . import inbox, views

urlpatterns = [
    # User actors
    path("users/<str:username>", views.user_actor, name="user-actor"),
    path("users/<str:username>/inbox", inbox.user_inbox, name="user-inbox"),
    path("users/<str:username>/outbox", views.user_outbox, name="user-outbox"),
    path("users/<str:username>/followers", views.user_followers, name="user-followers"),
    # Game actors
    path("games/<uuid:game_id>", views.game_actor, name="game-actor"),
    path("games/<uuid:game_id>/inbox", inbox.game_inbox, name="game-inbox"),
    path("games/<uuid:game_id>/outbox", views.game_outbox, name="game-outbox"),
    # Character actors
    path("characters/<uuid:character_id>", views.character_actor, name="character-actor"),
    path("characters/<uuid:character_id>/inbox", inbox.character_inbox, name="character-inbox"),
    path("characters/<uuid:character_id>/outbox", views.character_outbox, name="character-outbox"),
]
