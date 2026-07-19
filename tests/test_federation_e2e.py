"""
Federation tests — cross-instance flows.

Marker ``e2e_federation`` is excluded from the default test run.
Live tests require FEDERATION_PEER_URL to point at a running peer instance.

Unit-level tests in this file mock the network but verify the *contract*
between inbox/tasks and ``deliver_activity``, so they run in CI without a peer.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from suddenly.activitypub.signatures import generate_key_pair
from tests.factories import UserFactory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def peer_url() -> str:
    """URL of the remote peer instance (Railway test instance)."""
    return os.environ.get("FEDERATION_PEER_URL", "https://test.suddenly.social")


@pytest.fixture
def run_prefix() -> str:
    """Short unique prefix to avoid collision between test runs."""
    return uuid.uuid4().hex[:8]


@pytest.fixture
def local_federation_user(db: Any, settings: Any) -> Any:
    """Local user with a generated key pair, ready for federation."""
    settings.DOMAIN = "local.suddenly.test"
    settings.AP_BASE_URL = "https://local.suddenly.test"

    private_pem, public_pem = generate_key_pair()

    user = UserFactory(
        username="federation_user",
        display_name="Federation User",
        remote=False,
        public_key=public_pem,
        private_key=private_pem,
    )
    return user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_follow_activity(follower_url: str, target_url: str) -> dict[str, Any]:
    """Build a minimal Follow activity dict."""
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Follow",
        "id": f"{follower_url}#follow-{uuid.uuid4()}",
        "actor": follower_url,
        "object": target_url,
    }


def _make_signed_inbox_request(
    rf: RequestFactory,
    activity: dict[str, Any],
    actor_url: str,
    private_pem: str,
    path: str,
) -> Any:
    """Create a signed POST request as if coming from a remote actor."""
    import base64
    import hashlib
    from datetime import UTC, datetime
    from typing import cast
    from urllib.parse import urlparse

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

    key_id = f"{actor_url}#main-key"
    body = json.dumps(activity)
    parsed = urlparse(f"https://local.suddenly.test{path}")

    date_str = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
    host = parsed.netloc
    digest = f"SHA-256={base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()}"

    signing_string = (
        f"(request-target): post {parsed.path}\nhost: {host}\ndate: {date_str}\ndigest: {digest}"
    )

    private_key = cast(
        RSAPrivateKey,
        serialization.load_pem_private_key(
            private_pem.encode(), password=None, backend=default_backend()
        ),
    )
    sig = base64.b64encode(
        private_key.sign(signing_string.encode(), padding.PKCS1v15(), hashes.SHA256())
    ).decode()

    sig_header = (
        f'keyId="{key_id}",'
        f'algorithm="rsa-sha256",'
        f'headers="(request-target) host date digest",'
        f'signature="{sig}"'
    )

    return rf.post(
        path,
        data=body,
        content_type="application/activity+json",
        HTTP_HOST=host,
        HTTP_DATE=date_str,
        HTTP_DIGEST=digest,
        HTTP_SIGNATURE=sig_header,
    )


# ---------------------------------------------------------------------------
# Flow: Follow incoming (remote → local)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFollowIncoming:
    """Remote actor follows a local user — inbox must create Follow and send signed Accept."""

    def test_follow_incoming_creates_follow_and_sends_accept(
        self,
        rf: RequestFactory,
        local_federation_user: Any,
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        RED: inbox.handle_follow must call deliver_activity.delay with
        actor_key_id and private_key_pem so the Accept is signed.

        Failure mode without the fix:
          deliver_activity.delay(activity=..., inbox_url=...)
          — missing actor_key_id and private_key_pem → unsigned Accept.
        """
        from suddenly.activitypub.inbox import process_inbox
        from suddenly.characters.models import Follow
        from suddenly.users.models import User

        remote_private_pem, remote_public_pem = generate_key_pair()
        remote_actor_url = "https://peer.suddenly.test/users/remote_alice"
        remote_inbox_url = "https://peer.suddenly.test/users/remote_alice/inbox"

        # Simulate remote actor data returned by httpx
        actor_data = {
            "id": remote_actor_url,
            "type": "Person",
            "preferredUsername": "remote_alice",
            "name": "Remote Alice",
            "inbox": remote_inbox_url,
            "outbox": "https://peer.suddenly.test/users/remote_alice/outbox",
            "publicKey": {
                "id": f"{remote_actor_url}#main-key",
                "owner": remote_actor_url,
                "publicKeyPem": remote_public_pem,
            },
        }

        # Mock httpx.Client used in get_or_create_remote_user
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = actor_data
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.get.return_value = mock_http_response

        # Capture deliver_activity.delay calls
        captured_delay_calls: list[dict[str, Any]] = []

        def fake_delay(**kwargs: Any) -> None:
            captured_delay_calls.append(kwargs)

        mocker.patch("httpx.Client", return_value=mock_client_instance)
        # deliver_activity is imported inside handle_follow via
        # `from .tasks import deliver_activity` — patch the tasks module, not inbox.
        mock_deliver = mocker.MagicMock()
        mock_deliver.delay.side_effect = fake_delay
        mocker.patch("suddenly.activitypub.tasks.deliver_activity", mock_deliver)

        # Bypass signature verification — we test the handler contract, not sig verification
        mocker.patch(
            "suddenly.activitypub.inbox.verify_signature",
            return_value=(True, f"{remote_actor_url}#main-key"),
        )
        mocker.patch("suddenly.activitypub.inbox._check_rate_limit", return_value=False)

        target_url = local_federation_user.actor_url
        activity = _build_follow_activity(remote_actor_url, target_url)

        path = f"/users/{local_federation_user.username}/inbox"
        request = rf.post(
            path,
            data=json.dumps(activity),
            content_type="application/activity+json",
            HTTP_HOST="local.suddenly.test",
            HTTP_SIGNATURE=(
                f'keyId="{remote_actor_url}#main-key",'
                'headers="(request-target) host date",signature="dummy"'
            ),
        )

        response = process_inbox(
            request,
            actor_type="user",
            actor_identifier=local_federation_user.username,
        )

        # 1. Inbox must return 202
        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        # 2. A Follow object must have been created in the DB
        remote_user = User.objects.filter(ap_id=remote_actor_url).first()
        assert remote_user is not None, "Remote user must be created in DB"
        assert remote_user.remote is True

        follow_exists = Follow.objects.filter(
            follower=remote_user,
            object_id=local_federation_user.pk,
        ).exists()
        assert follow_exists, "Follow record must be created"

        # 3. deliver_activity.delay must have been called with signing keys
        assert len(captured_delay_calls) == 1, (
            f"deliver_activity.delay must be called exactly once, got {len(captured_delay_calls)}"
        )

        call_kwargs = captured_delay_calls[0]

        assert "actor_key_id" in call_kwargs, (
            "deliver_activity.delay must receive actor_key_id — Accept would be unsigned without it"
        )
        assert call_kwargs["actor_key_id"] is not None, "actor_key_id must not be None"
        assert "private_key_pem" in call_kwargs, (
            "deliver_activity.delay must receive private_key_pem"
            " — Accept would be unsigned without it"
        )
        assert call_kwargs["private_key_pem"] is not None, "private_key_pem must not be None"

        # 4. The Accept must target the remote actor's inbox
        assert call_kwargs.get("inbox_url") == remote_inbox_url, (
            f"Accept must be delivered to remote inbox {remote_inbox_url}, "
            f"got {call_kwargs.get('inbox_url')}"
        )

        # 5. The Accept activity must wrap the original Follow
        accept_activity = call_kwargs.get("activity", {})
        assert accept_activity.get("type") == "Accept", "Delivered activity must be of type Accept"
        assert accept_activity.get("actor") == target_url, "Accept actor must be the local user"


# ---------------------------------------------------------------------------
# Flow: Follow outgoing (local → remote)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFollowOutgoing:
    """Local user sends a Follow to a remote actor — verify deliver_activity contract."""

    def test_follow_outgoing_reaches_remote_inbox(
        self,
        local_federation_user: Any,
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        RED: send_follow_activity must call deliver_activity.delay with:
        - activity of type Follow, actor=local user's actor_url
        - inbox_url = remote actor's inbox
        - actor_key_id = local user's key id
        - private_key_pem = local user's private key

        Skips if FEDERATION_PEER_URL is not set (Mode A — no live peer needed).
        """
        peer_url = os.environ.get("FEDERATION_PEER_URL", "")
        peer_actor = os.environ.get(
            "FEDERATION_PEER_ACTOR",
            f"{peer_url}/users/testbot"
            if peer_url
            else "https://test.suddenly.social/users/testbot",
        )
        remote_inbox = f"{peer_actor}/inbox"

        from suddenly.activitypub.tasks import send_follow_activity

        captured_delay_calls: list[dict[str, Any]] = []

        def fake_delay(**kwargs: Any) -> None:
            captured_delay_calls.append(kwargs)

        mock_deliver = mocker.MagicMock()
        mock_deliver.delay.side_effect = fake_delay
        mocker.patch("suddenly.activitypub.tasks.deliver_activity", mock_deliver)

        # Mock httpx to resolve remote actor inbox without network
        remote_actor_data = {
            "id": peer_actor,
            "type": "Person",
            "preferredUsername": "testbot",
            "inbox": remote_inbox,
            "outbox": f"{peer_actor}/outbox",
            "publicKey": {
                "id": f"{peer_actor}#main-key",
                "owner": peer_actor,
                "publicKeyPem": "fake-public-key-pem",
            },
        }
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = remote_actor_data
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.get.return_value = mock_http_response
        mocker.patch("httpx.Client", return_value=mock_client_instance)

        # Execute: local user follows the remote actor
        send_follow_activity(str(local_federation_user.pk), peer_actor)

        # 1. deliver_activity.delay must have been called exactly once
        assert len(captured_delay_calls) == 1, (
            f"deliver_activity.delay must be called exactly once, got {len(captured_delay_calls)}"
        )

        call_kwargs = captured_delay_calls[0]

        # 2. Delivered activity must be of type Follow
        activity = call_kwargs.get("activity", {})
        assert activity.get("type") == "Follow", (
            f"Activity must be Follow, got {activity.get('type')}"
        )

        # 3. Actor must be the local user
        assert activity.get("actor") == local_federation_user.actor_url, (
            f"Follow actor must be {local_federation_user.actor_url}, got {activity.get('actor')}"
        )

        # 4. Object must be the remote actor
        assert activity.get("object") == peer_actor, (
            f"Follow object must be {peer_actor}, got {activity.get('object')}"
        )

        # 5. Inbox URL must be the remote actor's inbox
        assert call_kwargs.get("inbox_url") == remote_inbox, (
            f"inbox_url must be {remote_inbox}, got {call_kwargs.get('inbox_url')}"
        )

        # 6. Signing keys must be present and correct
        assert call_kwargs.get("actor_key_id") == f"{local_federation_user.actor_url}#main-key", (
            "actor_key_id must be the local user's key id"
        )
        assert call_kwargs.get("private_key_pem") == local_federation_user.private_key, (
            "private_key_pem must be the local user's private key"
        )


# ---------------------------------------------------------------------------
# Flow: Unfollow — Undo(Follow)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUnfollowIncoming:
    """Remote actor sends Undo(Follow) — inbox must remove the Follow from DB."""

    def test_unfollow_incoming_removes_follow(
        self,
        rf: RequestFactory,
        local_federation_user: Any,
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        RED: inbox.handle_undo must delete the Follow record when receiving
        Undo{object: {type: Follow}} from a remote actor.

        Contract:
        - A Follow record exists in DB (remote=True, follower=remote_user)
        - Inbox receives Undo(Follow) signed by remote actor
        - Follow record must be deleted after processing
        """
        from django.contrib.contenttypes.models import ContentType

        from suddenly.activitypub.inbox import process_inbox
        from suddenly.characters.models import Follow
        from suddenly.users.models import User

        remote_private_pem, remote_public_pem = generate_key_pair()
        remote_actor_url = "https://peer.suddenly.test/users/remote_bob"
        remote_inbox_url = "https://peer.suddenly.test/users/remote_bob/inbox"

        actor_data = {
            "id": remote_actor_url,
            "type": "Person",
            "preferredUsername": "remote_bob",
            "name": "Remote Bob",
            "inbox": remote_inbox_url,
            "outbox": "https://peer.suddenly.test/users/remote_bob/outbox",
            "publicKey": {
                "id": f"{remote_actor_url}#main-key",
                "owner": remote_actor_url,
                "publicKeyPem": remote_public_pem,
            },
        }

        mock_http_response = MagicMock()
        mock_http_response.json.return_value = actor_data
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.get.return_value = mock_http_response
        mocker.patch("httpx.Client", return_value=mock_client_instance)

        mocker.patch(
            "suddenly.activitypub.inbox.verify_signature",
            return_value=(True, f"{remote_actor_url}#main-key"),
        )
        mocker.patch("suddenly.activitypub.inbox._check_rate_limit", return_value=False)

        # Create the remote user and the Follow record in DB first
        remote_user = User.objects.create(
            username="remote_bob",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=remote_inbox_url,
        )
        content_type = ContentType.objects.get_for_model(User)
        follow = Follow.objects.create(
            follower=remote_user,
            content_type=content_type,
            object_id=local_federation_user.pk,
            remote=True,
            ap_id=f"{remote_actor_url}#follow-abc123",
        )

        assert Follow.objects.filter(pk=follow.pk).exists(), "Follow must exist before Undo"

        undo_activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Undo",
            "id": f"{remote_actor_url}#undo-abc123",
            "actor": remote_actor_url,
            "object": {
                "type": "Follow",
                "id": f"{remote_actor_url}#follow-abc123",
                "actor": remote_actor_url,
                "object": local_federation_user.actor_url,
            },
        }

        path = f"/users/{local_federation_user.username}/inbox"
        request = rf.post(
            path,
            data=json.dumps(undo_activity),
            content_type="application/activity+json",
            HTTP_HOST="local.suddenly.test",
            HTTP_SIGNATURE=(
                f'keyId="{remote_actor_url}#main-key",'
                'headers="(request-target) host date",signature="dummy"'
            ),
        )

        response = process_inbox(
            request,
            actor_type="user",
            actor_identifier=local_federation_user.username,
        )

        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        assert not Follow.objects.filter(pk=follow.pk).exists(), (
            "Follow record must be deleted after receiving Undo(Follow)"
        )


@pytest.mark.django_db
class TestUnfollowOutgoing:
    """Local user unfollows a remote actor.

    send_undo_follow_activity must deliver a signed Undo(Follow).
    """

    def test_unfollow_outgoing_sends_undo(
        self,
        local_federation_user: Any,
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        RED: send_undo_follow_activity must call deliver_activity.delay with:
        - activity of type Undo wrapping a Follow
        - inbox_url = remote actor's inbox
        - actor_key_id = local user's key id
        - private_key_pem = local user's private key

        Requires a Follow record in DB with ap_id set so the Undo can reference it.
        """
        from django.contrib.contenttypes.models import ContentType

        from suddenly.activitypub.tasks import send_undo_follow_activity
        from suddenly.characters.models import Follow
        from suddenly.users.models import User

        peer_actor = "https://test.suddenly.social/users/testbot"
        remote_inbox = f"{peer_actor}/inbox"
        follow_ap_id = f"{local_federation_user.actor_url}#follow-xyz789"

        # Patch deliver_activity before Follow creation so the follow_post_save
        # signal does not fire a real HTTP request during Follow.objects.create().
        captured_delay_calls: list[dict[str, Any]] = []

        def fake_delay(**kwargs: Any) -> None:
            captured_delay_calls.append(kwargs)

        mock_deliver = mocker.MagicMock()
        mock_deliver.delay.side_effect = fake_delay
        mocker.patch("suddenly.activitypub.tasks.deliver_activity", mock_deliver)
        # Suppress all signal-triggered task dispatches (follow_post_save fires
        # on Follow creation and would try to reach a real remote inbox).
        mocker.patch("suddenly.activitypub.signals._safe_delay")

        # Create the remote user
        remote_user = User.objects.create(
            username="testbot",
            remote=True,
            ap_id=peer_actor,
            inbox_url=remote_inbox,
        )

        # Create the Follow record the local user wants to undo.
        # The follow_post_save signal fires here — it will use the mock above.
        content_type = ContentType.objects.get_for_model(User)
        Follow.objects.create(
            follower=local_federation_user,
            content_type=content_type,
            object_id=remote_user.pk,
            remote=False,
            ap_id=follow_ap_id,
        )

        # Reset captured calls: the signal may have called mock_deliver.delay once
        # for the Follow creation itself. We only want to track the Undo delivery.
        captured_delay_calls.clear()

        send_undo_follow_activity(str(local_federation_user.pk), peer_actor)

        # 1. deliver_activity.delay must be called exactly once
        assert len(captured_delay_calls) == 1, (
            f"deliver_activity.delay must be called once, got {len(captured_delay_calls)}"
        )

        call_kwargs = captured_delay_calls[0]

        # 2. Activity must be Undo wrapping a Follow
        activity = call_kwargs.get("activity", {})
        assert activity.get("type") == "Undo", (
            f"Activity type must be Undo, got {activity.get('type')}"
        )
        inner = activity.get("object", {})
        assert inner.get("type") == "Follow", f"Undo object must be Follow, got {inner.get('type')}"
        assert inner.get("id") == follow_ap_id, (
            f"Undo object id must match Follow ap_id {follow_ap_id}, got {inner.get('id')}"
        )

        # 3. Actor must be the local user
        assert activity.get("actor") == local_federation_user.actor_url, (
            f"Undo actor must be {local_federation_user.actor_url}"
        )

        # 4. Delivery target must be remote inbox
        assert call_kwargs.get("inbox_url") == remote_inbox, (
            f"inbox_url must be {remote_inbox}, got {call_kwargs.get('inbox_url')}"
        )

        # 5. Signing keys must be present and correct
        assert call_kwargs.get("actor_key_id") == f"{local_federation_user.actor_url}#main-key", (
            "actor_key_id must be the local user's key id"
        )
        assert call_kwargs.get("private_key_pem") == local_federation_user.private_key, (
            "private_key_pem must be the local user's private key"
        )

        # 6. Follow record must be deleted after sending Undo
        assert not Follow.objects.filter(ap_id=follow_ap_id).exists(), (
            "Follow record must be deleted after send_undo_follow_activity"
        )


# ---------------------------------------------------------------------------
# Flow: Offer/Accept/Reject — LinkRequest cross-instance
# ---------------------------------------------------------------------------


@pytest.fixture
def local_character_with_remote_creator(db: Any, settings: Any) -> tuple[Any, Any]:
    """A local NPC character whose creator is a remote user (Railway instance)."""
    settings.DOMAIN = "local.suddenly.test"
    settings.AP_BASE_URL = "https://local.suddenly.test"

    from suddenly.characters.models import Character, CharacterStatus
    from suddenly.games.models import Game
    from suddenly.users.models import User

    remote_creator = User.objects.create(
        username="remote_creator@railway.suddenly.test",
        remote=True,
        ap_id="https://railway.suddenly.test/users/remote_creator",
        inbox_url="https://railway.suddenly.test/users/remote_creator/inbox",
    )

    owner = User.objects.create(username="local_owner", remote=False)
    game = Game.objects.create(title="Test Game", owner=owner)

    character = Character.objects.create(
        name="Luna",
        status=CharacterStatus.NPC,
        creator=remote_creator,
        origin_game=game,
        ap_id="https://local.suddenly.test/characters/luna",
    )

    return character, remote_creator


@pytest.fixture
def local_requester_with_key(db: Any, settings: Any) -> Any:
    """A local user with a generated key pair, to be the requester in Offer flows."""
    settings.DOMAIN = "local.suddenly.test"
    settings.AP_BASE_URL = "https://local.suddenly.test"

    from suddenly.activitypub.signatures import generate_key_pair

    private_pem, public_pem = generate_key_pair()

    return UserFactory(
        username="local_requester",
        display_name="Local Requester",
        remote=False,
        public_key=public_pem,
        private_key=private_pem,
    )


@pytest.mark.django_db
class TestOfferIncoming:
    """Remote actor sends Offer(Relationship) — inbox must create a PENDING LinkRequest."""

    def test_offer_incoming_creates_link_request(
        self,
        rf: RequestFactory,
        local_character_with_remote_creator: tuple[Any, Any],
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        inbox.handle_offer must create a LinkRequest with status PENDING when
        receiving a canonical Offer (object.type=='suddenly:Adopt', DEC-038) from
        a remote actor targeting a local NPC.

        Contract:
        - Remote actor POSTs Offer to local character inbox
        - Activity has object.type=='suddenly:Adopt', target=NPC actor URL
        - A LinkRequest must be created in DB with status PENDING
        - requester must be the remote actor (get_or_create_remote_user)
        - target_character must be the local NPC
        """
        from suddenly.activitypub.inbox import process_inbox
        from suddenly.characters.models import LinkRequest, LinkRequestStatus, LinkType

        character, remote_creator = local_character_with_remote_creator

        remote_requester_url = "https://railway.suddenly.test/users/remote_requester"
        remote_requester_inbox = f"{remote_requester_url}/inbox"

        actor_data = {
            "id": remote_requester_url,
            "type": "Person",
            "preferredUsername": "remote_requester",
            "name": "Remote Requester",
            "inbox": remote_requester_inbox,
            "outbox": f"{remote_requester_url}/outbox",
            "publicKey": {
                "id": f"{remote_requester_url}#main-key",
                "owner": remote_requester_url,
                "publicKeyPem": "fake-public-key-pem",
            },
        }

        mock_http_response = MagicMock()
        mock_http_response.json.return_value = actor_data
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.get.return_value = mock_http_response
        mocker.patch("httpx.Client", return_value=mock_client_instance)

        mocker.patch(
            "suddenly.activitypub.inbox.verify_signature",
            return_value=(True, f"{remote_requester_url}#main-key"),
        )
        mocker.patch("suddenly.activitypub.inbox._check_rate_limit", return_value=False)

        # Offer activity from Railway: remote actor wants to adopt the local NPC.
        # Canonical Suddenly format (DEC-038): object.type=suddenly:Adopt, target NPC
        # in top-level `target`, narrative message in object.content. The legacy
        # Relationship form is no longer accepted.
        offer_activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Offer",
            "id": f"{remote_requester_url}/link-requests/adopt-luna",
            "actor": remote_requester_url,
            "target": character.actor_url,
            "object": {
                "type": "suddenly:Adopt",
                "content": "I'd love to adopt Luna",
            },
        }

        path = f"/characters/{character.pk}/inbox"
        request = rf.post(
            path,
            data=json.dumps(offer_activity),
            content_type="application/activity+json",
            HTTP_HOST="local.suddenly.test",
            HTTP_SIGNATURE=(
                f'keyId="{remote_requester_url}#main-key",'
                'headers="(request-target) host date",signature="dummy"'
            ),
        )

        response = process_inbox(
            request,
            actor_type="character",
            actor_identifier=str(character.pk),
        )

        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        # A LinkRequest must have been created
        lr = LinkRequest.objects.filter(
            target_character=character,
            type=LinkType.ADOPT,
        ).first()

        assert lr is not None, (
            "A LinkRequest must be created in DB when an Offer(Relationship{adopt}) is received"
        )
        assert lr.status == LinkRequestStatus.PENDING, (
            f"LinkRequest status must be PENDING, got {lr.status}"
        )
        assert lr.requester.ap_id == remote_requester_url, (
            f"Requester ap_id must be {remote_requester_url}, got {lr.requester.ap_id}"
        )
        assert lr.message == "I'd love to adopt Luna", (
            "LinkRequest message must match activity summary"
        )


@pytest.mark.django_db
class TestAcceptIncoming:
    """
    Railway instance sends Accept(Offer) — inbox must update our LinkRequest to ACCEPTED
    and the CharacterLink must be created.
    """

    def test_accept_incoming_updates_link_request(
        self,
        rf: RequestFactory,
        local_character_with_remote_creator: tuple[Any, Any],
        local_requester_with_key: Any,
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        RED: inbox.handle_accept must update LinkRequest.status to ACCEPTED when
        receiving Accept(Offer) where the object is our original Offer URL
        (format: https://local.suddenly.test/link-requests/{pk}).

        Bug: current code looks for '/activities/offer/' in the offer_id,
        but serialize_link_request generates '/link-requests/{pk}'.
        Fix: extract UUID from '/link-requests/{pk}' pattern.

        Contract:
        - A PENDING LinkRequest exists locally
        - Railway POSTs Accept whose object is the Offer URL
        - LinkRequest.status must become ACCEPTED after processing
        """
        from suddenly.activitypub.inbox import process_inbox
        from suddenly.characters.models import LinkRequest, LinkRequestStatus, LinkType

        character, remote_creator = local_character_with_remote_creator
        requester = local_requester_with_key

        mocker.patch(
            "suddenly.activitypub.inbox.verify_signature",
            return_value=(True, f"{remote_creator.ap_id}#main-key"),
        )
        mocker.patch("suddenly.activitypub.inbox._check_rate_limit", return_value=False)
        # Suppress signal-triggered task dispatches: link_request_post_save fires
        # on LinkRequest.create (→ send_offer_activity) and on lr.save() with
        # status=ACCEPTED (→ send_accept_activity → deliver_activity HTTP POST).
        mocker.patch("suddenly.activitypub.signals._safe_delay")

        # Create the PENDING LinkRequest as if we sent an Offer to Railway
        lr = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=requester,
            target_character=character,
            message="Please accept my adoption request",
            status=LinkRequestStatus.PENDING,
        )

        # The offer URL that our serializer would have generated
        offer_url = f"https://local.suddenly.test/link-requests/{lr.pk}"

        # Accept activity from Railway: they accept our Offer
        accept_activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Accept",
            "id": f"{remote_creator.ap_id}/activities/accept/{lr.pk}",
            "actor": remote_creator.ap_id,
            "object": offer_url,
            "summary": "Adoption accepted, welcome Luna!",
        }

        path = f"/users/{requester.username}/inbox"
        request = rf.post(
            path,
            data=json.dumps(accept_activity),
            content_type="application/activity+json",
            HTTP_HOST="local.suddenly.test",
            HTTP_SIGNATURE=(
                f'keyId="{remote_creator.ap_id}#main-key",'
                'headers="(request-target) host date",signature="dummy"'
            ),
        )

        response = process_inbox(
            request,
            actor_type="user",
            actor_identifier=requester.username,
        )

        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        lr.refresh_from_db()
        assert lr.status == LinkRequestStatus.ACCEPTED, (
            f"LinkRequest status must be ACCEPTED after Accept activity, got {lr.status}. "
            f"Bug: handle_accept looks for '/activities/offer/' in offer URL but "
            f"serialize_link_request generates '/link-requests/{{pk}}'."
        )
        assert lr.response_message == "Adoption accepted, welcome Luna!", (
            "response_message must be set from activity summary"
        )


@pytest.mark.django_db
class TestRejectIncoming:
    """
    Railway instance sends Reject(Offer) — inbox must update our LinkRequest to REJECTED.
    """

    def test_reject_incoming_updates_link_request(
        self,
        rf: RequestFactory,
        local_character_with_remote_creator: tuple[Any, Any],
        local_requester_with_key: Any,
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        RED: inbox.handle_reject must update LinkRequest.status to REJECTED when
        receiving Reject(Offer) where the object is our original Offer URL
        (format: https://local.suddenly.test/link-requests/{pk}).

        Same bug as handle_accept: URL pattern mismatch.
        """
        from suddenly.activitypub.inbox import process_inbox
        from suddenly.characters.models import LinkRequest, LinkRequestStatus, LinkType

        character, remote_creator = local_character_with_remote_creator
        requester = local_requester_with_key

        mocker.patch(
            "suddenly.activitypub.inbox.verify_signature",
            return_value=(True, f"{remote_creator.ap_id}#main-key"),
        )
        mocker.patch("suddenly.activitypub.inbox._check_rate_limit", return_value=False)
        # Suppress signal-triggered task dispatches: link_request_post_save fires
        # on LinkRequest.create (→ send_offer_activity) and on lr.save() with
        # status=REJECTED (→ send_reject_activity → deliver_activity HTTP POST).
        mocker.patch("suddenly.activitypub.signals._safe_delay")

        lr = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=requester,
            target_character=character,
            message="Please accept my adoption request",
            status=LinkRequestStatus.PENDING,
        )

        offer_url = f"https://local.suddenly.test/link-requests/{lr.pk}"

        reject_activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Reject",
            "id": f"{remote_creator.ap_id}/activities/reject/{lr.pk}",
            "actor": remote_creator.ap_id,
            "object": offer_url,
            "summary": "Not compatible with our game, sorry.",
        }

        path = f"/users/{requester.username}/inbox"
        request = rf.post(
            path,
            data=json.dumps(reject_activity),
            content_type="application/activity+json",
            HTTP_HOST="local.suddenly.test",
            HTTP_SIGNATURE=(
                f'keyId="{remote_creator.ap_id}#main-key",'
                'headers="(request-target) host date",signature="dummy"'
            ),
        )

        response = process_inbox(
            request,
            actor_type="user",
            actor_identifier=requester.username,
        )

        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        lr.refresh_from_db()
        assert lr.status == LinkRequestStatus.REJECTED, (
            f"LinkRequest status must be REJECTED after Reject activity, got {lr.status}. "
            f"Bug: handle_reject looks for '/activities/offer/' in offer URL but "
            f"serialize_link_request generates '/link-requests/{{pk}}'."
        )
        assert lr.response_message == "Not compatible with our game, sorry.", (
            "response_message must be set from activity summary"
        )


@pytest.mark.django_db
class TestOfferOutgoing:
    """Local user sends an Offer to a remote character's creator — deliver must be signed."""

    def test_offer_outgoing_sends_to_remote_creator(
        self,
        local_character_with_remote_creator: tuple[Any, Any],
        local_requester_with_key: Any,
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        RED: send_offer_activity must call deliver_activity.delay with:
        - activity of type Offer
        - inbox_url = remote creator's inbox_url
        - actor_key_id = requester's key id
        - private_key_pem = requester's private key

        Bug: current send_offer_activity does not pass signing keys to
        deliver_activity.delay — the Offer would be sent unsigned.
        """
        from suddenly.activitypub.tasks import send_offer_activity
        from suddenly.characters.models import LinkRequest, LinkRequestStatus, LinkType

        character, remote_creator = local_character_with_remote_creator
        requester = local_requester_with_key

        # Mock deliver_activity BEFORE creating the LinkRequest to prevent the
        # post_save signal from triggering a real HTTP delivery attempt.
        captured_delay_calls: list[dict[str, Any]] = []

        def fake_delay(*args: Any, **kwargs: Any) -> None:
            # Normalise positional args to their named equivalents so assertions
            # can use call_kwargs.get("activity") / call_kwargs.get("inbox_url").
            param_names = ["activity", "inbox_url", "actor_key_id", "private_key_pem"]
            normalised = dict(zip(param_names, args, strict=False))
            normalised.update(kwargs)
            captured_delay_calls.append(normalised)

        mock_deliver = mocker.MagicMock()
        mock_deliver.delay.side_effect = fake_delay
        mocker.patch("suddenly.activitypub.tasks.deliver_activity", mock_deliver)

        lr = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=requester,
            target_character=character,
            message="I want to adopt Luna",
            status=LinkRequestStatus.PENDING,
        )

        # Reset captured calls — signal may have fired deliver_activity.delay once
        # already (via post_save). We only want to assert on the explicit call below.
        captured_delay_calls.clear()

        send_offer_activity(str(lr.pk))

        # 1. deliver_activity.delay must be called exactly once
        assert len(captured_delay_calls) == 1, (
            f"deliver_activity.delay must be called once, got {len(captured_delay_calls)}. "
            f"Check that creator.remote is True and creator.inbox_url is set."
        )

        call_kwargs = captured_delay_calls[0]

        # 2. Activity must be Offer
        activity = call_kwargs.get("activity", {})
        assert activity.get("type") == "Offer", (
            f"Activity must be Offer, got {activity.get('type')}"
        )

        # 3. Delivery target must be remote creator's inbox
        assert call_kwargs.get("inbox_url") == remote_creator.inbox_url, (
            f"inbox_url must be {remote_creator.inbox_url}, got {call_kwargs.get('inbox_url')}"
        )

        # 4. Signing keys must be present and correct
        assert "actor_key_id" in call_kwargs, (
            "deliver_activity.delay must receive actor_key_id"
            " — Offer would be unsigned without it."
            " Bug: send_offer_activity calls deliver_activity.delay(activity, creator.inbox_url)"
            " without passing actor_key_id or private_key_pem."
        )
        assert call_kwargs["actor_key_id"] == f"{requester.actor_url}#main-key", (
            f"actor_key_id must be requester's key id, got {call_kwargs.get('actor_key_id')}"
        )
        assert "private_key_pem" in call_kwargs, (
            "deliver_activity.delay must receive private_key_pem"
        )
        assert call_kwargs["private_key_pem"] == requester.private_key, (
            "private_key_pem must be requester's private key"
        )


# ---------------------------------------------------------------------------
# Flow: Create incoming (remote actor publishes a Character)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateIncoming:
    """Remote actor sends Create(Character) — inbox must create a local remote Character."""

    def test_create_incoming_character_creates_db_record(
        self,
        rf: RequestFactory,
        local_federation_user: Any,
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        RED: handle_create must persist a remote Character to the DB when it
        receives Create(Character).

        Current stub only logs — no Character is created.
        """
        from suddenly.activitypub.inbox import process_inbox
        from suddenly.characters.models import Character

        remote_actor_url = "https://peer.suddenly.test/users/remote_sender"
        character_ap_id = "https://peer.suddenly.test/characters/aria"
        private_pem, public_pem = generate_key_pair()

        # Register remote user so signature verification can find the public key
        UserFactory(
            username="remote_sender@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
            public_key=public_pem,
        )

        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Create",
            "id": f"{remote_actor_url}#create-aria",
            "actor": remote_actor_url,
            "object": {
                "type": "Character",
                "id": character_ap_id,
                "name": "Aria",
                "summary": "A mysterious bard",
                "attributedTo": remote_actor_url,
            },
        }

        path = f"/users/{local_federation_user.username}/inbox"
        request = _make_signed_inbox_request(rf, activity, remote_actor_url, private_pem, path)

        mocker.patch(
            "suddenly.activitypub.inbox.verify_signature",
            return_value=(True, ""),
        )
        mocker.patch(
            "suddenly.activitypub.inbox._check_rate_limit",
            return_value=False,
        )

        response = process_inbox(
            request,
            actor_type="user",
            actor_identifier=local_federation_user.username,
        )

        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        assert Character.objects.filter(ap_id=character_ap_id, remote=True).exists(), (
            "handle_create must create a remote Character with remote=True and ap_id set. "
            "Current stub only logs — no DB record is created."
        )

        character = Character.objects.get(ap_id=character_ap_id)
        assert character.name == "Aria", f"Character name must be 'Aria', got '{character.name}'"


# ---------------------------------------------------------------------------
# Flow: Update incoming (remote actor updates a Character)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUpdateIncoming:
    """Remote actor sends Update(Character) — inbox must update the existing record."""

    def test_update_incoming_character_updates_db_record(
        self,
        rf: RequestFactory,
        local_federation_user: Any,
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        RED: handle_update must update a remote Character's fields when it
        receives Update(Character).

        Current stub only logs — no record is updated.
        """
        from suddenly.activitypub.inbox import process_inbox
        from suddenly.characters.models import Character, CharacterStatus

        remote_actor_url = "https://peer.suddenly.test/users/remote_sender"
        character_ap_id = "https://peer.suddenly.test/characters/aria"
        private_pem, public_pem = generate_key_pair()

        remote_user = UserFactory(
            username="remote_sender@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
            public_key=public_pem,
        )

        # Pre-existing remote character in DB
        from suddenly.games.models import Game

        game = Game.objects.create(title="Remote Game", owner=remote_user, remote=True)
        character = Character.objects.create(
            name="Aria",
            description="Old description",
            status=CharacterStatus.NPC,
            creator=remote_user,
            origin_game=game,
            remote=True,
            ap_id=character_ap_id,
        )

        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Update",
            "id": f"{remote_actor_url}#update-aria",
            "actor": remote_actor_url,
            "object": {
                "type": "Character",
                "id": character_ap_id,
                "name": "Aria Updated",
                "summary": "A legendary bard",
            },
        }

        path = f"/users/{local_federation_user.username}/inbox"
        request = _make_signed_inbox_request(rf, activity, remote_actor_url, private_pem, path)

        mocker.patch(
            "suddenly.activitypub.inbox.verify_signature",
            return_value=(True, ""),
        )
        mocker.patch(
            "suddenly.activitypub.inbox._check_rate_limit",
            return_value=False,
        )

        response = process_inbox(
            request,
            actor_type="user",
            actor_identifier=local_federation_user.username,
        )

        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        character.refresh_from_db()
        assert character.name == "Aria Updated", (
            f"Character name must be 'Aria Updated' after Update, got '{character.name}'. "
            "Current stub only logs — no record is updated."
        )
        assert character.description == "A legendary bard", (
            f"Character description must be 'A legendary bard', got '{character.description}'"
        )


# ---------------------------------------------------------------------------
# Flow: Delete incoming (remote actor deletes a Character)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# View: remote_follow_toggle
# ---------------------------------------------------------------------------


@pytest.fixture
def local_user_with_key(db: Any, settings: Any) -> Any:
    """Local user with a generated RSA key pair for federation."""
    settings.DOMAIN = "local.suddenly.test"
    settings.AP_BASE_URL = "https://local.suddenly.test"

    private_pem, public_pem = generate_key_pair()

    return UserFactory(
        username="local_toggle_user",
        display_name="Local Toggle User",
        remote=False,
        public_key=public_pem,
        private_key=private_pem,
    )


@pytest.mark.django_db
class TestRemoteFollowToggle:
    """View remote_follow_toggle — Follow and Unfollow branches."""

    # ------------------------------------------------------------------
    # Follow (no existing Follow record)
    # ------------------------------------------------------------------

    def test_follow_creates_follow_record(
        self,
        local_user_with_key: Any,
        settings: Any,
    ) -> None:
        """
        POST with ap_id when no Follow exists must create a Follow with the
        expected ap_id and enqueue send_follow_activity.delay.
        """
        from django.contrib.contenttypes.models import ContentType
        from django.test import Client

        from suddenly.characters.models import Follow
        from suddenly.users.models import User as UserModel

        remote_actor_url = "https://peer.suddenly.test/users/remote_charlie"
        remote_user = UserModel.objects.create(
            username="remote_charlie@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
        )

        client = Client()
        client.force_login(local_user_with_key)

        with (
            patch(
                "suddenly.activitypub._http.fetch_ap_actor",
                return_value={"type": "Person", "id": remote_actor_url},
            ),
            patch(
                "suddenly.activitypub.tasks.get_or_create_remote_user",
                return_value=remote_user,
            ),
            patch("suddenly.activitypub.tasks.send_follow_activity") as mock_follow_task,
            patch("suddenly.activitypub.signals._safe_delay"),
        ):
            mock_follow_task.delay = MagicMock()
            response = client.post(
                "/federation/remote/follow/",
                {"ap_id": remote_actor_url},
            )

        assert response.status_code == 200

        ct = ContentType.objects.get_for_model(UserModel)
        follow = Follow.objects.filter(
            follower=local_user_with_key,
            content_type=ct,
            object_id=remote_user.pk,
        ).first()
        assert follow is not None, "Follow record must be created"

        expected_ap_id = (
            f"https://{settings.DOMAIN}/users/{local_user_with_key.username}"
            f"/follows/{remote_user.pk}"
        )
        assert follow.ap_id == expected_ap_id, (
            f"Follow ap_id must be {expected_ap_id}, got {follow.ap_id}"
        )

    def test_follow_enqueues_send_follow_activity(
        self,
        local_user_with_key: Any,
        settings: Any,
    ) -> None:
        """
        POST follow must enqueue send_follow_activity.delay with
        (user_id, ap_id, follow_ap_id).
        """
        from django.test import Client

        from suddenly.users.models import User as UserModel

        remote_actor_url = "https://peer.suddenly.test/users/remote_charlie"
        remote_user = UserModel.objects.create(
            username="remote_charlie2@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
        )

        client = Client()
        client.force_login(local_user_with_key)

        captured_delay_calls: list[tuple[Any, ...]] = []

        def fake_delay(*args: Any, **kwargs: Any) -> None:
            captured_delay_calls.append((args, kwargs))

        with (
            patch(
                "suddenly.activitypub._http.fetch_ap_actor",
                return_value={"type": "Person", "id": remote_actor_url},
            ),
            patch(
                "suddenly.activitypub.tasks.get_or_create_remote_user",
                return_value=remote_user,
            ),
            patch("suddenly.activitypub.tasks.send_follow_activity") as mock_task,
            patch("suddenly.activitypub.signals._safe_delay"),
        ):
            mock_task.delay.side_effect = fake_delay
            response = client.post(
                "/federation/remote/follow/",
                {"ap_id": remote_actor_url},
            )

        assert response.status_code == 200
        assert len(captured_delay_calls) == 1, (
            f"send_follow_activity.delay must be called once, got {len(captured_delay_calls)}"
        )

        args, kwargs = captured_delay_calls[0]
        # Called as send_follow_activity.delay(user_id, ap_id, follow_ap_id)
        list(args) + [kwargs.get(k) for k in ("user_id", "ap_id", "follow_ap_id") if k in kwargs]
        positional = list(args)
        assert positional[0] == str(local_user_with_key.pk), (
            f"First arg must be user_id={local_user_with_key.pk}"
        )
        assert positional[1] == remote_actor_url, f"Second arg must be ap_id={remote_actor_url}"
        expected_ap_id = (
            f"https://{settings.DOMAIN}/users/{local_user_with_key.username}"
            f"/follows/{remote_user.pk}"
        )
        assert positional[2] == expected_ap_id, f"Third arg must be follow_ap_id={expected_ap_id}"

    def test_follow_returns_is_following_true(
        self,
        local_user_with_key: Any,
        settings: Any,
    ) -> None:
        """
        After a follow POST, the rendered template context must have
        is_following=True and status code 200.
        """
        from django.test import Client

        from suddenly.users.models import User as UserModel

        remote_actor_url = "https://peer.suddenly.test/users/remote_delta"
        remote_user = UserModel.objects.create(
            username="remote_delta@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
        )

        client = Client()
        client.force_login(local_user_with_key)

        with (
            patch(
                "suddenly.activitypub._http.fetch_ap_actor",
                return_value={"type": "Person", "id": remote_actor_url},
            ),
            patch(
                "suddenly.activitypub.tasks.get_or_create_remote_user",
                return_value=remote_user,
            ),
            patch("suddenly.activitypub.tasks.send_follow_activity") as mock_task,
            patch("suddenly.activitypub.signals._safe_delay"),
        ):
            mock_task.delay = MagicMock()
            response = client.post(
                "/federation/remote/follow/",
                {"ap_id": remote_actor_url},
            )

        assert response.status_code == 200
        assert response.context["is_following"] is True, (
            "Context is_following must be True after follow"
        )

    # ------------------------------------------------------------------
    # Unfollow (existing Follow record present)
    # ------------------------------------------------------------------

    def test_unfollow_enqueues_send_undo_follow_activity(
        self,
        local_user_with_key: Any,
        settings: Any,
    ) -> None:
        """
        POST when a Follow already exists must enqueue
        send_undo_follow_activity.delay(user_id, ap_id).
        """
        from django.contrib.contenttypes.models import ContentType
        from django.test import Client

        from suddenly.characters.models import Follow
        from suddenly.users.models import User as UserModel

        remote_actor_url = "https://peer.suddenly.test/users/remote_echo"
        remote_user = UserModel.objects.create(
            username="remote_echo@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
        )

        ct = ContentType.objects.get_for_model(UserModel)
        # Suppress signals during Follow creation to avoid eager HTTP delivery
        with patch("suddenly.activitypub.signals._safe_delay"):
            Follow.objects.create(
                follower=local_user_with_key,
                content_type=ct,
                object_id=remote_user.pk,
                remote=False,
                ap_id=f"https://{settings.DOMAIN}/users/{local_user_with_key.username}/follows/{remote_user.pk}",
            )

        client = Client()
        client.force_login(local_user_with_key)

        captured_delay_calls: list[tuple[Any, ...]] = []

        def fake_delay(*args: Any, **kwargs: Any) -> None:
            captured_delay_calls.append((args, kwargs))

        with (
            patch(
                "suddenly.activitypub._http.fetch_ap_actor",
                return_value={"type": "Person", "id": remote_actor_url},
            ),
            patch(
                "suddenly.activitypub.tasks.get_or_create_remote_user",
                return_value=remote_user,
            ),
            patch("suddenly.activitypub.tasks.send_undo_follow_activity") as mock_task,
        ):
            mock_task.delay.side_effect = fake_delay
            response = client.post(
                "/federation/remote/follow/",
                {"ap_id": remote_actor_url},
            )

        assert response.status_code == 200
        assert len(captured_delay_calls) == 1, (
            f"send_undo_follow_activity.delay must be called once, got {len(captured_delay_calls)}"
        )
        args, kwargs = captured_delay_calls[0]
        positional = list(args)
        assert positional[0] == str(local_user_with_key.pk), "First arg must be user_id"
        assert positional[1] == remote_actor_url, "Second arg must be ap_id"

    def test_unfollow_does_not_delete_follow_locally(
        self,
        local_user_with_key: Any,
        settings: Any,
    ) -> None:
        """
        The view must NOT delete the Follow record — deletion is the task's job.
        """
        from django.contrib.contenttypes.models import ContentType
        from django.test import Client

        from suddenly.characters.models import Follow
        from suddenly.users.models import User as UserModel

        remote_actor_url = "https://peer.suddenly.test/users/remote_foxtrot"
        remote_user = UserModel.objects.create(
            username="remote_foxtrot@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
        )

        ct = ContentType.objects.get_for_model(UserModel)
        # Suppress signals during Follow creation to avoid eager HTTP delivery
        with patch("suddenly.activitypub.signals._safe_delay"):
            existing_follow = Follow.objects.create(
                follower=local_user_with_key,
                content_type=ct,
                object_id=remote_user.pk,
                remote=False,
                ap_id=f"https://{settings.DOMAIN}/users/{local_user_with_key.username}/follows/{remote_user.pk}",
            )
        follow_pk = existing_follow.pk

        client = Client()
        client.force_login(local_user_with_key)

        with (
            patch(
                "suddenly.activitypub._http.fetch_ap_actor",
                return_value={"type": "Person", "id": remote_actor_url},
            ),
            patch(
                "suddenly.activitypub.tasks.get_or_create_remote_user",
                return_value=remote_user,
            ),
            patch("suddenly.activitypub.tasks.send_undo_follow_activity") as mock_task,
        ):
            mock_task.delay = MagicMock()
            response = client.post(
                "/federation/remote/follow/",
                {"ap_id": remote_actor_url},
            )

        assert response.status_code == 200
        assert Follow.objects.filter(pk=follow_pk).exists(), (
            "View must NOT delete the Follow record — deletion belongs to the Celery task"
        )

    def test_unfollow_returns_is_following_false(
        self,
        local_user_with_key: Any,
        settings: Any,
    ) -> None:
        """
        Unfollow POST must return 200 with is_following=False in context.
        """
        from django.contrib.contenttypes.models import ContentType
        from django.test import Client

        from suddenly.characters.models import Follow
        from suddenly.users.models import User as UserModel

        remote_actor_url = "https://peer.suddenly.test/users/remote_golf"
        remote_user = UserModel.objects.create(
            username="remote_golf@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
        )

        ct = ContentType.objects.get_for_model(UserModel)
        # Suppress signals during Follow creation to avoid eager HTTP delivery
        with patch("suddenly.activitypub.signals._safe_delay"):
            Follow.objects.create(
                follower=local_user_with_key,
                content_type=ct,
                object_id=remote_user.pk,
                remote=False,
                ap_id=f"https://{settings.DOMAIN}/users/{local_user_with_key.username}/follows/{remote_user.pk}",
            )

        client = Client()
        client.force_login(local_user_with_key)

        with (
            patch(
                "suddenly.activitypub._http.fetch_ap_actor",
                return_value={"type": "Person", "id": remote_actor_url},
            ),
            patch(
                "suddenly.activitypub.tasks.get_or_create_remote_user",
                return_value=remote_user,
            ),
            patch("suddenly.activitypub.tasks.send_undo_follow_activity") as mock_task,
        ):
            mock_task.delay = MagicMock()
            response = client.post(
                "/federation/remote/follow/",
                {"ap_id": remote_actor_url},
            )

        assert response.status_code == 200
        assert response.context["is_following"] is False, (
            "Context is_following must be False after unfollow"
        )

    # ------------------------------------------------------------------
    # action= field mismatch — view decides by DB state, not POST field
    # ------------------------------------------------------------------

    def test_action_field_ignored_when_no_follow_exists(
        self,
        local_user_with_key: Any,
        settings: Any,
    ) -> None:
        """
        Even if action=unfollow is sent, when no Follow exists the view
        must follow (not unfollow), because the decision is based on DB state.
        """
        from django.contrib.contenttypes.models import ContentType
        from django.test import Client

        from suddenly.characters.models import Follow
        from suddenly.users.models import User as UserModel

        remote_actor_url = "https://peer.suddenly.test/users/remote_hotel"
        remote_user = UserModel.objects.create(
            username="remote_hotel@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
        )

        client = Client()
        client.force_login(local_user_with_key)

        with (
            patch(
                "suddenly.activitypub._http.fetch_ap_actor",
                return_value={"type": "Person", "id": remote_actor_url},
            ),
            patch(
                "suddenly.activitypub.tasks.get_or_create_remote_user",
                return_value=remote_user,
            ),
            patch("suddenly.activitypub.tasks.send_follow_activity") as mock_task,
            patch("suddenly.activitypub.signals._safe_delay"),
        ):
            mock_task.delay = MagicMock()
            response = client.post(
                "/federation/remote/follow/",
                {"ap_id": remote_actor_url, "action": "unfollow"},
            )

        assert response.status_code == 200
        assert response.context["is_following"] is True, (
            "View must follow (not unfollow) when no Follow exists, "
            "regardless of action= field value"
        )
        ct = ContentType.objects.get_for_model(UserModel)
        assert Follow.objects.filter(
            follower=local_user_with_key,
            content_type=ct,
            object_id=remote_user.pk,
        ).exists(), "Follow record must be created even when action=unfollow was sent"

    # ------------------------------------------------------------------
    # Error cases
    # ------------------------------------------------------------------

    def test_missing_ap_id_returns_400(
        self,
        local_user_with_key: Any,
    ) -> None:
        """POST without ap_id must return 400."""
        from django.test import Client

        client = Client()
        client.force_login(local_user_with_key)

        response = client.post("/federation/remote/follow/", {})

        assert response.status_code == 400

    def test_unresolvable_ap_id_returns_400(
        self,
        local_user_with_key: Any,
    ) -> None:
        """POST with an ap_id that get_or_create_remote_user cannot resolve must return 400."""
        from django.test import Client

        client = Client()
        client.force_login(local_user_with_key)

        with patch(
            "suddenly.activitypub.tasks.get_or_create_remote_user",
            return_value=None,
        ):
            response = client.post(
                "/federation/remote/follow/",
                {"ap_id": "https://unreachable.test/users/nobody"},
            )

        assert response.status_code == 400

    def test_get_method_returns_405(
        self,
        local_user_with_key: Any,
    ) -> None:
        """GET requests must be rejected with 405 Method Not Allowed."""
        from django.test import Client

        client = Client()
        client.force_login(local_user_with_key)

        response = client.get("/federation/remote/follow/")

        assert response.status_code == 405

    def test_unauthenticated_redirects_to_login(self) -> None:
        """Unauthenticated POST must redirect to the login page (302)."""
        from django.test import Client

        client = Client()
        response = client.post(
            "/federation/remote/follow/",
            {"ap_id": "https://peer.suddenly.test/users/someone"},
        )

        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"] or "/login" in response["Location"], (
            f"Redirect must point to login, got {response['Location']}"
        )


# ---------------------------------------------------------------------------
# View: remote_profile — is_following context
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRemoteProfileIsFollowing:
    """remote_profile view must set is_following correctly in context.

    The view calls htmx_render (imported at module level in federation_views).
    We patch htmx_render to capture the context dict without actually rendering
    templates — this avoids static file manifest issues in test settings.

    The view's first DB query (redirect check) uses User.objects.filter(ap_id=…)
    without remote=True.  The is_following check uses …filter(ap_id=…, remote=True).
    We use a filter side_effect to return an empty queryset on the redirect check
    while allowing the real queryset on the is_following check.
    """

    def _setup_view_mocks(
        self,
        mocker: Any,
        ap_id: str,
        captured_contexts: list[dict[str, Any]],
    ) -> None:
        """Patch _fetch_actor and htmx_render to capture context without rendering."""
        mocker.patch(
            "suddenly.activitypub.federation_views._fetch_actor",
            return_value={
                "id": ap_id,
                "type": "Person",
                "preferredUsername": "remote_person",
                "name": "Remote Person",
                "inbox": f"{ap_id}/inbox",
                "summary": "",
            },
        )

        from django.http import HttpResponse

        def fake_htmx_render(
            request: Any,
            full_template: str,
            partial_template: str,
            context: dict[str, Any] | None = None,
        ) -> HttpResponse:
            captured_contexts.append(context or {})
            return HttpResponse(status=200)

        mocker.patch(
            "suddenly.activitypub.federation_views.htmx_render",
            side_effect=fake_htmx_render,
        )

    def test_authenticated_user_following_sees_is_following_true(
        self,
        local_user_with_key: Any,
        settings: Any,
        rf: RequestFactory,
        mocker: Any,
    ) -> None:
        """
        Authenticated user who already follows the remote actor must see
        is_following=True in the remote_profile context.

        We bypass the redirect branch by making the first filter() return None
        (actor not yet locally known) via side_effect, while the second call
        (with remote=True) returns the real remote_user so the Follow lookup works.
        """
        from django.contrib.contenttypes.models import ContentType

        from suddenly.characters.models import Follow
        from suddenly.users.models import User as UserModel

        remote_actor_url = "https://peer.suddenly.test/users/remote_india"
        remote_user = UserModel.objects.create(
            username="remote_india@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
        )

        ct = ContentType.objects.get_for_model(UserModel)
        # Suppress post_save signal during Follow creation
        with patch("suddenly.activitypub.signals._safe_delay"):
            Follow.objects.create(
                follower=local_user_with_key,
                content_type=ct,
                object_id=remote_user.pk,
                remote=False,
                ap_id=f"https://{settings.DOMAIN}/users/{local_user_with_key.username}/follows/{remote_user.pk}",
            )

        captured_contexts: list[dict[str, Any]] = []
        self._setup_view_mocks(mocker, remote_actor_url, captured_contexts)

        # First filter(ap_id=…) → empty (no redirect); second filter(ap_id=…, remote=True) → real
        real_filter = UserModel.objects.filter

        def filter_side_effect(**kwargs: Any) -> Any:
            if kwargs.get("remote") is True:
                return real_filter(**kwargs)
            return UserModel.objects.none()

        mocker.patch(
            "suddenly.users.models.User.objects.filter",
            side_effect=filter_side_effect,
        )

        request = rf.get("/federation/remote/", {"ap_id": remote_actor_url})
        request.user = local_user_with_key

        from suddenly.activitypub.federation_views import remote_profile

        response = remote_profile(request)

        assert response.status_code == 200
        assert len(captured_contexts) == 1, "htmx_render must be called once"
        assert captured_contexts[0]["is_following"] is True, (
            "is_following must be True when user has an existing Follow for this remote actor"
        )

    def test_authenticated_user_not_following_sees_is_following_false(
        self,
        local_user_with_key: Any,
        rf: RequestFactory,
        mocker: Any,
    ) -> None:
        """
        Authenticated user who does not follow the remote actor must see
        is_following=False.
        """
        from suddenly.users.models import User as UserModel

        remote_actor_url = "https://peer.suddenly.test/users/remote_juliet"
        UserModel.objects.create(
            username="remote_juliet@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
        )

        captured_contexts: list[dict[str, Any]] = []
        self._setup_view_mocks(mocker, remote_actor_url, captured_contexts)

        real_filter = UserModel.objects.filter

        def filter_side_effect(**kwargs: Any) -> Any:
            if kwargs.get("remote") is True:
                return real_filter(**kwargs)
            return UserModel.objects.none()

        mocker.patch(
            "suddenly.users.models.User.objects.filter",
            side_effect=filter_side_effect,
        )

        request = rf.get("/federation/remote/", {"ap_id": remote_actor_url})
        request.user = local_user_with_key

        from suddenly.activitypub.federation_views import remote_profile

        response = remote_profile(request)

        assert response.status_code == 200
        assert len(captured_contexts) == 1, "htmx_render must be called once"
        assert captured_contexts[0]["is_following"] is False, (
            "is_following must be False when user has no Follow for this remote actor"
        )

    def test_unauthenticated_user_sees_is_following_false(
        self,
        rf: RequestFactory,
        mocker: Any,
    ) -> None:
        """
        Unauthenticated access to remote_profile must succeed (200) with
        is_following=False — no exception or redirect.
        """
        from django.contrib.auth.models import AnonymousUser

        from suddenly.users.models import User as UserModel

        remote_actor_url = "https://peer.suddenly.test/users/remote_kilo"

        captured_contexts: list[dict[str, Any]] = []
        self._setup_view_mocks(mocker, remote_actor_url, captured_contexts)

        mocker.patch(
            "suddenly.users.models.User.objects.filter",
            return_value=UserModel.objects.none(),
        )

        request = rf.get("/federation/remote/", {"ap_id": remote_actor_url})
        request.user = AnonymousUser()

        from suddenly.activitypub.federation_views import remote_profile

        response = remote_profile(request)

        assert response.status_code == 200
        assert len(captured_contexts) == 1, "htmx_render must be called once"
        assert captured_contexts[0]["is_following"] is False, (
            "is_following must be False for unauthenticated users"
        )


# ---------------------------------------------------------------------------
# Serializer: create_follow_activity — activity_id parameter
# ---------------------------------------------------------------------------


class TestCreateFollowActivityId:
    """create_follow_activity must honour the optional activity_id parameter."""

    def test_with_activity_id_sets_id_field(self) -> None:
        """When activity_id is provided, activity['id'] must equal activity_id."""
        from suddenly.activitypub.serializers import create_follow_activity

        actor = MagicMock()
        actor.actor_url = "https://local.suddenly.test/users/alice"
        target = "https://peer.suddenly.test/users/bob"
        activity_id = "https://local.suddenly.test/users/alice/follows/42"

        activity = create_follow_activity(actor, target, activity_id)

        assert activity.get("id") == activity_id, (
            f"activity['id'] must be {activity_id}, got {activity.get('id')}"
        )

    def test_without_activity_id_omits_id_field(self) -> None:
        """When activity_id is None, 'id' must be absent from the activity."""
        from suddenly.activitypub.serializers import create_follow_activity

        actor = MagicMock()
        actor.actor_url = "https://local.suddenly.test/users/alice"
        target = "https://peer.suddenly.test/users/bob"

        activity = create_follow_activity(actor, target, None)

        assert "id" not in activity, (
            f"'id' key must be absent when activity_id is None, got {activity.get('id')}"
        )


# ---------------------------------------------------------------------------
# Flow: Follow outgoing — follow_ap_id propagates to delivered activity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFollowOutgoingActivityId:
    """send_follow_activity must propagate follow_ap_id into the delivered Follow activity."""

    def test_follow_ap_id_appears_in_delivered_activity(
        self,
        local_federation_user: Any,
        mocker: Any,
    ) -> None:
        """
        When follow_ap_id is passed to send_follow_activity, the activity
        delivered via deliver_activity.delay must contain 'id': follow_ap_id.
        """
        from suddenly.activitypub.tasks import send_follow_activity

        peer_actor = "https://test.suddenly.social/users/testbot"
        remote_inbox = f"{peer_actor}/inbox"
        follow_ap_id = f"{local_federation_user.actor_url}/follows/99"

        captured_delay_calls: list[dict[str, Any]] = []

        def fake_delay(**kwargs: Any) -> None:
            captured_delay_calls.append(kwargs)

        mock_deliver = mocker.MagicMock()
        mock_deliver.delay.side_effect = fake_delay
        mocker.patch("suddenly.activitypub.tasks.deliver_activity", mock_deliver)

        remote_actor_data = {
            "id": peer_actor,
            "type": "Person",
            "preferredUsername": "testbot",
            "inbox": remote_inbox,
            "outbox": f"{peer_actor}/outbox",
            "publicKey": {
                "id": f"{peer_actor}#main-key",
                "owner": peer_actor,
                "publicKeyPem": "fake-public-key-pem",
            },
        }
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = remote_actor_data
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.get.return_value = mock_http_response
        mocker.patch("httpx.Client", return_value=mock_client_instance)

        send_follow_activity(str(local_federation_user.pk), peer_actor, follow_ap_id)

        assert len(captured_delay_calls) == 1, (
            f"deliver_activity.delay must be called once, got {len(captured_delay_calls)}"
        )

        activity = captured_delay_calls[0].get("activity", {})
        assert activity.get("id") == follow_ap_id, (
            f"Delivered Follow activity must contain id={follow_ap_id}, got id={activity.get('id')}"
        )


# ---------------------------------------------------------------------------
# Flow: Delete incoming (remote actor deletes a Character)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeleteIncoming:
    """Remote actor sends Delete — inbox must remove the remote Character from DB."""

    def test_delete_incoming_character_removes_db_record(
        self,
        rf: RequestFactory,
        local_federation_user: Any,
        mocker: Any,
        settings: Any,
    ) -> None:
        """
        RED: handle_delete must delete the remote Character from DB when it
        receives Delete{object: character_ap_id}.

        Current stub only logs — no record is deleted.
        """
        from suddenly.activitypub.inbox import process_inbox
        from suddenly.characters.models import Character, CharacterStatus

        remote_actor_url = "https://peer.suddenly.test/users/remote_sender"
        character_ap_id = "https://peer.suddenly.test/characters/aria"
        private_pem, public_pem = generate_key_pair()

        remote_user = UserFactory(
            username="remote_sender@peer.suddenly.test",
            remote=True,
            ap_id=remote_actor_url,
            inbox_url=f"{remote_actor_url}/inbox",
            public_key=public_pem,
        )

        from suddenly.games.models import Game

        game = Game.objects.create(title="Remote Game", owner=remote_user, remote=True)
        Character.objects.create(
            name="Aria",
            status=CharacterStatus.NPC,
            creator=remote_user,
            origin_game=game,
            remote=True,
            ap_id=character_ap_id,
        )

        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Delete",
            "id": f"{remote_actor_url}#delete-aria",
            "actor": remote_actor_url,
            "object": character_ap_id,
        }

        path = f"/users/{local_federation_user.username}/inbox"
        request = _make_signed_inbox_request(rf, activity, remote_actor_url, private_pem, path)

        mocker.patch(
            "suddenly.activitypub.inbox.verify_signature",
            return_value=(True, ""),
        )
        mocker.patch(
            "suddenly.activitypub.inbox._check_rate_limit",
            return_value=False,
        )

        response = process_inbox(
            request,
            actor_type="user",
            actor_identifier=local_federation_user.username,
        )

        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        assert not Character.objects.filter(ap_id=character_ap_id).exists(), (
            "handle_delete must remove the remote Character from DB. "
            "Current stub only logs — no record is deleted."
        )
