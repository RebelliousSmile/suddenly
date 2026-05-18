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
    from urllib.parse import urlparse

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
    from typing import cast

    key_id = f"{actor_url}#main-key"
    body = json.dumps(activity)
    parsed = urlparse(f"https://local.suddenly.test{path}")

    date_str = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
    host = parsed.netloc
    digest = f"SHA-256={base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()}"

    signing_string = (
        f"(request-target): post {parsed.path}\n"
        f"host: {host}\n"
        f"date: {date_str}\n"
        f"digest: {digest}"
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
        # deliver_activity is imported inside handle_follow via `from .tasks import deliver_activity`
        # so we must patch the task object on the tasks module, not on inbox.
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
            HTTP_SIGNATURE=f'keyId="{remote_actor_url}#main-key",headers="(request-target) host date",signature="dummy"',
        )

        response = process_inbox(
            request,
            actor_type="user",
            actor_identifier=local_federation_user.username,
        )

        # 1. Inbox must return 202
        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}"
        )

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
        assert call_kwargs["actor_key_id"] is not None, (
            "actor_key_id must not be None"
        )
        assert "private_key_pem" in call_kwargs, (
            "deliver_activity.delay must receive private_key_pem — Accept would be unsigned without it"
        )
        assert call_kwargs["private_key_pem"] is not None, (
            "private_key_pem must not be None"
        )

        # 4. The Accept must target the remote actor's inbox
        assert call_kwargs.get("inbox_url") == remote_inbox_url, (
            f"Accept must be delivered to remote inbox {remote_inbox_url}, "
            f"got {call_kwargs.get('inbox_url')}"
        )

        # 5. The Accept activity must wrap the original Follow
        accept_activity = call_kwargs.get("activity", {})
        assert accept_activity.get("type") == "Accept", (
            "Delivered activity must be of type Accept"
        )
        assert accept_activity.get("actor") == target_url, (
            "Accept actor must be the local user"
        )


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
            f"{peer_url}/users/testbot" if peer_url else "https://test.suddenly.social/users/testbot",
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

        assert Follow.objects.filter(pk=follow.pk).exists(), (
            "Follow must exist before Undo"
        )

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
            HTTP_SIGNATURE=f'keyId="{remote_actor_url}#main-key",headers="(request-target) host date",signature="dummy"',
        )

        response = process_inbox(
            request,
            actor_type="user",
            actor_identifier=local_federation_user.username,
        )

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}"
        )

        assert not Follow.objects.filter(pk=follow.pk).exists(), (
            "Follow record must be deleted after receiving Undo(Follow)"
        )


@pytest.mark.django_db
class TestUnfollowOutgoing:
    """Local user unfollows a remote actor — send_undo_follow_activity must deliver signed Undo(Follow)."""

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
        assert inner.get("type") == "Follow", (
            f"Undo object must be Follow, got {inner.get('type')}"
        )
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
