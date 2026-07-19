"""
Tests for ActivityPub functionality.
"""

from __future__ import annotations

import json
from typing import Any, cast

import pytest
from django.http import HttpRequest
from django.test import Client, RequestFactory

from suddenly.activitypub.serializers import (
    serialize_character,
    serialize_game,
    serialize_quote,
    serialize_report,
    serialize_user,
)
from suddenly.activitypub.signatures import generate_key_pair
from suddenly.characters.models import Character, CharacterStatus, Quote, QuoteVisibility
from suddenly.games.models import Game, Report
from suddenly.users.models import User


class TestWebFinger:
    """Tests for WebFinger endpoint."""

    def test_webfinger_valid_user(self, client: Client, user: User, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        response = client.get(
            "/.well-known/webfinger", {"resource": f"acct:{user.username}@test.social"}
        )

        assert response.status_code == 200
        assert response["Content-Type"] == "application/jrd+json"

        data = response.json()
        assert data["subject"] == f"acct:{user.username}@test.social"
        assert len(data["links"]) >= 1

        # Check for self link
        self_link = next(link for link in data["links"] if link["rel"] == "self")
        assert "application/activity+json" in self_link["type"]

    def test_webfinger_unknown_user(self, client: Client, db: Any, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        response = client.get("/.well-known/webfinger", {"resource": "acct:nobody@test.social"})

        assert response.status_code == 404

    def test_webfinger_wrong_domain(self, client: Client, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        response = client.get("/.well-known/webfinger", {"resource": "acct:user@other.social"})

        assert response.status_code == 404

    def test_webfinger_missing_resource(self, client: Client) -> None:
        response = client.get("/.well-known/webfinger")
        assert response.status_code == 400


class TestNodeInfo:
    """Tests for NodeInfo endpoints."""

    def test_nodeinfo_index(self, client: Client, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        response = client.get("/.well-known/nodeinfo")

        assert response.status_code == 200
        data = response.json()
        assert "links" in data
        assert any("nodeinfo" in link["rel"] for link in data["links"])

    def test_nodeinfo_2_0(self, client: Client, db: Any, user: User, settings: Any) -> None:
        settings.DOMAIN = "test.social"
        settings.SITE_NAME = "Test Suddenly"

        response = client.get("/.well-known/nodeinfo/2.0")

        assert response.status_code == 200
        data = response.json()

        assert data["version"] == "2.0"
        assert data["software"]["name"] == "suddenly"
        assert "activitypub" in data["protocols"]
        assert "users" in data["usage"]


class TestUserActor:
    """Tests for User actor endpoints."""

    def test_user_actor_json(self, client: Client, user: User, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        response = client.get(f"/users/{user.username}", HTTP_ACCEPT="application/activity+json")

        assert response.status_code == 200
        assert "application/activity+json" in response["Content-Type"]

        data = response.json()
        assert data["type"] == "Person"
        assert data["preferredUsername"] == user.username
        assert "inbox" in data
        assert "outbox" in data

    def test_user_actor_html_redirect(self, client: Client, user: User) -> None:
        response = client.get(f"/users/{user.username}", HTTP_ACCEPT="text/html")

        # Should redirect to profile page
        assert response.status_code == 302

    def test_user_outbox(self, client: Client, user: User, game: Game, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        # Create a published report
        Report.objects.create(
            title="Test Report", content="Test content", game=game, author=user, status="published"
        )

        response = client.get(
            f"/users/{user.username}/outbox", HTTP_ACCEPT="application/activity+json"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "OrderedCollection"


class TestGameActor:
    """Tests for Game actor endpoints."""

    def test_game_actor_json(self, client: Client, game: Game, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        response = client.get(f"/games/{game.id}", HTTP_ACCEPT="application/activity+json")

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "Group"
        assert data["name"] == game.title

    def test_game_outbox(self, client: Client, game: Game, user: User, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        Report.objects.create(
            title="Test", content="Content", game=game, author=user, status="published"
        )

        response = client.get(f"/games/{game.id}/outbox", HTTP_ACCEPT="application/activity+json")

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "OrderedCollection"


class TestCharacterActor:
    """Tests for Character actor endpoints."""

    def test_character_actor_json(
        self, client: Client, character: Character, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"

        response = client.get(
            f"/characters/{character.id}", HTTP_ACCEPT="application/activity+json"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "Person"
        assert data["name"] == character.name
        assert data["status"] == character.status


class TestSerializers:
    """Tests for ActivityPub serializers."""

    def test_serialize_user(self, user: User, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        data = serialize_user(user)

        assert data["type"] == "Person"
        assert data["preferredUsername"] == user.username
        assert data["name"] == user.get_display_name()
        assert "inbox" in data
        assert "outbox" in data
        assert "@context" in data

    def test_serialize_game(self, game: Game, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        data = serialize_game(game)

        assert data["type"] == "Group"
        assert data["name"] == game.title
        assert "attributedTo" in data

    def test_serialize_character_npc(self, character: Character, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        data = serialize_character(character)

        assert data["type"] == "Person"
        assert data["name"] == character.name
        assert data["status"] == "npc"

    def test_serialize_character_with_parent(
        self, db: Any, character: Character, user: User, game: Game, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"

        fork = Character.objects.create(
            name="Fork Character",
            status=CharacterStatus.PC,
            owner=user,
            creator=user,
            origin_game=game,
            parent=character,
        )

        data = serialize_character(fork)

        assert "derivedFrom" in data
        assert str(character.actor_url) in str(data["derivedFrom"])

    def test_serialize_report(self, report: Report, settings: Any) -> None:
        settings.DOMAIN = "test.social"

        data = serialize_report(report)

        assert data["type"] == "Article"
        assert data["content"] == report.content
        assert "attributedTo" in data

    def test_serialize_quote(
        self, db: Any, character: Character, user: User, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"

        quote = Quote.objects.create(
            content="To be or not to be",
            character=character,
            author=user,
            visibility=QuoteVisibility.PUBLIC,
        )

        data = serialize_quote(quote)

        assert data["type"] == "Note"
        assert "To be or not to be" in data["content"]


@pytest.mark.django_db
class TestHTTPSignatures:
    """Tests for HTTP signature generation and verification."""

    def test_generate_key_pair(self) -> None:
        private_key, public_key = generate_key_pair()

        assert "BEGIN PRIVATE KEY" in private_key
        assert "BEGIN PUBLIC KEY" in public_key

    def test_key_pair_consistency(self) -> None:
        """Generated keys should be usable together."""
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

        private_pem, public_pem = generate_key_pair()

        # Load private key
        private_key = cast(
            RSAPrivateKey,
            serialization.load_pem_private_key(
                private_pem.encode(), password=None, backend=default_backend()
            ),
        )

        # Extract public key from private
        derived_public = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )

        assert derived_public == public_pem

    def test_sign_request_adds_required_headers(self) -> None:
        """sign_request must set Signature, Date, and Host headers."""
        from suddenly.activitypub.signatures import sign_request

        private_pem, _ = generate_key_pair()
        headers: dict[str, str] = {}
        sign_request(
            method="GET",
            url="https://example.com/users/alice/inbox",
            headers=headers,
            key_id="https://example.com/users/alice#main-key",
            private_key_pem=private_pem,
        )
        assert "Signature" in headers
        assert "Date" in headers
        assert "Host" in headers
        assert 'keyId="https://example.com/users/alice#main-key"' in headers["Signature"]

    def test_sign_request_adds_digest_when_body_given(self) -> None:
        """sign_request must add SHA-256 Digest header when body is provided."""
        from suddenly.activitypub.signatures import sign_request

        private_pem, _ = generate_key_pair()
        headers: dict[str, str] = {}
        sign_request(
            method="POST",
            url="https://example.com/inbox",
            headers=headers,
            body={"type": "Follow"},
            key_id="https://example.com/actor#main-key",
            private_key_pem=private_pem,
        )
        assert "Digest" in headers
        assert headers["Digest"].startswith("SHA-256=")
        assert "digest" in headers["Signature"]

    def test_verify_signature_returns_tuple(self) -> None:
        """Regression: verify_signature returns (bool, str), not a plain bool."""
        from suddenly.activitypub.signatures import verify_signature

        request = RequestFactory().post("/inbox")
        result = verify_signature(request)

        assert isinstance(
            result, tuple
        ), "verify_signature must return (bool, str), not a plain bool"
        is_valid, _ = result
        assert is_valid is False

    def test_verify_signature_rejects_unsigned_request(self) -> None:
        """Request without Signature header must fail verification."""
        from suddenly.activitypub.signatures import verify_signature

        request = RequestFactory().post("/inbox")
        is_valid, reason = verify_signature(request)

        assert is_valid is False
        assert reason is not None
        assert "No Signature" in reason

    def test_sign_then_verify_roundtrip(self, mocker: Any) -> None:
        """Full roundtrip: sign outgoing request, then verify incoming."""
        from suddenly.activitypub.signatures import sign_request, verify_signature

        private_pem, public_pem = generate_key_pair()
        key_id = "https://remote.social/users/alice#main-key"
        target_url = "https://test.social/users/testuser/inbox"
        body: dict[str, object] = {"type": "Follow"}

        # Sign the outgoing request
        headers: dict[str, str] = {}
        sign_request(
            method="POST",
            url=target_url,
            headers=headers,
            body=body,
            key_id=key_id,
            private_key_pem=private_pem,
        )

        # Reconstruct the incoming request
        meta: dict[str, Any] = {
            "HTTP_HOST": headers["Host"],
            "HTTP_DATE": headers["Date"],
            "HTTP_SIGNATURE": headers["Signature"],
        }
        if "Digest" in headers:
            meta["HTTP_DIGEST"] = headers["Digest"]

        request = RequestFactory().post(
            "/users/testuser/inbox",
            data=json.dumps(body),
            content_type="application/activity+json",
            **meta,
        )

        # Mock _fetch_public_key to return our public key
        mocker.patch(
            "suddenly.activitypub.signatures._fetch_public_key",
            return_value=public_pem,
        )

        is_valid, result = verify_signature(request)
        assert is_valid is True
        assert result == key_id

    def test_verify_signature_rejects_tampered_request(self, mocker: Any) -> None:
        """Request with valid signature but tampered body must fail."""
        from suddenly.activitypub.signatures import sign_request, verify_signature

        private_pem, public_pem = generate_key_pair()
        key_id = "https://remote.social/users/alice#main-key"

        # Sign with original body
        headers: dict[str, str] = {}
        sign_request(
            method="POST",
            url="https://test.social/users/testuser/inbox",
            headers=headers,
            body={"type": "Follow"},
            key_id=key_id,
            private_key_pem=private_pem,
        )

        # Tamper: replace body content but keep old Digest
        meta: dict[str, Any] = {
            "HTTP_HOST": headers["Host"],
            "HTTP_DATE": headers["Date"],
            "HTTP_SIGNATURE": headers["Signature"],
        }
        if "Digest" in headers:
            meta["HTTP_DIGEST"] = headers["Digest"]

        request = RequestFactory().post(
            "/users/testuser/inbox",
            data=json.dumps({"type": "Delete"}),  # tampered
            content_type="application/activity+json",
            **meta,
        )

        # Mock _fetch_public_key to return our public key
        mocker.patch(
            "suddenly.activitypub.signatures._fetch_public_key",
            return_value=public_pem,
        )

        is_valid, _ = verify_signature(request)
        assert is_valid is False


class TestInbox:
    """Tests for inbox endpoints (receiving activities)."""

    def test_inbox_rejects_invalid_json(self, client: Client, user: User) -> None:
        response = client.post(
            f"/users/{user.username}/inbox",
            data="not json",
            content_type="application/activity+json",
        )

        # Signature-first inbox: an unsigned request is rejected (403) before
        # the body is ever parsed, so it never reaches JSON validation (400).
        assert response.status_code == 403


class TestPublicKeyCache:
    """Tests for PublicKeyCache model and verify_signature cache/retry logic."""

    pytestmark = pytest.mark.django_db

    def test_fetch_public_key_stores_in_cache(self, mocker: Any) -> None:
        """_fetch_public_key should store the key in PublicKeyCache."""
        from suddenly.activitypub.models import PublicKeyCache
        from suddenly.activitypub.signatures import _fetch_public_key

        _, public_pem = generate_key_pair()
        actor_url = "https://remote.social/users/alice"

        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "publicKey": {"publicKeyPem": public_pem},
        }
        mock_response.raise_for_status = mocker.MagicMock()

        mock_client = mocker.MagicMock()
        mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
        mock_client.__exit__ = mocker.MagicMock(return_value=False)
        mock_client.get.return_value = mock_response

        mocker.patch("httpx.Client", return_value=mock_client)

        result = _fetch_public_key(actor_url)

        assert result == public_pem
        cached = PublicKeyCache.objects.get(actor_url=actor_url)
        assert cached.public_key_pem == public_pem

    def test_fetch_public_key_returns_none_on_timeout(self, mocker: Any) -> None:
        """_fetch_public_key should return None on HTTP error."""
        from suddenly.activitypub.signatures import _fetch_public_key

        mock_client = mocker.MagicMock()
        mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
        mock_client.__exit__ = mocker.MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("Connection timeout")

        mocker.patch("httpx.Client", return_value=mock_client)

        result = _fetch_public_key("https://slow.server/users/bob")
        assert result is None

    def _make_signed_request(
        self,
        rf: RequestFactory,
        private_pem: str,
        actor_url: str,
        path: str = "/users/bob/inbox",
    ) -> HttpRequest:
        """Helper to create a properly signed Django request."""
        import base64
        import hashlib
        from datetime import UTC, datetime
        from urllib.parse import urlparse

        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

        key_id = f"{actor_url}#main-key"
        body = json.dumps({"type": "Follow"})
        parsed = urlparse(f"https://test.social{path}")

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

    def test_verify_uses_cached_key(self, mocker: Any, rf: RequestFactory) -> None:
        """verify_signature should use cached key without HTTP call."""
        from suddenly.activitypub.models import PublicKeyCache
        from suddenly.activitypub.signatures import verify_signature

        private_pem, public_pem = generate_key_pair()
        actor_url = "https://remote.social/users/alice"

        PublicKeyCache.objects.create(
            actor_url=actor_url,
            public_key_pem=public_pem,
        )

        request = self._make_signed_request(rf, private_pem, actor_url)

        mock_fetch = mocker.patch("suddenly.activitypub.signatures._fetch_public_key")

        is_valid, result = verify_signature(request)

        assert is_valid is True
        assert result == f"{actor_url}#main-key"
        mock_fetch.assert_not_called()

    def test_verify_retries_on_stale_cached_key(self, mocker: Any, rf: RequestFactory) -> None:
        """verify_signature should re-fetch if cached key fails."""
        from suddenly.activitypub.models import PublicKeyCache
        from suddenly.activitypub.signatures import verify_signature

        private_pem, public_pem = generate_key_pair()
        _, stale_public_pem = generate_key_pair()
        actor_url = "https://remote.social/users/alice"

        PublicKeyCache.objects.create(
            actor_url=actor_url,
            public_key_pem=stale_public_pem,
        )

        request = self._make_signed_request(rf, private_pem, actor_url)

        mocker.patch(
            "suddenly.activitypub.signatures._fetch_public_key",
            return_value=public_pem,
        )

        is_valid, result = verify_signature(request)

        assert is_valid is True
        assert result == f"{actor_url}#main-key"


@pytest.mark.skip(reason="Requires django-ratelimit (optional federation dependency)")
class TestInboxRateLimit:
    """Tests for per-instance rate limiting on inbox endpoints."""

    pytestmark = pytest.mark.django_db

    def test_known_instance_not_rate_limited(self, rf: RequestFactory, mocker: Any) -> None:
        """Known instances should have a higher rate limit."""
        from suddenly.activitypub.inbox import _check_rate_limit
        from suddenly.activitypub.models import FederatedServer

        FederatedServer.objects.create(server_name="known.social")

        request = rf.post(
            "/users/bob/inbox",
            content_type="application/activity+json",
            HTTP_SIGNATURE='keyId="https://known.social/users/alice#main-key"',
        )

        # Should not be rate limited on first request
        assert _check_rate_limit(request) is False

    def test_unknown_instance_rate_limited(self, rf: RequestFactory, mocker: Any) -> None:
        """Unknown instances should hit rate limit faster."""
        from suddenly.activitypub.inbox import _check_rate_limit

        mocker.patch(
            "suddenly.activitypub.inbox.is_ratelimited",
            return_value=True,
        )

        request = rf.post(
            "/users/bob/inbox",
            content_type="application/activity+json",
            HTTP_SIGNATURE='keyId="https://unknown.social/users/evil#main-key"',
        )

        assert _check_rate_limit(request) is True

    def test_rate_limited_request_returns_403(
        self, rf: RequestFactory, user: User, mocker: Any
    ) -> None:
        """Rate-limited requests should get HTTP 403."""
        from suddenly.activitypub.inbox import process_inbox

        mocker.patch(
            "suddenly.activitypub.inbox._check_rate_limit",
            return_value=True,
        )

        request = rf.post(
            f"/users/{user.username}/inbox",
            data=json.dumps({"type": "Follow"}),
            content_type="application/activity+json",
        )

        response = process_inbox(request, actor_type="user", actor_identifier=user.username)

        assert response.status_code == 403


class TestLinkOfferFederation:
    """Inbound Offer (claim/adopt/fork) reconstruction from the emitted format."""

    pytestmark = pytest.mark.django_db

    @staticmethod
    def _remote_requester() -> User:
        from tests.factories import UserFactory

        return cast(
            User,
            UserFactory(
                username="bob@remote.social",
                email="bob@remote.social",
                remote=True,
                ap_id="https://remote.social/users/bob",
                inbox_url="https://remote.social/users/bob/inbox",
            ),
        )

    def test_serialized_claim_offer_round_trips_into_a_link_request(
        self, character: Character, user: User
    ) -> None:
        """
        The Offer we emit (``serialize_link_request``) must be ingestible by the
        inbox handler that receives it. This is the regression guard against the
        two federation code paths silently diverging again: emit-then-ingest,
        assert the link request is rebuilt with the right type, actors and PC.
        """
        from suddenly.activitypub.inbox import handle_offer
        from suddenly.activitypub.serializers import serialize_link_request
        from suddenly.characters.models import LinkRequest, LinkRequestStatus, LinkType
        from tests.factories import CharacterFactory

        bob = self._remote_requester()
        # Bob's proposed PC — remote from this instance's point of view
        viktor = CharacterFactory(
            name="Viktor",
            status="pc",
            owner=bob,
            creator=bob,
            remote=True,
            ap_id="https://remote.social/characters/viktor",
        )

        # Build the sender-side request, serialize it exactly as it goes on the wire
        sender_side = LinkRequest.objects.create(
            type=LinkType.CLAIM,
            requester=bob,
            target_character=character,
            proposed_character=viktor,
            message="Le Corbeau, c'était Viktor infiltré",
        )
        offer = serialize_link_request(sender_side)
        sender_side.delete()  # simulate crossing to the receiving instance
        assert LinkRequest.objects.count() == 0

        # The receiving instance ingests the very same JSON
        handle_offer(offer, "user", user.username)

        created = LinkRequest.objects.get()
        assert created.type == LinkType.CLAIM
        assert created.requester == bob
        assert created.target_character == character
        assert created.proposed_character == viktor
        assert created.message == "Le Corbeau, c'était Viktor infiltré"
        assert created.status == LinkRequestStatus.PENDING

    def test_offer_with_unknown_object_type_is_ignored(
        self, character: Character, user: User
    ) -> None:
        from suddenly.activitypub.inbox import handle_offer
        from suddenly.characters.models import LinkRequest

        bob = self._remote_requester()
        offer = {
            "type": "Offer",
            "actor": bob.actor_url,
            "target": character.actor_url,
            "object": {"type": "suddenly:Bogus", "content": "nope"},
        }

        handle_offer(offer, "user", user.username)

        assert LinkRequest.objects.count() == 0

    # ------------------------------------------------------------------
    # DEC-038 Part 1 — Offer id correlation (round-trip id → Accept)
    # ------------------------------------------------------------------

    def test_inbound_offer_stores_origin_offer_id(self, character: Character, user: User) -> None:
        """handle_offer persists the inbound Offer id for later Accept correlation."""
        from suddenly.activitypub.inbox import handle_offer
        from suddenly.characters.models import LinkRequest

        bob = self._remote_requester()
        offer = {
            "type": "Offer",
            "id": "https://remote.social/link-requests/abc-123",
            "actor": bob.actor_url,
            "target": character.actor_url,
            "object": {"type": "suddenly:Adopt", "content": "reprise"},
        }

        handle_offer(offer, "user", user.username)

        created = LinkRequest.objects.get()
        assert created.origin_offer_id == "https://remote.social/link-requests/abc-123"

    def test_remote_origin_accept_references_origin_offer_id(
        self, character: Character, user: User, mocker: Any
    ) -> None:
        """A request of remote origin emits an Accept whose object is that origin id."""
        from suddenly.activitypub.tasks import send_accept_activity
        from suddenly.characters.models import LinkRequest, LinkRequestStatus, LinkType

        bob = self._remote_requester()
        origin_id = "https://remote.social/link-requests/abc-123"
        lr = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=bob,
            target_character=character,
            message="reprise",
            status=LinkRequestStatus.PENDING,
            origin_offer_id=origin_id,
        )

        deliver = mocker.patch("suddenly.activitypub.tasks.deliver_activity")

        send_accept_activity(str(lr.pk))

        assert deliver.delay.called
        # sign_and_deliver calls deliver_activity.delay(...) with all-keyword
        # arguments (activity=, inbox_url=, actor_key_id=, private_key_pem=) —
        # see suddenly/activitypub/_http.py::sign_and_deliver.
        sent_activity = deliver.delay.call_args.kwargs["activity"]
        assert sent_activity["object"] == origin_id

    def test_locally_created_request_accept_keeps_serialized_offer(
        self, character: Character, user: User, mocker: Any
    ) -> None:
        """Without origin_offer_id, the Accept still carries the full Offer object."""
        from suddenly.activitypub.tasks import send_accept_activity
        from suddenly.characters.models import LinkRequest, LinkRequestStatus, LinkType

        bob = self._remote_requester()
        lr = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=bob,
            target_character=character,
            message="reprise",
            status=LinkRequestStatus.PENDING,
        )

        deliver = mocker.patch("suddenly.activitypub.tasks.deliver_activity")

        send_accept_activity(str(lr.pk))

        assert deliver.delay.called
        # sign_and_deliver calls deliver_activity.delay(...) with all-keyword
        # arguments (activity=, inbox_url=, actor_key_id=, private_key_pem=) —
        # see suddenly/activitypub/_http.py::sign_and_deliver.
        sent_activity = deliver.delay.call_args.kwargs["activity"]
        assert isinstance(sent_activity["object"], dict)
        assert sent_activity["object"]["type"] == "Offer"

    # ------------------------------------------------------------------
    # DEC-038 Part 2 — State reconstruction on the requester side
    # ------------------------------------------------------------------

    def test_federated_accept_reconstructs_state_and_is_idempotent(
        self, character: Character, user: User, mocker: Any
    ) -> None:
        """An inbound Accept rebuilds link + sequence + notification, replay-safe."""
        from suddenly.activitypub.inbox import handle_accept
        from suddenly.characters.models import (
            CharacterLink,
            LinkRequest,
            LinkRequestStatus,
            LinkType,
            SharedSequence,
        )
        from suddenly.core.models import Notification, NotificationType
        from tests.factories import CharacterFactory

        # Suppress signal-triggered task dispatches (Offer/Accept emission).
        mocker.patch("suddenly.activitypub.signals._safe_delay")

        bob = self._remote_requester()
        # The requester (local) targets a remote NPC mirror on the accepting side.
        target_mirror = CharacterFactory(
            name="Le Corbeau",
            status="npc",
            creator=bob,
            remote=True,
            ap_id="https://remote.social/characters/corbeau",
        )
        lr = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=user,
            target_character=target_mirror,
            message="Je le reprends",
            status=LinkRequestStatus.PENDING,
        )

        accept = {
            "type": "Accept",
            "actor": "https://remote.social/users/bob",
            "object": f"https://remote.social/link-requests/{lr.pk}",
            "summary": "Adoption acceptée",
        }

        handle_accept(accept, "user", user.username)

        lr.refresh_from_db()
        assert lr.status == LinkRequestStatus.ACCEPTED
        assert lr.response_message == "Adoption acceptée"

        link = CharacterLink.objects.get(link_request=lr)
        assert link.type == LinkType.ADOPT
        assert SharedSequence.objects.filter(link=link).exists()
        assert Notification.objects.filter(
            recipient=user, type=NotificationType.LINK_ACCEPTED
        ).exists()

        # Replay (retry / duplicate Accept) must not duplicate anything.
        handle_accept(accept, "user", user.username)
        assert CharacterLink.objects.filter(link_request=lr).count() == 1
        assert (
            Notification.objects.filter(recipient=user, type=NotificationType.LINK_ACCEPTED).count()
            == 1
        )

    # ------------------------------------------------------------------
    # DEC-038 Part 3 — Remote proposed-character resolution
    # ------------------------------------------------------------------

    def test_offer_fetches_unknown_remote_proposed_character(
        self, character: Character, user: User, mocker: Any
    ) -> None:
        """An unknown proposedCharacter is fetched and mirrored locally."""
        from suddenly.activitypub.inbox import handle_offer
        from suddenly.characters.models import LinkRequest

        bob = self._remote_requester()
        proposed_url = "https://remote.social/characters/viktor"

        mocker.patch(
            "suddenly.activitypub._http.fetch_ap_actor",
            return_value={
                "type": "Person",
                "name": "Viktor",
                "summary": "infiltré",
                "creator": bob.ap_id,
            },
        )

        offer = {
            "type": "Offer",
            "id": "https://remote.social/link-requests/xyz",
            "actor": bob.actor_url,
            "target": character.actor_url,
            "object": {
                "type": "suddenly:Claim",
                "content": "c'était Viktor",
                "proposedCharacter": proposed_url,
            },
        }

        handle_offer(offer, "user", user.username)

        created = LinkRequest.objects.get()
        assert created.proposed_character is not None
        pc = created.proposed_character
        assert pc.remote is True
        assert pc.ap_id == proposed_url
        assert pc.origin_game is not None

    def test_offer_with_unresolvable_proposed_character_degrades_to_null(
        self, character: Character, user: User, mocker: Any
    ) -> None:
        """A failed fetch leaves proposed_character null but still records the request."""
        from suddenly.activitypub.inbox import handle_offer
        from suddenly.characters.models import LinkRequest

        bob = self._remote_requester()

        mocker.patch("suddenly.activitypub._http.fetch_ap_actor", return_value=None)

        offer = {
            "type": "Offer",
            "id": "https://remote.social/link-requests/xyz",
            "actor": bob.actor_url,
            "target": character.actor_url,
            "object": {
                "type": "suddenly:Claim",
                "content": "c'était Viktor",
                "proposedCharacter": "https://remote.social/characters/ghost",
            },
        }

        handle_offer(offer, "user", user.username)

        created = LinkRequest.objects.get()
        assert created.proposed_character is None

    def test_proposed_character_without_author_does_not_mint_user_from_game(
        self, character: Character, user: User, mocker: Any
    ) -> None:
        """A fetched Character actor exposing only `attributedTo` (its origin Game,
        never the author) must not be mistaken for its creator — otherwise we mint a
        bogus remote User from a Group actor URL. proposedCharacter degrades to null.
        """
        from suddenly.activitypub.inbox import handle_offer
        from suddenly.characters.models import LinkRequest
        from suddenly.users.models import User as UserModel

        bob = self._remote_requester()
        game_url = "https://remote.social/games/some-campaign"

        # No `creator`/`owner` — only `attributedTo`, which for a Character is the Game.
        mocker.patch(
            "suddenly.activitypub._http.fetch_ap_actor",
            return_value={"type": "Person", "name": "Ghost", "attributedTo": game_url},
        )

        offer = {
            "type": "Offer",
            "id": "https://remote.social/link-requests/no-author",
            "actor": bob.actor_url,
            "target": character.actor_url,
            "object": {
                "type": "suddenly:Claim",
                "content": "auteur absent",
                "proposedCharacter": "https://remote.social/characters/ghost",
            },
        }

        handle_offer(offer, "user", user.username)

        created = LinkRequest.objects.get()
        assert created.proposed_character is None
        assert not UserModel.objects.filter(ap_id=game_url).exists()

    def test_remote_adopt_accept_leaves_mirror_owner_untouched(
        self, character: Character, user: User, mocker: Any
    ) -> None:
        """Requester-side ADOPT reconstruction must not locally reassign the remote
        mirror's owner/status: the accepting instance is authoritative and propagates
        the change via Update, not a local mutation (DEC-038 Part 2 design lock).
        """
        from suddenly.activitypub.inbox import handle_accept
        from suddenly.characters.models import (
            CharacterLink,
            LinkRequest,
            LinkRequestStatus,
            LinkType,
        )
        from tests.factories import CharacterFactory

        mocker.patch("suddenly.activitypub.signals._safe_delay")

        bob = self._remote_requester()
        target_mirror = CharacterFactory(
            name="Le Corbeau",
            status="npc",
            creator=bob,
            remote=True,
            ap_id="https://remote.social/characters/corbeau2",
        )
        lr = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=user,
            target_character=target_mirror,
            message="Je le reprends",
            status=LinkRequestStatus.PENDING,
        )

        accept = {
            "type": "Accept",
            "actor": "https://remote.social/users/bob",
            "object": f"https://remote.social/link-requests/{lr.pk}",
            "summary": "ok",
        }
        handle_accept(accept, "user", user.username)

        # Link is built for provenance, but the mirror itself is not mutated locally.
        assert CharacterLink.objects.filter(link_request=lr, type=LinkType.ADOPT).exists()
        target_mirror.refresh_from_db()
        assert target_mirror.owner != user
        assert target_mirror.status == "npc"
