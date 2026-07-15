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
    """Return True if an IP is a non-routable SSRF target.

    Blocks private/RFC1918, loopback, and link-local ranges, plus reserved,
    multicast, and the unspecified address (0.0.0.0 / ::) — all of which can
    reach internal or non-public destinations (SUD-F3).
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return bool(
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_reserved
        or ip_obj.is_multicast
        or ip_obj.is_unspecified
    )


def _validate_and_pin(url: str) -> tuple[str, dict[str, str], dict[str, Any]] | None:
    """Validate a URL for SSRF safety and return connection details for a pinned GET.

    Resolves the hostname once and blocks private/loopback/link-local addresses,
    then produces a request URL that connects directly to the validated IP so
    httpx cannot re-resolve the name and land on a different (internal) address —
    closing the DNS-rebinding TOCTOU window (SUD-F3). TLS SNI and certificate
    verification still use the original hostname. Only http/https schemes allowed.

    Returns:
        `None` if the request must be rejected outright (disallowed scheme, no
        hostname, or a resolved IP is blocked).
        Otherwise `(request_url, extra_headers, extensions)`. If the hostname did
        not resolve, the tuple carries the original URL with no pinning — the
        caller still attempts it, which simply fails to connect.
    """
    from django.conf import settings

    parsed = urlparse(url)
    # https is mandatory in production; http is only tolerated where explicitly
    # allowed (dev/test) via AP_ALLOW_INSECURE_HTTP. Plain http otherwise lets a
    # peer downgrade the fetch and strip TLS auth of the fetched document.
    allow_http = getattr(settings, "AP_ALLOW_INSECURE_HTTP", False)
    allowed_schemes = ("http", "https") if allow_http else ("https",)
    if parsed.scheme not in allowed_schemes:
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

    if pinned_ip is None:
        # Unresolved hostname: no IP to pin. Attempt the original URL; it will
        # fail to connect naturally. No SSRF risk since nothing resolved.
        return (url, {}, {})

    # Connect straight to the validated IP; keep the Host header and use the
    # original hostname for TLS SNI + cert verification via httpx extensions.
    ip_host = f"[{pinned_ip}]" if ":" in pinned_ip else pinned_ip
    connect_netloc = f"{ip_host}:{parsed.port}" if parsed.port else ip_host
    request_url = urlunparse(parsed._replace(netloc=connect_netloc))
    headers = {"Host": f"{hostname}:{parsed.port}" if parsed.port else hostname}
    extensions: dict[str, Any] = {"sni_hostname": hostname}
    return (request_url, headers, extensions)


def fetch_ap_json(url: str, *, accept: str, timeout: int = 10) -> dict[str, Any] | None:
    """Fetch a JSON document over HTTP(S) with SSRF protection.

    Shared by ActivityPub actor fetches and WebFinger lookups. Every outbound
    GET on a caller-influenced URL MUST go through this helper (or a wrapper),
    never a raw `httpx.Client`, so the SSRF allow/deny + IP-pin logic applies.

    Args:
        url: The URL to fetch.
        accept: The `Accept` header value (e.g. `application/jrd+json`).
        timeout: HTTP timeout in seconds (default 10).

    Returns:
        The parsed dict on a 200 response, or None on rejection or any failure.
    """
    import httpx

    pinned = _validate_and_pin(url)
    if pinned is None:
        return None
    request_url, extra_headers, extensions = pinned
    headers = {"Accept": accept, **extra_headers}

    try:
        # follow_redirects=False (explicit): a redirect would re-resolve to an
        # unvalidated host and reopen the SSRF window we just closed.
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            resp = client.get(request_url, headers=headers, extensions=extensions)
        if resp.status_code == 200:
            return resp.json()  # type: ignore[no-any-return]
    except Exception:
        logger.warning("Failed to fetch %s", url, exc_info=True)

    return None


def fetch_ap_actor(url: str, *, timeout: int = 10) -> dict[str, Any] | None:
    """Fetch an ActivityPub actor JSON document with SSRF protection.

    Thin wrapper over `fetch_ap_json` with the actor `Accept` header. Behavior is
    unchanged from the previous standalone implementation.
    """
    return fetch_ap_json(
        url,
        accept="application/activity+json, application/ld+json",
        timeout=timeout,
    )
