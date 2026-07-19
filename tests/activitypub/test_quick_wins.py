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

    @pytest.mark.parametrize(
        "ip",
        [
            "240.0.0.1",  # reserved (240.0.0.0/4)
            "224.0.0.1",  # multicast
            "0.0.0.0",  # unspecified
            "10.0.0.5",  # RFC1918 private
            "169.254.1.1",  # link-local
        ],
    )
    def test_reserved_multicast_unspecified_blocked(self, mocker: Any, ip: str) -> None:
        """Reserved, multicast, unspecified and private IPs are blocked pre-network."""
        mocker.patch(
            "suddenly.activitypub._http.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", (ip, 443))],
        )
        mock_client = mocker.patch("httpx.Client")

        result = fetch_ap_actor("https://evil.example/actor")

        assert result is None
        mock_client.assert_not_called()

    def test_plain_http_rejected_when_insecure_disabled(self, mocker: Any, settings: Any) -> None:
        """Outside dev (AP_ALLOW_INSECURE_HTTP off), http:// is refused up front."""
        settings.AP_ALLOW_INSECURE_HTTP = False
        mock_client = mocker.patch("httpx.Client")

        result = fetch_ap_actor("http://remote.example/actor")

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
class TestInboxDispatchObservability:
    """A handler failing inside dispatch is logged with its stack and still 202."""

    def test_handler_exception_logs_stack_and_returns_202(
        self, client: Client, user: User, mocker: Any
    ) -> None:
        """A raising handler → logger.exception (stack) and an unchanged 202."""
        mocker.patch(
            "suddenly.activitypub.inbox.verify_signature",
            return_value=(True, "https://remote.example/actor#main-key"),
        )
        mocker.patch("suddenly.activitypub.inbox._check_rate_limit", return_value=False)
        mocker.patch("suddenly.activitypub.inbox.get_or_create_remote_user", return_value=None)
        mocker.patch(
            "suddenly.activitypub.inbox.handle_follow",
            side_effect=RuntimeError("handler boom"),
        )
        spy_exception = mocker.patch("suddenly.activitypub.inbox.logger.exception")

        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Follow",
            "id": "https://remote.example/activities/dispatch-boom",
            "actor": "https://remote.example/actor",
        }

        response = client.post(
            f"/users/{user.username}/inbox",
            data=json.dumps(activity),
            content_type="application/activity+json",
            HTTP_SIGNATURE='keyId="https://remote.example/actor#main-key"',
        )

        assert response.status_code == 202
        spy_exception.assert_called_once()


@pytest.mark.django_db
class TestOfferSuddenlyOnlyGuard:
    """send_offer_activity must not deliver Claim/Adopt/Fork Offers to a known
    non-Suddenly instance (08-activitypub.md "Never send Suddenly-only
    activities to non-Suddenly instances"), but must still deliver to an
    unresolved/unknown instance (no prior NodeInfo discovery) to preserve
    first-contact delivery.
    """

    def _make_link_request(self, settings: Any, inbox_url: str) -> Any:
        """Build a PENDING LinkRequest whose target NPC's creator is remote."""
        from suddenly.characters.models import (
            Character,
            CharacterStatus,
            LinkRequest,
            LinkRequestStatus,
            LinkType,
        )
        from suddenly.games.models import Game

        settings.DOMAIN = "local.suddenly.test"
        settings.AP_BASE_URL = "https://local.suddenly.test"

        remote_creator = User.objects.create(
            username="remote_creator@somewhere.example",
            remote=True,
            ap_id="https://somewhere.example/users/remote_creator",
            inbox_url=inbox_url,
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
        requester = User.objects.create(username="local_requester", remote=False)

        return LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=requester,
            target_character=character,
            message="Please adopt",
            status=LinkRequestStatus.PENDING,
        )

    def test_skips_known_non_suddenly_instance(self, mocker: Any, settings: Any) -> None:
        """A known Mastodon instance (application_type != 'suddenly') is skipped."""
        from suddenly.activitypub.models import FederatedServer
        from suddenly.activitypub.tasks import send_offer_activity

        mocker.patch("suddenly.activitypub.signals._safe_delay")
        lr = self._make_link_request(settings, "https://mastodon.example/users/bob/inbox")
        FederatedServer.objects.create(server_name="mastodon.example", application_type="mastodon")
        mock_delay = mocker.patch("suddenly.activitypub.tasks.deliver_activity.delay")

        send_offer_activity(str(lr.pk))

        mock_delay.assert_not_called()

    def test_delivers_to_known_suddenly_instance(self, mocker: Any, settings: Any) -> None:
        """A known Suddenly instance receives the Offer."""
        from suddenly.activitypub.models import FederatedServer
        from suddenly.activitypub.tasks import send_offer_activity

        mocker.patch("suddenly.activitypub.signals._safe_delay")
        lr = self._make_link_request(settings, "https://sibling.suddenly.test/users/bob/inbox")
        FederatedServer.objects.create(
            server_name="sibling.suddenly.test", application_type="suddenly"
        )
        mock_delay = mocker.patch("suddenly.activitypub.tasks.deliver_activity.delay")

        send_offer_activity(str(lr.pk))

        mock_delay.assert_called_once()

    def test_delivers_to_unknown_instance(self, mocker: Any, settings: Any) -> None:
        """No FederatedServer row (never NodeInfo-probed) — first contact is allowed."""
        from suddenly.activitypub.tasks import send_offer_activity

        mocker.patch("suddenly.activitypub.signals._safe_delay")
        lr = self._make_link_request(settings, "https://unknown.example/users/bob/inbox")
        mock_delay = mocker.patch("suddenly.activitypub.tasks.deliver_activity.delay")

        send_offer_activity(str(lr.pk))

        mock_delay.assert_called_once()


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
