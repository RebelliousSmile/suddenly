"""
Custom middleware for Suddenly.
"""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden

logger = logging.getLogger(__name__)


class AuthRateLimitMiddleware:
    """
    Simple rate limiting for authentication endpoints.

    Uses Django's cache framework — no Redis required (falls back to DB cache).
    Limits:
    - /accounts/login/  : 10 attempts per minute per IP
    - /accounts/signup/ : 5 attempts per minute per IP
    """

    RATE_LIMITS: dict[str, tuple[int, int]] = {
        "/accounts/login/": (10, 60),  # 10 per 60s
        "/accounts/signup/": (5, 60),  # 5 per 60s
    }

    def __init__(self, get_response: object) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method != "POST":
            return self.get_response(request)

        for path_prefix, (max_attempts, window) in self.RATE_LIMITS.items():
            if request.path.startswith(path_prefix):
                if self._is_rate_limited(request, path_prefix, max_attempts, window):
                    logger.warning(
                        "Auth rate limit exceeded: %s from %s",
                        path_prefix,
                        self._get_client_ip(request),
                    )
                    return HttpResponseForbidden("Too many attempts. Please try again later.")

        return self.get_response(request)

    def _is_rate_limited(
        self,
        request: HttpRequest,
        path: str,
        max_attempts: int,
        window: int,
    ) -> bool:
        from django.core.cache import cache

        try:
            ip = self._get_client_ip(request)
            cache_key = f"auth_rl:{path}:{ip}"
            attempts = cache.get(cache_key, 0)

            if attempts >= max_attempts:
                return True

            cache.set(cache_key, attempts + 1, window)
        except Exception:  # noqa: BLE001 — fail open if cache is down
            logger.warning("Rate limit cache error, allowing request", exc_info=True)

        return False

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Extract client IP, using REMOTE_ADDR only.

        X-Forwarded-For is NOT trusted here — Railway and most reverse
        proxies set REMOTE_ADDR correctly. Trusting XFF without proxy
        validation enables rate limit bypass via header spoofing.
        """
        return request.META.get("REMOTE_ADDR", "unknown")
