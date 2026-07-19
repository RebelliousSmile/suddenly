"""
Tests for the Follow federation lifecycle (Epic C, #133).

Covers Phase 1 acceptance criterion 2: an inbound Accept(Follow) confirms our
outbound Follow (DEC-C1/C2). Reject(Follow) and the Accept(Offer) non-regression
coverage land in follow-up commits of the same phase.

Criterion 1 (`makemigrations --check --dry-run` clean after adding
`Follow.accepted`) is a CI/manual check, not a pytest assertion — verified
out-of-band.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType

from suddenly.activitypub.inbox import handle_accept, handle_reject
from suddenly.characters.models import Follow
from suddenly.users.models import User
from tests.factories import UserFactory


def _make_remote_user(actor_url: str) -> User:
    return User.objects.create(
        username=f"remote-{actor_url}",
        remote=True,
        ap_id=actor_url,
    )


def _make_outbound_follow(
    follower: User, target: User, follow_ap_id: str, *, accepted: bool = False
) -> Follow:
    ct = ContentType.objects.get_for_model(User)
    return Follow.objects.create(
        follower=follower,
        content_type=ct,
        object_id=target.pk,
        remote=False,
        ap_id=follow_ap_id,
        accepted=accepted,
    )


@pytest.mark.django_db
class TestAcceptFollow:
    """Criterion 2: Accept(Follow) confirms our outbound Follow."""

    def test_accept_follow_by_dict_object_confirms_follow(self, db: Any) -> None:
        follower = UserFactory()
        remote_actor_url = "https://peer.example/users/alice"
        remote_user = _make_remote_user(remote_actor_url)
        follow_ap_id = f"https://testserver/users/{follower.username}/follows/{remote_user.pk}"
        _make_outbound_follow(follower, remote_user, follow_ap_id, accepted=False)

        handle_accept(
            {
                "type": "Accept",
                "actor": remote_actor_url,
                "object": {"type": "Follow", "id": follow_ap_id},
            },
            actor_type="user",
            actor_identifier=follower.username,
        )

        assert Follow.objects.get(ap_id=follow_ap_id).accepted is True

    def test_accept_follow_by_bare_string_object_confirms_follow(self, db: Any) -> None:
        follower = UserFactory()
        remote_actor_url = "https://peer.example/users/bob"
        remote_user = _make_remote_user(remote_actor_url)
        follow_ap_id = f"https://testserver/users/{follower.username}/follows/{remote_user.pk}"
        _make_outbound_follow(follower, remote_user, follow_ap_id, accepted=False)

        handle_accept(
            {"type": "Accept", "actor": remote_actor_url, "object": follow_ap_id},
            actor_type="user",
            actor_identifier=follower.username,
        )

        assert Follow.objects.get(ap_id=follow_ap_id).accepted is True

    def test_accept_follow_fallback_matches_by_actor_when_id_unknown(self, db: Any) -> None:
        """A dict object whose id doesn't match any row falls back to the sender's actor."""
        follower = UserFactory()
        remote_actor_url = "https://peer.example/users/carol"
        remote_user = _make_remote_user(remote_actor_url)
        follow_ap_id = f"https://testserver/users/{follower.username}/follows/{remote_user.pk}"
        _make_outbound_follow(follower, remote_user, follow_ap_id, accepted=False)

        handle_accept(
            {
                "type": "Accept",
                "actor": remote_actor_url,
                "object": {"type": "Follow", "id": "https://peer.example/activities/unrelated"},
            },
            actor_type="user",
            actor_identifier=follower.username,
        )

        assert Follow.objects.get(ap_id=follow_ap_id).accepted is True

    def test_accept_follow_no_match_does_not_error(self, db: Any) -> None:
        """No local Follow matches: handled gracefully, no exception, nothing mutated."""
        handle_accept(
            {
                "type": "Accept",
                "actor": "https://peer.example/users/nobody",
                "object": {"type": "Follow", "id": "https://peer.example/follows/unknown"},
            },
            actor_type="user",
            actor_identifier="local",
        )
        # No assertion target other than "did not raise" — nothing was created.
        assert Follow.objects.count() == 0


@pytest.mark.django_db
class TestRejectFollow:
    """Criterion 3: Reject(Follow) deletes the optimistic outbound Follow."""

    def test_reject_follow_by_dict_object_deletes_follow(self, db: Any) -> None:
        follower = UserFactory()
        remote_actor_url = "https://peer.example/users/dave"
        remote_user = _make_remote_user(remote_actor_url)
        follow_ap_id = f"https://testserver/users/{follower.username}/follows/{remote_user.pk}"
        _make_outbound_follow(follower, remote_user, follow_ap_id, accepted=False)

        handle_reject(
            {
                "type": "Reject",
                "actor": remote_actor_url,
                "object": {"type": "Follow", "id": follow_ap_id},
            },
            actor_type="user",
            actor_identifier=follower.username,
        )

        assert not Follow.objects.filter(ap_id=follow_ap_id).exists()

    def test_reject_follow_by_bare_string_object_deletes_follow(self, db: Any) -> None:
        follower = UserFactory()
        remote_actor_url = "https://peer.example/users/erin"
        remote_user = _make_remote_user(remote_actor_url)
        follow_ap_id = f"https://testserver/users/{follower.username}/follows/{remote_user.pk}"
        _make_outbound_follow(follower, remote_user, follow_ap_id, accepted=False)

        handle_reject(
            {"type": "Reject", "actor": remote_actor_url, "object": follow_ap_id},
            actor_type="user",
            actor_identifier=follower.username,
        )

        assert not Follow.objects.filter(ap_id=follow_ap_id).exists()
