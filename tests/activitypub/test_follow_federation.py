"""
Tests for the Follow federation lifecycle (Epic C, #133).

Covers all 4 Phase 1 acceptance criteria:
1. `makemigrations --check --dry-run` clean after adding `Follow.accepted`
   (CI/manual check, not a pytest assertion — verified out-of-band).
2. An inbound Accept(Follow) confirms our outbound Follow (DEC-C1/C2).
3. An inbound Reject(Follow) deletes the optimistic outbound Follow (DEC-C3).
4. An inbound Accept(Offer) still follows the LinkRequest path unchanged
   (non-regression, DEC-038).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType

from suddenly.activitypub.inbox import handle_accept, handle_reject
from suddenly.characters.models import (
    Character,
    CharacterStatus,
    Follow,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
)
from suddenly.games.models import Game
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


@pytest.mark.django_db
class TestAcceptOfferNonRegression:
    """Criterion 4: Accept(Offer)/LinkRequest path unaffected by Follow discrimination."""

    def _make_remote_offer_setup(self) -> tuple[LinkRequest, str, str]:
        """Requester is local; target NPC + its controller live on the peer instance."""
        requester = UserFactory()
        peer_owner_actor_url = "https://peer.example/users/gm"
        peer_owner = _make_remote_user(peer_owner_actor_url)
        peer_game = Game.objects.create(
            title="Remote Game",
            owner=peer_owner,
            remote=True,
            ap_id="https://peer.example/games/remote",
        )
        target_character = Character.objects.create(
            name="Aria",
            status=CharacterStatus.NPC,
            creator=peer_owner,
            owner=peer_owner,
            origin_game=peer_game,
            remote=True,
            ap_id="https://peer.example/characters/aria",
        )
        link_request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=requester,
            target_character=target_character,
            status=LinkRequestStatus.PENDING,
            message="Please let me adopt Aria.",
        )
        offer_id = f"https://testserver/link-requests/{link_request.pk}"
        return link_request, offer_id, peer_owner_actor_url

    def test_accept_offer_still_reconstructs_link_request(self, db: Any, mocker: Any) -> None:
        link_request, offer_id, peer_owner_actor_url = self._make_remote_offer_setup()

        reconstruct = mocker.patch(
            "suddenly.characters.services.LinkService.reconstruct_remote_accept"
        )

        handle_accept(
            {"type": "Accept", "actor": peer_owner_actor_url, "object": offer_id, "summary": ""},
            actor_type="user",
            actor_identifier=link_request.requester.username,
        )

        reconstruct.assert_called_once()
        called_request = reconstruct.call_args[0][0]
        assert called_request.pk == link_request.pk
        # The Follow path must not have been touched — no Follow was created or matched.
        assert Follow.objects.count() == 0

    def test_accept_offer_not_swallowed_by_follow_ambiguous_string_match(
        self, db: Any, mocker: Any
    ) -> None:
        """A bare-string Offer id must never spuriously match an unrelated outbound Follow."""
        follower = UserFactory()
        remote_actor_url = "https://peer.example/users/frank"
        remote_user = _make_remote_user(remote_actor_url)
        unrelated_follow_ap_id = (
            f"https://testserver/users/{follower.username}/follows/{remote_user.pk}"
        )
        _make_outbound_follow(follower, remote_user, unrelated_follow_ap_id, accepted=False)

        link_request, offer_id, peer_owner_actor_url = self._make_remote_offer_setup()

        reconstruct = mocker.patch(
            "suddenly.characters.services.LinkService.reconstruct_remote_accept"
        )

        handle_accept(
            {"type": "Accept", "actor": peer_owner_actor_url, "object": offer_id, "summary": ""},
            actor_type="user",
            actor_identifier=link_request.requester.username,
        )

        reconstruct.assert_called_once()
        # The unrelated Follow must remain untouched (still unaccepted).
        assert Follow.objects.get(ap_id=unrelated_follow_ap_id).accepted is False
