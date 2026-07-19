"""
Tests for the instance-wide interaction ban gating the local follow toggle
(Epic F, #136, DEC-F3 — local volet of critère 3).

Complements `tests/activitypub/test_block_gating.py` (federated volet) and
`tests/core/test_moderation.py` (service + admin queue + critères 1/2/4).

`characters.follow_views.follow_toggle` must refuse (403) when either the
requesting user or the target user is blocked (`User.is_blocked`), without
creating a `Follow` row. Non-user targets (`Character`/`Game`) are unaffected
since `is_blocked` tolerantly reads `False` off any object lacking the
attribute.
"""

from __future__ import annotations

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import Follow
from suddenly.users.models import User
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestFollowToggleBlockedRequester:
    def test_blocked_requester_gets_403_and_creates_no_follow(self) -> None:
        follower = UserFactory(is_blocked=True)
        target = UserFactory()
        client = Client()
        client.force_login(follower)

        response = client.post(
            reverse("characters:follow_toggle"),
            {"target_type": "user", "target_id": str(target.pk)},
        )

        assert response.status_code == 403
        ct = ContentType.objects.get_for_model(User)
        assert not Follow.objects.filter(
            follower=follower, content_type=ct, object_id=target.pk
        ).exists()


class TestFollowToggleBlockedTarget:
    def test_blocked_target_user_gets_403_and_creates_no_follow(self) -> None:
        follower = UserFactory()
        target = UserFactory(is_blocked=True)
        client = Client()
        client.force_login(follower)

        response = client.post(
            reverse("characters:follow_toggle"),
            {"target_type": "user", "target_id": str(target.pk)},
        )

        assert response.status_code == 403
        ct = ContentType.objects.get_for_model(User)
        assert not Follow.objects.filter(
            follower=follower, content_type=ct, object_id=target.pk
        ).exists()


class TestFollowToggleUnblockedNonRegression:
    def test_unblocked_user_can_still_follow(self) -> None:
        follower = UserFactory()
        target = UserFactory()
        client = Client()
        client.force_login(follower)

        response = client.post(
            reverse("characters:follow_toggle"),
            {"target_type": "user", "target_id": str(target.pk)},
        )

        assert response.status_code == 200
        ct = ContentType.objects.get_for_model(User)
        assert Follow.objects.filter(
            follower=follower, content_type=ct, object_id=target.pk
        ).exists()
