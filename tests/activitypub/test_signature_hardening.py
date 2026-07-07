"""
Tests for HTTP Signature hardening (SUD-F1, SUD-F2).

Covers the requirements added to ``verify_signature``:
- A body must be authenticated by a signed, matching Digest (SUD-F1).
- Date must be present and signed; the skew window rejects stale requests.
- A minimum signed header set — (request-target), host, date — is enforced
  so a peer cannot sign only a trivial subset (SUD-F2).
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import urlparse

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from django.test import RequestFactory

from suddenly.activitypub.signatures import generate_key_pair, verify_signature

# verify_signature reads PublicKeyCache before hitting the network mock.
pytestmark = pytest.mark.django_db

KEY_ID = "https://remote.example/actor#main-key"
PATH = "/users/testuser/inbox"


def _sign(
    private_pem: str,
    *,
    body: str,
    signed_headers: list[str],
    date_str: str | None,
    digest_value: str | None,
    include_digest_header: bool = True,
) -> Any:
    """Build a POST request signed over exactly ``signed_headers``.

    ``digest_value`` controls the value used both in the signing string and the
    Digest header, letting tests sign one thing and send another.
    """
    parsed = urlparse(f"https://test.social{PATH}")
    host = parsed.netloc
    if date_str is None:
        date_str = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")

    available = {
        "(request-target)": f"(request-target): post {parsed.path}",
        "host": f"host: {host}",
        "date": f"date: {date_str}",
    }
    if digest_value is not None:
        available["digest"] = f"digest: {digest_value}"

    signing_string = "\n".join(available[h] for h in signed_headers)

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
        f'keyId="{KEY_ID}",'
        f'algorithm="rsa-sha256",'
        f'headers="{" ".join(signed_headers)}",'
        f'signature="{sig}"'
    )

    meta: dict[str, Any] = {
        "HTTP_HOST": host,
        "HTTP_DATE": date_str,
        "HTTP_SIGNATURE": sig_header,
    }
    if digest_value is not None and include_digest_header:
        meta["HTTP_DIGEST"] = digest_value

    return RequestFactory().post(
        PATH, data=body, content_type="application/activity+json", **meta
    )


def _digest_of(body: str) -> str:
    return "SHA-256=" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()


@pytest.fixture
def keys() -> tuple[str, str]:
    return generate_key_pair()


def _mock_key(mocker: Any, public_pem: str) -> None:
    mocker.patch(
        "suddenly.activitypub.signatures._fetch_public_key",
        return_value=public_pem,
    )


class TestDigestRequired:
    """SUD-F1: a body must be covered by a signed, matching Digest."""

    def test_valid_signed_digest_accepted(self, keys: tuple[str, str], mocker: Any) -> None:
        private_pem, public_pem = keys
        _mock_key(mocker, public_pem)
        body = json.dumps({"type": "Follow"})
        request = _sign(
            private_pem,
            body=body,
            signed_headers=["(request-target)", "host", "date", "digest"],
            date_str=None,
            digest_value=_digest_of(body),
        )
        is_valid, result = verify_signature(request)
        assert is_valid is True
        assert result == KEY_ID

    def test_body_without_signed_digest_rejected(
        self, keys: tuple[str, str], mocker: Any
    ) -> None:
        """A validly-signed request that omits digest from the signed set fails."""
        private_pem, public_pem = keys
        _mock_key(mocker, public_pem)
        body = json.dumps({"type": "Delete"})
        request = _sign(
            private_pem,
            body=body,
            signed_headers=["(request-target)", "host", "date"],
            date_str=None,
            digest_value=None,
        )
        is_valid, reason = verify_signature(request)
        assert is_valid is False
        assert reason == "Digest not covered by signature"

    def test_digest_mismatch_rejected(self, keys: tuple[str, str], mocker: Any) -> None:
        """Digest signed but not matching the delivered body → rejected."""
        private_pem, public_pem = keys
        _mock_key(mocker, public_pem)
        signed_body = json.dumps({"type": "Follow"})
        wrong_digest = _digest_of(signed_body)
        # Sign over wrong_digest, then deliver a different body.
        request = _sign(
            private_pem,
            body=json.dumps({"type": "Delete"}),
            signed_headers=["(request-target)", "host", "date", "digest"],
            date_str=None,
            digest_value=wrong_digest,
        )
        is_valid, reason = verify_signature(request)
        assert is_valid is False
        assert reason == "Digest mismatch"


class TestMinimumSignedHeaders:
    """SUD-F2: date mandatory + signed, and a minimum signed header set."""

    def test_missing_date_rejected(self, keys: tuple[str, str], mocker: Any) -> None:
        private_pem, public_pem = keys
        _mock_key(mocker, public_pem)
        body = json.dumps({"type": "Follow"})
        request = _sign(
            private_pem,
            body=body,
            signed_headers=["(request-target)", "host", "date", "digest"],
            date_str=None,
            digest_value=_digest_of(body),
        )
        # Strip the Date header the client would otherwise send.
        del request.META["HTTP_DATE"]
        is_valid, reason = verify_signature(request)
        assert is_valid is False
        assert reason == "Missing Date header"

    def test_request_target_not_signed_rejected(
        self, keys: tuple[str, str], mocker: Any
    ) -> None:
        private_pem, public_pem = keys
        _mock_key(mocker, public_pem)
        body = json.dumps({"type": "Follow"})
        request = _sign(
            private_pem,
            body=body,
            signed_headers=["host", "date", "digest"],
            date_str=None,
            digest_value=_digest_of(body),
        )
        is_valid, reason = verify_signature(request)
        assert is_valid is False
        assert reason is not None
        assert "Unsigned required headers" in reason
        assert "(request-target)" in reason
