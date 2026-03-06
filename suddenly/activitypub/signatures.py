"""
HTTP Signatures for ActivityPub.

Implements draft-cavage-http-signatures for signing outgoing
requests and verifying incoming ones.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from django.conf import settings
from django.http import HttpRequest

logger = logging.getLogger(__name__)


def generate_key_pair() -> tuple[str, str]:
    """
    Generate a new RSA key pair for ActivityPub signatures.

    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    return private_pem, public_pem


def sign_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict[str, object] | None = None,
    key_id: str | None = None,
    private_key_pem: str | None = None,
) -> dict[str, str]:
    """
    Sign an outgoing HTTP request.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Target URL
        headers: Request headers (will be modified)
        body: Request body (for digest)
        key_id: Key identifier URL (defaults to instance actor)
        private_key_pem: Private key PEM (defaults to instance key)

    Returns:
        Updated headers dict with Signature header
    """
    import json

    # Default to instance key
    if not key_id:
        key_id = f"{settings.AP_BASE_URL}/actor#main-key"

    if not private_key_pem:
        # Load instance private key
        try:
            with open(settings.AP_PRIVATE_KEY_PATH) as f:
                private_key_pem = f.read()
        except FileNotFoundError:
            logger.error("Instance private key not found")
            return headers

    # Parse URL
    parsed = urlparse(url)

    # Build signing string
    now = datetime.now(UTC)
    date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

    headers["Host"] = parsed.netloc
    headers["Date"] = date_str

    # Calculate digest if body present
    signed_headers = ["(request-target)", "host", "date"]

    if body:
        body_bytes = json.dumps(body).encode("utf-8")
        digest = base64.b64encode(hashlib.sha256(body_bytes).digest()).decode("utf-8")
        headers["Digest"] = f"SHA-256={digest}"
        signed_headers.append("digest")

    # Build signing string
    signing_parts: list[str] = []
    for header in signed_headers:
        if header == "(request-target)":
            signing_parts.append(f"(request-target): {method.lower()} {parsed.path}")
        else:
            signing_parts.append(f"{header}: {headers[header]}")

    signing_string = "\n".join(signing_parts)

    # Cast to RSAPrivateKey since we know we use RSA keys (DEC-018)
    from typing import cast

    private_key = cast(
        RSAPrivateKey,
        serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=None, backend=default_backend()
        ),
    )

    signature = private_key.sign(
        signing_string.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()
    )

    signature_b64 = base64.b64encode(signature).decode("utf-8")

    # Build Signature header
    sig_header = (
        f'keyId="{key_id}",'
        f'algorithm="rsa-sha256",'
        f'headers="{" ".join(signed_headers)}",'
        f'signature="{signature_b64}"'
    )

    headers["Signature"] = sig_header

    return headers


def _fetch_public_key(actor_url: str) -> str | None:
    """
    Fetch the public key PEM from a remote actor and update cache.

    Returns:
        The public key PEM string, or None on failure.
    """
    import httpx

    from .models import PublicKeyCache

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                actor_url,
                headers={"Accept": "application/activity+json, application/ld+json"},
            )
            response.raise_for_status()
            actor = response.json()
    except Exception as e:
        logger.warning("Failed to fetch actor %s: %s", actor_url, e)
        return None

    pem: str | None = actor.get("publicKey", {}).get("publicKeyPem")
    if not pem:
        logger.warning("No public key in actor %s", actor_url)
        return None

    PublicKeyCache.objects.update_or_create(
        actor_url=actor_url,
        defaults={"public_key_pem": pem},
    )
    return pem


def _build_signing_string(request: HttpRequest, signed_headers: list[str]) -> str:
    """Build the signing string from request and header list."""
    parts: list[str] = []
    for header in signed_headers:
        if header == "(request-target)":
            method = request.method or "GET"
            parts.append(f"(request-target): {method.lower()} {request.path}")
        else:
            value = request.headers.get(header.title())
            if value:
                parts.append(f"{header}: {value}")
    return "\n".join(parts)


def _verify_with_key(public_key_pem: str, signature_b64: str, signing_string: str) -> bool:
    """Verify a signature against a public key. Returns True if valid."""
    try:
        # Cast to RSAPublicKey since we only support RSA keys (DEC-018)
        from typing import cast

        public_key = cast(
            RSAPublicKey,
            serialization.load_pem_public_key(
                public_key_pem.encode("utf-8"),
                backend=default_backend(),
            ),
        )
        public_key.verify(
            base64.b64decode(signature_b64),
            signing_string.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def verify_signature(request: HttpRequest) -> tuple[bool, str | None]:
    """
    Verify an incoming request's HTTP signature.

    Uses cached public keys when available. On verification failure
    with a cached key, re-fetches the key once before rejecting.

    Args:
        request: Django request object

    Returns:
        Tuple of (is_valid, key_id or error message)
    """
    from .models import PublicKeyCache

    signature_header = request.headers.get("Signature")
    if not signature_header:
        return False, "No Signature header"

    # Parse signature header
    sig_parts: dict[str, str] = {}
    for part in signature_header.split(","):
        key, _, value = part.partition("=")
        sig_parts[key.strip()] = value.strip('"')

    key_id = sig_parts.get("keyId")
    algorithm = sig_parts.get("algorithm", "rsa-sha256")
    headers_str = sig_parts.get("headers", "")
    signature_b64 = sig_parts.get("signature")

    if not key_id or not signature_b64:
        return False, "Invalid Signature header"

    if algorithm != "rsa-sha256":
        return False, f"Unsupported algorithm: {algorithm}"

    actor_url = key_id.split("#")[0]
    signing_string = _build_signing_string(request, headers_str.split())

    # Try cached key first
    cached = PublicKeyCache.objects.filter(actor_url=actor_url).first()
    if cached:
        if _verify_with_key(cached.public_key_pem, signature_b64, signing_string):
            return True, key_id

        # Cached key failed — re-fetch once
        logger.info("Cached key failed for %s, re-fetching", actor_url)
        fresh_pem = _fetch_public_key(actor_url)
        if fresh_pem and _verify_with_key(fresh_pem, signature_b64, signing_string):
            return True, key_id

        logger.warning("Signature invalid after key re-fetch for %s", actor_url)
        return False, f"Verification failed for {actor_url}"

    # No cached key — fetch
    pem = _fetch_public_key(actor_url)
    if not pem:
        return False, f"Could not fetch actor: {actor_url}"

    if _verify_with_key(pem, signature_b64, signing_string):
        return True, key_id

    logger.warning("Signature invalid for %s (first fetch)", actor_url)
    return False, f"Verification failed for {actor_url}"


def ensure_instance_keys() -> None:
    """
    Ensure the instance has RSA keys for ActivityPub.

    Creates keys if they don't exist.
    """
    import os

    private_path = str(settings.AP_PRIVATE_KEY_PATH)
    public_path = str(settings.AP_PUBLIC_KEY_PATH)

    # Create keys directory
    os.makedirs(os.path.dirname(private_path), exist_ok=True)

    if not os.path.exists(private_path) or not os.path.exists(public_path):
        logger.info("Generating instance ActivityPub keys...")

        private_pem, public_pem = generate_key_pair()

        with open(private_path, "w") as f:
            f.write(private_pem)
        os.chmod(private_path, 0o600)

        with open(public_path, "w") as f:
            f.write(public_pem)

        logger.info("Instance keys generated")
