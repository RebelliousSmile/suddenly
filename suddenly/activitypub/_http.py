"""
Shared HTTP helpers for ActivityPub actor fetching.

Centralizes the SSRF-safe actor fetch used across federation views,
signature verification, inbox processing, and Celery delivery tasks.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def fetch_ap_actor(url: str, *, timeout: int = 10) -> dict[str, Any] | None:
    """
    Fetch an ActivityPub actor JSON document with SSRF protection.

    Blocks requests to private, loopback, or link-local addresses by
    resolving the hostname before issuing the HTTP request. Only http/https
    schemes are allowed.

    Args:
        url: The actor URL to fetch.
        timeout: HTTP timeout in seconds (default 10).

    Returns:
        The parsed actor dict on a 200 response, or None on any failure.
    """
    import socket

    import httpx

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None

    # Block private/loopback IPs (SSRF protection)
    hostname = parsed.hostname
    if hostname:
        try:
            resolved = socket.getaddrinfo(hostname, None)
            for _, _, _, _, addr in resolved:
                ip = addr[0]
                import ipaddress

                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                    logger.warning("Blocked SSRF attempt to %s (%s)", url, ip)
                    return None
        except (socket.gaierror, ValueError):
            pass  # DNS resolution failed or invalid IP — let httpx handle it

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(
                url,
                headers={"Accept": "application/activity+json, application/ld+json"},
            )
        if resp.status_code == 200:
            return resp.json()  # type: ignore[no-any-return]
    except Exception:
        logger.warning("Failed to fetch actor %s", url, exc_info=True)

    return None
