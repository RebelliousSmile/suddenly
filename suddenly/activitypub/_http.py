"""
Shared HTTP helpers for ActivityPub actor fetching.

Centralizes the SSRF-safe actor fetch used across federation views,
signature verification, inbox processing, and Celery delivery tasks.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


def _is_blocked_ip(ip: str) -> bool:
    """Return True if an IP is private, loopback, or link-local (SSRF target)."""
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return bool(ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local)


def fetch_ap_actor(url: str, *, timeout: int = 10) -> dict[str, Any] | None:
    """
    Fetch an ActivityPub actor JSON document with SSRF protection.

    Resolves the hostname once, blocks private/loopback/link-local addresses,
    then connects directly to the validated IP so httpx cannot re-resolve the
    name and land on a different (internal) address — closing the DNS-rebinding
    TOCTOU window (SUD-F3). TLS SNI and certificate verification still use the
    original hostname. Only http/https schemes are allowed.

    Args:
        url: The actor URL to fetch.
        timeout: HTTP timeout in seconds (default 10).

    Returns:
        The parsed actor dict on a 200 response, or None on any failure.
    """
    import httpx

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None

    hostname = parsed.hostname
    if not hostname:
        return None

    # Resolve once. The IP we validate here is the exact IP we connect to below.
    try:
        resolved = socket.getaddrinfo(hostname, parsed.port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        resolved = []

    pinned_ip: str | None = None
    for _family, _type, _proto, _canon, sockaddr in resolved:
        ip = str(sockaddr[0])
        if _is_blocked_ip(ip):
            logger.warning("Blocked SSRF attempt to %s (%s)", url, ip)
            return None
        if pinned_ip is None:
            pinned_ip = ip

    request_url = url
    headers = {"Accept": "application/activity+json, application/ld+json"}
    extensions: dict[str, Any] = {}

    if pinned_ip is not None:
        # Connect straight to the validated IP; keep the Host header and use the
        # original hostname for TLS SNI + cert verification via httpx extensions.
        ip_host = f"[{pinned_ip}]" if ":" in pinned_ip else pinned_ip
        connect_netloc = f"{ip_host}:{parsed.port}" if parsed.port else ip_host
        request_url = urlunparse(parsed._replace(netloc=connect_netloc))
        headers["Host"] = f"{hostname}:{parsed.port}" if parsed.port else hostname
        extensions["sni_hostname"] = hostname

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(request_url, headers=headers, extensions=extensions)
        if resp.status_code == 200:
            return resp.json()  # type: ignore[no-any-return]
    except Exception:
        logger.warning("Failed to fetch actor %s", url, exc_info=True)

    return None
