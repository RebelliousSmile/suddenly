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
