"""
HTTP Signatures for ActivityPub.

Implements draft-cavage-http-signatures for signing outgoing
requests and verifying incoming ones.
"""

import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_key_pair() -> tuple[str, str]:
    """
    Generate a new RSA key pair for ActivityPub signatures.
    
    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode("utf-8")
    
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")
    
    return private_pem, public_pem


def sign_request(
    method: str,
    url: str,
    headers: dict,
    body: Optional[dict] = None,
    key_id: Optional[str] = None,
    private_key_pem: Optional[str] = None
) -> dict:
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
            with open(settings.AP_PRIVATE_KEY_PATH, "r") as f:
                private_key_pem = f.read()
        except FileNotFoundError:
            logger.error("Instance private key not found")
            return headers
    
    # Parse URL
    parsed = urlparse(url)
    
    # Build signing string
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    headers["Host"] = parsed.netloc
    headers["Date"] = date_str
    
    # Calculate digest if body present
    signed_headers = ["(request-target)", "host", "date"]
    
    if body:
        body_bytes = json.dumps(body).encode("utf-8")
        digest = base64.b64encode(
            hashlib.sha256(body_bytes).digest()
        ).decode("utf-8")
        headers["Digest"] = f"SHA-256={digest}"
        signed_headers.append("digest")
    
    # Build signing string
    signing_parts = []
    for header in signed_headers:
        if header == "(request-target)":
            signing_parts.append(f"(request-target): {method.lower()} {parsed.path}")
        else:
            signing_parts.append(f"{header}: {headers[header]}")
    
    signing_string = "\n".join(signing_parts)
    
    # Sign
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
        backend=default_backend()
    )
    
    signature = private_key.sign(
        signing_string.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256()
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


def verify_signature(request) -> tuple[bool, Optional[str]]:
    """
    Verify an incoming request's HTTP signature.
    
    Args:
        request: Django request object
    
    Returns:
        Tuple of (is_valid, key_id or error message)
    """
    import httpx
    
    signature_header = request.headers.get("Signature")
    if not signature_header:
        return False, "No Signature header"
    
    # Parse signature header
    sig_parts = {}
    for part in signature_header.split(","):
        key, _, value = part.partition("=")
        sig_parts[key.strip()] = value.strip('"')
    
    key_id = sig_parts.get("keyId")
    algorithm = sig_parts.get("algorithm", "rsa-sha256")
    headers_str = sig_parts.get("headers", "")
    signature_b64 = sig_parts.get("signature")
    
    if not all([key_id, signature_b64]):
        return False, "Invalid Signature header"
    
    if algorithm != "rsa-sha256":
        return False, f"Unsupported algorithm: {algorithm}"
    
    # Fetch actor's public key
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                key_id.split("#")[0],  # Actor URL
                headers={"Accept": "application/activity+json"}
            )
            response.raise_for_status()
            actor = response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch actor for verification: {e}")
        return False, f"Could not fetch actor: {e}"
    
    # Get public key
    public_key_pem = actor.get("publicKey", {}).get("publicKeyPem")
    if not public_key_pem:
        return False, "No public key in actor"
    
    # Build signing string
    signed_headers = headers_str.split()
    signing_parts = []
    
    for header in signed_headers:
        if header == "(request-target)":
            signing_parts.append(
                f"(request-target): {request.method.lower()} {request.path}"
            )
        else:
            value = request.headers.get(header.title())
            if value:
                signing_parts.append(f"{header}: {value}")
    
    signing_string = "\n".join(signing_parts)
    
    # Verify
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode("utf-8"),
            backend=default_backend()
        )
        
        signature = base64.b64decode(signature_b64)
        
        public_key.verify(
            signature,
            signing_string.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        return True, key_id
        
    except Exception as e:
        logger.warning(f"Signature verification failed: {e}")
        return False, f"Verification failed: {e}"


def ensure_instance_keys():
    """
    Ensure the instance has RSA keys for ActivityPub.
    
    Creates keys if they don't exist.
    """
    import os
    
    private_path = settings.AP_PRIVATE_KEY_PATH
    public_path = settings.AP_PUBLIC_KEY_PATH
    
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
