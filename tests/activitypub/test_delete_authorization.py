"""
Tests for Delete object authorization (SUD-F6).

A Delete only removes an object that lives on the *signing actor's own domain*.
This prevents instance A from signing a Delete for an object hosted by
instance B.
"""

from __future__ import annotations

from typing import Any

import pytest

from suddenly.activitypub.inbox import handle_delete
from suddenly.characters.models import Character, CharacterStatus
from suddenly.games.models import Game
from suddenly.users.models import User


def _make_remote_character(ap_id: str, actor_url: str) -> Character:
    owner = User.objects.create(
        username=f"owner@{ap_id}",
        remote=True,
        ap_id=actor_url,
    )
    game = Game.objects.create(title="Remote", owner=owner, remote=True, ap_id=f"{actor_url}/game")
    return Character.objects.create(
        name="Aria",
        status=CharacterStatus.NPC,
        creator=owner,
        origin_game=game,
        remote=True,
        ap_id=ap_id,
    )


@pytest.mark.django_db
class TestDeleteAuthorization:
    def test_same_domain_delete_removes_record(self, db: Any) -> None:
        actor = "https://peer.example/users/sender"
        target = "https://peer.example/characters/aria"
        _make_remote_character(target, actor)

        handle_delete(
            {"type": "Delete", "actor": actor, "object": target},
            actor_type="user",
            actor_identifier="local",
        )

        assert not Character.objects.filter(ap_id=target).exists()

    def test_cross_domain_delete_is_rejected(self, db: Any) -> None:
        actor = "https://evil.example/users/attacker"
        target = "https://victim.example/characters/aria"
        _make_remote_character(target, "https://victim.example/users/owner")

        handle_delete(
            {"type": "Delete", "actor": actor, "object": target},
            actor_type="user",
            actor_identifier="local",
        )

        # The victim's character must survive a cross-domain Delete.
        assert Character.objects.filter(ap_id=target).exists()
