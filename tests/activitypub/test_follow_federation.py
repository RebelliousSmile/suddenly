"""
Tests for the Follow federation lifecycle (Epic C, #133).

Covers the 4 epic-level acceptance criteria (see Phase 5 of
`aidd_docs/tasks/2026_07/2026_07_19-133-epic-c-follow-federation.md`):
1. An outbound Follow delivers a signed activity, and an inbound
   Accept(Follow) confirms it (DEC-C1/C2) — `TestAcceptFollow` +
   `TestFollowOutgoingThenAccept`.
2. An inbound Follow creates a local `Follow` and delivers a signed Accept
   — `TestFollowIncoming`.
3. Remote profile enrichment (Suddenly vs Mastodon) — covered in
   `tests/activitypub/test_follow_ui.py` (Phase 4/5).
4. `Undo(Follow)` outbound deletes the local `Follow`; `Undo(Follow)` inbound
   deletes the local `Follow` — `TestUndoFollow`.

Also covers Phase 1's non-regression criterion:
- An inbound Accept(Offer) still follows the LinkRequest path unchanged
  (DEC-038) — `TestAcceptOfferNonRegression`.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType

from suddenly.activitypub.inbox import handle_accept, handle_follow, handle_reject, handle_undo
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


def _make_remote_user_with_inbox(actor_url: str, inbox_url: str) -> User:
    user = _make_remote_user(actor_url)
    user.inbox_url = inbox_url
    user.save(update_fields=["inbox_url"])
    return user


@pytest.mark.django_db
class TestFollowOutgoingThenAccept:
    """Criterion 1: an outbound Follow delivers a signed activity, and an inbound
    Accept(Follow) confirms it (DEC-C1/C2).

    Direct-call complement to `tests/test_federation_e2e.py::TestFollowOutgoing`
    (which proves delivery via full HTTP mocking) — this test chains delivery
    with the confirming Accept in one flow, at the handler/task level.
    """

    def test_follow_outgoing_then_accept_confirms(
        self, db: Any, mocker: Any, settings: Any
    ) -> None:
        from suddenly.activitypub.tasks import send_follow_activity

        settings.AP_BASE_URL = "https://testserver"
        follower = UserFactory(remote=False)
        remote_actor_url = "https://peer.example/users/judy"
        remote_target = _make_remote_user_with_inbox(
            remote_actor_url, "https://peer.example/users/judy/inbox"
        )
        follow_ap_id = f"https://testserver/users/{follower.username}/follows/{remote_target.pk}"
        # follow_post_save fires real delivery for a target with inbox_url set —
        # suppress it during creation (delivery under test is the explicit
        # send_follow_activity call below, not the signal's own eager delivery).
        mocker.patch("suddenly.activitypub.signals._safe_delay")
        _make_outbound_follow(follower, remote_target, follow_ap_id, accepted=False)

        deliver = mocker.patch("suddenly.activitypub._http.sign_and_deliver")

        send_follow_activity(str(follower.pk), remote_actor_url, follow_ap_id, target_type="user")

        deliver.assert_called_once()
        activity_arg = deliver.call_args[0][0]
        assert activity_arg["type"] == "Follow"
        assert activity_arg["id"] == follow_ap_id
        assert deliver.call_args[0][1] == remote_target.inbox_url
        assert Follow.objects.get(ap_id=follow_ap_id).accepted is False

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


@pytest.mark.django_db
class TestFollowIncoming:
    """Criterion 2: an inbound Follow creates a local `Follow` and delivers a
    signed Accept.

    Direct-call complement to `tests/test_federation_e2e.py::TestFollowIncoming`
    (full HTTP-cycle via `process_inbox`) — this test calls `handle_follow`
    directly, lighter-weight and co-located with the rest of the discrimination
    tests in this file.
    """

    def test_handle_follow_creates_follow_and_delivers_accept(self, db: Any, mocker: Any) -> None:
        target = UserFactory()
        remote_actor_url = "https://peer.example/users/grace"
        remote_follower = _make_remote_user_with_inbox(
            remote_actor_url, "https://peer.example/users/grace/inbox"
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
        activity_arg = deliver.call_args[0][0]
        assert activity_arg["type"] == "Accept"
        assert activity_arg["object"]["type"] == "Follow"
        assert deliver.call_args[0][1] == remote_follower.inbox_url

    def test_handle_follow_unknown_actor_type_does_not_error(self, db: Any, mocker: Any) -> None:
        """An unrecognized `actor_type` is handled gracefully — no exception."""
        deliver = mocker.patch("suddenly.activitypub.inbox.sign_and_deliver")

        handle_follow(
            {"type": "Follow", "actor": "https://peer.example/users/nobody", "object": "x"},
            actor_type="spaceship",
            actor_identifier="unknown",
        )

        deliver.assert_not_called()
        assert Follow.objects.count() == 0


@pytest.mark.django_db
class TestUndoFollow:
    """Criterion 4: `Undo(Follow)` outbound deletes the local `Follow`;
    `Undo(Follow)` inbound deletes the local `Follow`.
    """

    def test_send_undo_follow_activity_outbound_deletes_follow(
        self, db: Any, mocker: Any, settings: Any
    ) -> None:
        from suddenly.activitypub.tasks import send_undo_follow_activity

        settings.AP_BASE_URL = "https://testserver"
        follower = UserFactory(remote=False)
        remote_actor_url = "https://peer.example/users/heidi"
        remote_target = _make_remote_user_with_inbox(
            remote_actor_url, "https://peer.example/users/heidi/inbox"
        )
        follow_ap_id = f"https://testserver/users/{follower.username}/follows/{remote_target.pk}"
        # follow_post_save fires real delivery for a target with inbox_url set —
        # suppress it during creation (delivery under test is the explicit
        # send_undo_follow_activity call below, not the signal's own eager delivery).
        mocker.patch("suddenly.activitypub.signals._safe_delay")
        _make_outbound_follow(follower, remote_target, follow_ap_id, accepted=True)

        deliver = mocker.patch("suddenly.activitypub._http.sign_and_deliver")

        send_undo_follow_activity(str(follower.pk), remote_actor_url, target_type="user")

        deliver.assert_called_once()
        activity_arg = deliver.call_args[0][0]
        assert activity_arg["type"] == "Undo"
        assert activity_arg["object"]["id"] == follow_ap_id
        assert deliver.call_args[0][1] == remote_target.inbox_url

        assert not Follow.objects.filter(ap_id=follow_ap_id).exists()

    def test_handle_undo_inbound_deletes_follow(self, db: Any) -> None:
        target = UserFactory()
        remote_actor_url = "https://peer.example/users/ivan"
        remote_follower = _make_remote_user(remote_actor_url)
        ct = ContentType.objects.get_for_model(User)
        follow = Follow.objects.create(
            follower=remote_follower,
            content_type=ct,
            object_id=target.pk,
            remote=True,
        )

        handle_undo(
            {
                "type": "Undo",
                "actor": remote_actor_url,
                "object": {
                    "type": "Follow",
                    "id": "https://peer.example/follows/123",
                    "actor": remote_actor_url,
                    "object": target.actor_url,
                },
            },
            actor_type="user",
            actor_identifier=target.username,
        )

        assert not Follow.objects.filter(pk=follow.pk).exists()
