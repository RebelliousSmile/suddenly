"""
Tests for the instance-wide interaction ban gating inbound federation
(Epic F, #136, DEC-F3 — federated volet of critère 3).

Complements `tests/characters/test_follow_gating.py` (local volet) and
`tests/core/test_moderation.py` (service + admin queue + critères 1/2/4).

`handle_follow` (`suddenly.activitypub.inbox`) must silently drop an inbound
Follow from a blocked remote user — no `Follow` row created, no signed
Accept delivered, no exception raised (best-effort, matches the existing
`handle_follow` error-handling style proven in
`tests/activitypub/test_follow_federation.py::TestFollowIncoming`).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType

from suddenly.activitypub.inbox import handle_follow
from suddenly.characters.models import Follow
from suddenly.users.models import User
from tests.factories import UserFactory


def _make_remote_user(actor_url: str, inbox_url: str, *, is_blocked: bool = False) -> User:
    user = User.objects.create(
        username=f"remote-{actor_url}",
        remote=True,
        ap_id=actor_url,
        inbox_url=inbox_url,
        is_blocked=is_blocked,
    )
    return user


@pytest.mark.django_db
class TestHandleFollowBlockedFollower:
    def test_blocked_remote_follower_creates_no_follow(self, mocker: Any) -> None:
        target = UserFactory()
        remote_actor_url = "https://peer.example/users/blocked-eve"
        _make_remote_user(
            remote_actor_url, "https://peer.example/users/blocked-eve/inbox", is_blocked=True
        )
        deliver = mocker.patch("suddenly.activitypub.inbox.sign_and_deliver")

        handle_follow(
            {"type": "Follow", "actor": remote_actor_url, "object": target.actor_url},
            actor_type="user",
            actor_identifier=target.username,
        )

        assert Follow.objects.count() == 0
        deliver.assert_not_called()

    def test_blocked_remote_follower_never_raises(self, mocker: Any) -> None:
        """Best-effort drop, not a 500 — mirrors the unknown-actor-type test in
        `test_follow_federation.py::TestFollowIncoming`."""
        target = UserFactory()
        remote_actor_url = "https://peer.example/users/blocked-mallory"
        _make_remote_user(
            remote_actor_url, "https://peer.example/users/blocked-mallory/inbox", is_blocked=True
        )
        mocker.patch("suddenly.activitypub.inbox.sign_and_deliver")

        handle_follow(
            {"type": "Follow", "actor": remote_actor_url, "object": target.actor_url},
            actor_type="user",
            actor_identifier=target.username,
        )
        # No exception -> pass.

    def test_unblocked_remote_follower_still_creates_follow(self, mocker: Any) -> None:
        """Non-regression: gating must not accidentally drop legitimate Follows."""
        target = UserFactory()
        remote_actor_url = "https://peer.example/users/allowed-frank"
        remote_follower = _make_remote_user(
            remote_actor_url, "https://peer.example/users/allowed-frank/inbox", is_blocked=False
        )
        deliver = mocker.patch("suddenly.activitypub.inbox.sign_and_deliver")

        handle_follow(
            {"type": "Follow", "actor": remote_actor_url, "object": target.actor_url},
            actor_type="user",
            actor_identifier=target.username,
        )

        ct = ContentType.objects.get_for_model(User)
        follow = Follow.objects.get(content_type=ct, object_id=target.pk)
        assert follow.follower_id == remote_follower.pk
        deliver.assert_called_once()
