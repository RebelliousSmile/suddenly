"""
Tests for the ActivityPub federation quick wins (2026-05-29 audit).

Covers the security/reliability hardening: SSRF block on actor fetch,
date-skew rejection in signature verification, inbox signature + idempotency
guarantees, signed Accept delivery, and the permanent-vs-transient retry policy
of the Celery delivery task.

Single mocking strategy (per project rules): ``mocker.patch`` for ``.delay``
enqueue checks, and ``<task>.apply(...)`` / direct calls for internal behavior.
No network is ever hit.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.test import Client, RequestFactory

from suddenly.activitypub._http import fetch_ap_actor
from suddenly.activitypub.signatures import verify_signature
from suddenly.users.models import User


class TestSsrfBlock:
    """fetch_ap_actor must block loopback/private targets before any network."""

    def test_loopback_returns_none_without_network(self, mocker: Any) -> None:
        """A loopback URL is rejected before httpx.Client is instantiated."""
        mock_client = mocker.patch("httpx.Client")

        result = fetch_ap_actor("http://127.0.0.1/actor")

        assert result is None
        mock_client.assert_not_called()


class TestDateSkewReject:
    """verify_signature must reject a stale Date header (replay protection)."""

    def test_stale_date_rejected(self, rf: RequestFactory) -> None:
        """A Date header beyond the skew window returns (False, 'Date skew')."""
        stale = datetime.now(UTC) - timedelta(seconds=600)
        date_str = stale.strftime("%a, %d %b %Y %H:%M:%S GMT")

        sig_header = (
            'keyId="https://remote.example/actor#main-key",'
            'algorithm="rsa-sha256",'
            'headers="(request-target) host date",'
            'signature="ZmFrZQ=="'
        )

        request = rf.post(
            "/users/bob/inbox",
            data=json.dumps({"type": "Follow"}),
            content_type="application/activity+json",
            HTTP_DATE=date_str,
            HTTP_SIGNATURE=sig_header,
        )

        is_valid, reason = verify_signature(request)

        assert is_valid is False
        assert reason == "Date skew"


@pytest.mark.django_db
class TestInboxSignatureReject:
    """An unsigned POST to a real local inbox must be forbidden."""

    def test_missing_signature_returns_403(self, client: Client, user: User) -> None:
        """No Signature header against a real local user → 403."""
        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Follow",
            "id": "https://remote.example/activities/1",
            "actor": "https://remote.example/actor",
        }

        response = client.post(
            f"/users/{user.username}/inbox",
            data=json.dumps(activity),
            content_type="application/activity+json",
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestInboxIdempotency:
    """Replaying an activity with the same id must be processed only once."""

    def test_duplicate_activity_processed_once(
        self, client: Client, user: User, mocker: Any
    ) -> None:
        """Second identical POST returns 202 and creates no second row."""
        from suddenly.activitypub.models import ProcessedActivity

        mocker.patch(
            "suddenly.activitypub.inbox.verify_signature",
            return_value=(True, "https://remote.example/actor#main-key"),
        )
        mocker.patch(
            "suddenly.activitypub.inbox._check_rate_limit",
            return_value=False,
        )
        mocker.patch(
            "suddenly.activitypub.inbox.get_or_create_remote_user",
            return_value=None,
        )

        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Follow",
            "id": "https://remote.example/activities/42",
            "actor": "https://remote.example/actor",
        }
        body = json.dumps(activity)

        first = client.post(
            f"/users/{user.username}/inbox",
            data=body,
            content_type="application/activity+json",
            HTTP_SIGNATURE='keyId="https://remote.example/actor#main-key"',
        )
        second = client.post(
            f"/users/{user.username}/inbox",
            data=body,
            content_type="application/activity+json",
            HTTP_SIGNATURE='keyId="https://remote.example/actor#main-key"',
        )

        assert first.status_code == 202
        assert second.status_code == 202
        assert ProcessedActivity.objects.count() == 1


@pytest.mark.django_db
class TestSignedAcceptDelivery:
    """send_accept_follow must deliver a signed Accept (non-None key id)."""

    def test_accept_delivery_carries_actor_key_id(self, mocker: Any, settings: Any) -> None:
        """deliver_activity.delay is called with a non-None actor_key_id."""
        from suddenly.activitypub.signatures import generate_key_pair
        from suddenly.activitypub.tasks import send_accept_follow

        settings.DOMAIN = "test.social"
        settings.AP_BASE_URL = "https://test.social"

        private_pem, public_pem = generate_key_pair()
        target = User.objects.create(
            username="local",
            email="local@test.social",
            private_key=private_pem,
            public_key=public_pem,
        )
        User.objects.create(
            username="alice@remote.example",
            remote=True,
            ap_id="https://remote.example/actor",
            inbox_url="https://remote.example/actor/inbox",
        )

        follow_activity: dict[str, Any] = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Follow",
            "id": "https://remote.example/activities/1",
            "actor": "https://remote.example/actor",
            "object": target.actor_url,
        }

        mock_delay = mocker.patch("suddenly.activitypub.tasks.deliver_activity.delay")

        send_accept_follow.apply(args=[str(target.id), "User", follow_activity])

        mock_delay.assert_called_once()
        _, kwargs = mock_delay.call_args
        assert kwargs["actor_key_id"] is not None
        assert kwargs["actor_key_id"] == f"{target.actor_url}#main-key"


class TestDeliveryRetryPolicy:
    """deliver_activity must retry on 5xx/network but not on permanent 4xx."""

    def _mock_post_status(self, mocker: Any, status_code: int) -> None:
        """Patch httpx.Client so .post returns a response with status_code."""
        response = mocker.MagicMock()
        response.status_code = status_code

        client = mocker.MagicMock()
        client.__enter__ = mocker.MagicMock(return_value=client)
        client.__exit__ = mocker.MagicMock(return_value=False)
        client.post.return_value = response

        mocker.patch("httpx.Client", return_value=client)

    def test_4xx_does_not_retry(self, mocker: Any) -> None:
        """A 404 response returns normally without raising Retry."""
        from suddenly.activitypub.tasks import deliver_activity

        self._mock_post_status(mocker, 404)
        spy_retry = mocker.patch.object(
            deliver_activity, "retry", side_effect=AssertionError("retry must not be called")
        )

        result = deliver_activity.apply(
            args=[{"type": "Accept"}, "https://remote.example/actor/inbox"],
        )

        assert result.successful()
        spy_retry.assert_not_called()

    def test_5xx_retries(self, mocker: Any) -> None:
        """A 503 response triggers self.retry."""
        from suddenly.activitypub.tasks import deliver_activity

        self._mock_post_status(mocker, 503)
        # self.retry returns the exception the task body then raises. Use a
        # sentinel so we can assert the retry path without a live broker.
        sentinel = RuntimeError("retry-sentinel")
        spy_retry = mocker.patch.object(deliver_activity, "retry", return_value=sentinel)

        with pytest.raises(RuntimeError, match="retry-sentinel"):
            deliver_activity.apply(
                args=[{"type": "Accept"}, "https://remote.example/actor/inbox"],
                throw=True,
            )

        spy_retry.assert_called_once()
