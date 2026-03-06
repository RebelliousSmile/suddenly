"""
Tests for ActivityPub functionality.
"""

import json

import pytest

from suddenly.activitypub.serializers import (
    serialize_character,
    serialize_game,
    serialize_quote,
    serialize_report,
    serialize_user,
)
from suddenly.activitypub.signatures import generate_key_pair
from suddenly.characters.models import Character, CharacterStatus, Quote, QuoteVisibility
from suddenly.games.models import Report


class TestWebFinger:
    """Tests for WebFinger endpoint."""

    def test_webfinger_valid_user(self, client, user, settings):
        settings.DOMAIN = "test.social"

        response = client.get(
            "/.well-known/webfinger",
            {"resource": f"acct:{user.username}@test.social"}
        )

        assert response.status_code == 200
        assert response["Content-Type"] == "application/jrd+json"

        data = response.json()
        assert data["subject"] == f"acct:{user.username}@test.social"
        assert len(data["links"]) >= 1

        # Check for self link
        self_link = next(l for l in data["links"] if l["rel"] == "self")
        assert "application/activity+json" in self_link["type"]

    def test_webfinger_unknown_user(self, client, settings):
        settings.DOMAIN = "test.social"

        response = client.get(
            "/.well-known/webfinger",
            {"resource": "acct:nobody@test.social"}
        )

        assert response.status_code == 404

    def test_webfinger_wrong_domain(self, client, settings):
        settings.DOMAIN = "test.social"

        response = client.get(
            "/.well-known/webfinger",
            {"resource": "acct:user@other.social"}
        )

        assert response.status_code == 404

    def test_webfinger_missing_resource(self, client):
        response = client.get("/.well-known/webfinger")
        assert response.status_code == 400


class TestNodeInfo:
    """Tests for NodeInfo endpoints."""

    def test_nodeinfo_index(self, client, settings):
        settings.DOMAIN = "test.social"

        response = client.get("/.well-known/nodeinfo")

        assert response.status_code == 200
        data = response.json()
        assert "links" in data
        assert any("nodeinfo" in l["rel"] for l in data["links"])

    def test_nodeinfo_2_0(self, client, db, user, settings):
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

    def test_user_actor_json(self, client, user, settings):
        settings.DOMAIN = "test.social"

        response = client.get(
            f"/users/{user.username}",
            HTTP_ACCEPT="application/activity+json"
        )

        assert response.status_code == 200
        assert "application/activity+json" in response["Content-Type"]

        data = response.json()
        assert data["type"] == "Person"
        assert data["preferredUsername"] == user.username
        assert "inbox" in data
        assert "outbox" in data

    def test_user_actor_html_redirect(self, client, user):
        response = client.get(
            f"/users/{user.username}",
            HTTP_ACCEPT="text/html"
        )

        # Should redirect to profile page
        assert response.status_code == 302

    def test_user_outbox(self, client, user, game, settings):
        settings.DOMAIN = "test.social"

        # Create a published report
        report = Report.objects.create(
            title="Test Report",
            content="Test content",
            game=game,
            author=user,
            status="published"
        )

        response = client.get(
            f"/users/{user.username}/outbox",
            HTTP_ACCEPT="application/activity+json"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "OrderedCollection"


class TestGameActor:
    """Tests for Game actor endpoints."""

    def test_game_actor_json(self, client, game, settings):
        settings.DOMAIN = "test.social"

        response = client.get(
            f"/games/{game.id}",
            HTTP_ACCEPT="application/activity+json"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "Group"
        assert data["name"] == game.title

    def test_game_outbox(self, client, game, user, settings):
        settings.DOMAIN = "test.social"

        Report.objects.create(
            title="Test",
            content="Content",
            game=game,
            author=user,
            status="published"
        )

        response = client.get(
            f"/games/{game.id}/outbox",
            HTTP_ACCEPT="application/activity+json"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "OrderedCollection"


class TestCharacterActor:
    """Tests for Character actor endpoints."""

    def test_character_actor_json(self, client, character, settings):
        settings.DOMAIN = "test.social"

        response = client.get(
            f"/characters/{character.id}",
            HTTP_ACCEPT="application/activity+json"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "Person"
        assert data["name"] == character.name
        assert data["status"] == character.status


class TestSerializers:
    """Tests for ActivityPub serializers."""

    def test_serialize_user(self, user, settings):
        settings.DOMAIN = "test.social"

        data = serialize_user(user)

        assert data["type"] == "Person"
        assert data["preferredUsername"] == user.username
        assert data["name"] == user.get_display_name()
        assert "inbox" in data
        assert "outbox" in data
        assert "@context" in data

    def test_serialize_game(self, game, settings):
        settings.DOMAIN = "test.social"

        data = serialize_game(game)

        assert data["type"] == "Group"
        assert data["name"] == game.title
        assert "attributedTo" in data

    def test_serialize_character_npc(self, character, settings):
        settings.DOMAIN = "test.social"

        data = serialize_character(character)

        assert data["type"] == "Person"
        assert data["name"] == character.name
        assert data["status"] == "npc"

    def test_serialize_character_with_parent(self, db, character, user, game, settings):
        settings.DOMAIN = "test.social"

        fork = Character.objects.create(
            name="Fork Character",
            status=CharacterStatus.FORKED,
            creator=user,
            origin_game=game,
            parent=character
        )

        data = serialize_character(fork)

        assert "derivedFrom" in data
        assert character.actor_url in data["derivedFrom"]

    def test_serialize_report(self, report, settings):
        settings.DOMAIN = "test.social"

        data = serialize_report(report)

        assert data["type"] == "Article"
        assert data["content"] == report.content
        assert "attributedTo" in data

    def test_serialize_quote(self, db, character, user, settings):
        settings.DOMAIN = "test.social"

        quote = Quote.objects.create(
            content="To be or not to be",
            character=character,
            author=user,
            visibility=QuoteVisibility.PUBLIC
        )

        data = serialize_quote(quote)

        assert data["type"] == "Note"
        assert "To be or not to be" in data["content"]


class TestHTTPSignatures:
    """Tests for HTTP signature generation and verification."""

    def test_generate_key_pair(self):
        private_key, public_key = generate_key_pair()

        assert "BEGIN PRIVATE KEY" in private_key
        assert "BEGIN PUBLIC KEY" in public_key

    def test_key_pair_consistency(self):
        """Generated keys should be usable together."""
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization

        private_pem, public_pem = generate_key_pair()

        # Load private key
        private_key = serialization.load_pem_private_key(
            private_pem.encode(),
            password=None,
            backend=default_backend()
        )

        # Extract public key from private
        derived_public = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

        assert derived_public == public_pem

    def test_sign_request_adds_required_headers(self):
        """sign_request must set Signature, Date, and Host headers."""
        from suddenly.activitypub.signatures import sign_request

        private_pem, _ = generate_key_pair()
        headers: dict = {}
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

    def test_sign_request_adds_digest_when_body_given(self):
        """sign_request must add SHA-256 Digest header when body is provided."""
        from suddenly.activitypub.signatures import sign_request

        private_pem, _ = generate_key_pair()
        headers: dict = {}
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

    def test_verify_signature_returns_tuple(self):
        """Regression: verify_signature returns (bool, str), not a plain bool.

        The original bug: `if not verify_signature(request)` never rejected
        because a non-empty tuple is always truthy in Python.
        """
        from django.test import RequestFactory

        from suddenly.activitypub.signatures import verify_signature

        request = RequestFactory().post("/inbox")
        result = verify_signature(request)

        assert isinstance(result, tuple), "verify_signature must return (bool, str), not a plain bool"
        is_valid, _ = result
        assert is_valid is False

    def test_verify_signature_rejects_unsigned_request(self):
        """Request without Signature header must fail verification."""
        from django.test import RequestFactory

        from suddenly.activitypub.signatures import verify_signature

        request = RequestFactory().post("/inbox")
        is_valid, reason = verify_signature(request)

        assert is_valid is False
        assert "No Signature" in reason

    def test_sign_then_verify_roundtrip(self, mocker):
        """Full roundtrip: sign outgoing request, then verify incoming."""
        from django.test import RequestFactory

        from suddenly.activitypub.signatures import sign_request, verify_signature

        private_pem, public_pem = generate_key_pair()
        key_id = "https://remote.social/users/alice#main-key"
        target_url = "https://test.social/users/testuser/inbox"
        body = {"type": "Follow"}

        # Sign the outgoing request
        headers: dict = {}
        sign_request(
            method="POST",
            url=target_url,
            headers=headers,
            body=body,
            key_id=key_id,
            private_key_pem=private_pem,
        )

        # Reconstruct the incoming request
        meta: dict = {
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

        # Mock the actor fetch to return our public key
        mock_response = mocker.MagicMock()
        mock_response.json.return_value = {
            "publicKey": {"id": key_id, "publicKeyPem": public_pem}
        }
        mock_response.raise_for_status.return_value = None
        mock_ctx = mocker.MagicMock()
        mock_ctx.__enter__.return_value = mock_ctx
        mock_ctx.get.return_value = mock_response
        mocker.patch("suddenly.activitypub.signatures.httpx.Client", return_value=mock_ctx)

        is_valid, result = verify_signature(request)
        assert is_valid is True
        assert result == key_id

    def test_verify_signature_rejects_tampered_request(self, mocker):
        """Request with valid signature but tampered body must fail."""
        from django.test import RequestFactory

        from suddenly.activitypub.signatures import sign_request, verify_signature

        private_pem, public_pem = generate_key_pair()
        key_id = "https://remote.social/users/alice#main-key"

        # Sign with original body
        headers: dict = {}
        sign_request(
            method="POST",
            url="https://test.social/users/testuser/inbox",
            headers=headers,
            body={"type": "Follow"},
            key_id=key_id,
            private_key_pem=private_pem,
        )

        # Tamper: replace body content but keep old Digest
        meta: dict = {
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

        mock_response = mocker.MagicMock()
        mock_response.json.return_value = {
            "publicKey": {"id": key_id, "publicKeyPem": public_pem}
        }
        mock_response.raise_for_status.return_value = None
        mock_ctx = mocker.MagicMock()
        mock_ctx.__enter__.return_value = mock_ctx
        mock_ctx.get.return_value = mock_response
        mocker.patch("suddenly.activitypub.signatures.httpx.Client", return_value=mock_ctx)

        is_valid, _ = verify_signature(request)
        assert is_valid is False


class TestInbox:
    """Tests for inbox endpoints (receiving activities)."""

    def test_inbox_rejects_invalid_json(self, client, user):
        response = client.post(
            f"/users/{user.username}/inbox",
            data="not json",
            content_type="application/activity+json"
        )

        assert response.status_code == 400

    def test_inbox_accepts_valid_activity(self, client, user, mocker):
        # Mock the task to avoid actual processing
        mock_task = mocker.patch(
            "suddenly.activitypub.views.process_incoming_activity"
        )
        mock_task.delay = mocker.MagicMock()

        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Follow",
            "actor": "https://remote.social/users/alice",
            "object": f"https://test.social/users/{user.username}"
        }

        response = client.post(
            f"/users/{user.username}/inbox",
            data=json.dumps(activity),
            content_type="application/activity+json"
        )

        assert response.status_code == 202


class TestPublicKeyCache:
    """Tests for PublicKeyCache model and verify_signature cache/retry logic."""

    pytestmark = pytest.mark.django_db

    def test_fetch_public_key_stores_in_cache(self, mocker):
        """_fetch_public_key should store the key in PublicKeyCache."""
        from suddenly.activitypub.models import PublicKeyCache
        from suddenly.activitypub.signatures import _fetch_public_key

        _, public_pem = generate_key_pair()
        actor_url = "https://remote.social/users/alice"

        mock_response = mocker.MagicMock()
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

    def test_fetch_public_key_returns_none_on_timeout(self, mocker):
        """_fetch_public_key should return None on HTTP error."""
        from suddenly.activitypub.signatures import _fetch_public_key

        mock_client = mocker.MagicMock()
        mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
        mock_client.__exit__ = mocker.MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("Connection timeout")

        mocker.patch("httpx.Client", return_value=mock_client)

        result = _fetch_public_key("https://slow.server/users/bob")
        assert result is None

    def _make_signed_request(self, rf, private_pem, actor_url, path="/users/bob/inbox"):
        """Helper to create a properly signed Django request."""
        import base64
        import hashlib
        from datetime import UTC, datetime
        from urllib.parse import urlparse

        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

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

        private_key = serialization.load_pem_private_key(
            private_pem.encode(), password=None, backend=default_backend()
        )
        sig = base64.b64encode(
            private_key.sign(
                signing_string.encode(), padding.PKCS1v15(), hashes.SHA256()
            )
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

    def test_verify_uses_cached_key(self, mocker, rf):
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

        mock_fetch = mocker.patch(
            "suddenly.activitypub.signatures._fetch_public_key"
        )

        is_valid, result = verify_signature(request)

        assert is_valid is True
        assert result == f"{actor_url}#main-key"
        mock_fetch.assert_not_called()

    def test_verify_retries_on_stale_cached_key(self, mocker, rf):
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


class TestInboxRateLimit:
    """Tests for per-instance rate limiting on inbox endpoints."""

    pytestmark = pytest.mark.django_db

    def test_known_instance_not_rate_limited(self, rf, mocker):
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

    def test_unknown_instance_rate_limited(self, rf, mocker):
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

    def test_rate_limited_request_returns_403(self, rf, user, mocker):
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
