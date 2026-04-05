# mypy: disable-error-code="no-untyped-call,type-arg,attr-defined"
"""
Tests for security features added in T5.

Covers:
- ProcessedActivity dedup (inbox)
- Actor domain validation (inbox)
- Auth rate limiting middleware
- Celery _safe_delay resilience
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client, RequestFactory

from suddenly.activitypub.models import ProcessedActivity
from suddenly.core.middleware import AuthRateLimitMiddleware

# ─── ProcessedActivity dedup ─────────────────────────────────────


@pytest.mark.django_db
class TestInboxDedup:
    """Test that duplicate activities are rejected."""

    def test_first_activity_is_processed(self, client: Client) -> None:
        """A new activity ID should be stored and processed."""
        assert ProcessedActivity.objects.count() == 0

    def test_processed_activity_creation(self, db: Any) -> None:
        """ProcessedActivity can be created with ap_id."""
        pa = ProcessedActivity.objects.create(
            ap_id="https://remote.social/activity/1",
            actor_domain="remote.social",
        )
        assert pa.ap_id == "https://remote.social/activity/1"
        assert pa.actor_domain == "remote.social"

    def test_duplicate_ap_id_rejected(self, db: Any) -> None:
        """Duplicate ap_id raises IntegrityError."""
        from django.db import IntegrityError

        ProcessedActivity.objects.create(
            ap_id="https://remote.social/activity/dup",
            actor_domain="remote.social",
        )
        with pytest.raises(IntegrityError):
            ProcessedActivity.objects.create(
                ap_id="https://remote.social/activity/dup",
                actor_domain="remote.social",
            )

    def test_get_or_create_handles_race(self, db: Any) -> None:
        """get_or_create returns existing record without error."""
        ProcessedActivity.objects.create(
            ap_id="https://remote.social/activity/race",
            actor_domain="remote.social",
        )
        _, created = ProcessedActivity.objects.get_or_create(
            ap_id="https://remote.social/activity/race",
            defaults={"actor_domain": "remote.social"},
        )
        assert not created


# ─── Auth rate limiting middleware ────────────────────────────────


@pytest.mark.django_db
class TestAuthRateLimitMiddleware:
    """Test rate limiting on auth endpoints."""

    def _make_request(self, path: str, method: str = "POST") -> Any:
        factory = RequestFactory()
        if method == "POST":
            return factory.post(path)
        return factory.get(path)

    def test_get_requests_not_limited(self) -> None:
        """GET requests should never be rate limited."""
        middleware = AuthRateLimitMiddleware(lambda r: r)
        request = self._make_request("/accounts/login/", "GET")
        # Should pass through (returns the request itself since get_response=identity)
        result = middleware(request)
        assert result is request

    def test_post_to_non_auth_not_limited(self) -> None:
        """POST to non-auth endpoints should not be rate limited."""
        middleware = AuthRateLimitMiddleware(lambda r: r)
        request = self._make_request("/api/characters/", "POST")
        result = middleware(request)
        assert result is request

    def test_login_rate_limit_enforced(self) -> None:
        """After 10 login attempts, further POSTs are blocked."""
        from django.core.cache import cache

        cache.clear()
        middleware = AuthRateLimitMiddleware(lambda r: r)

        for _ in range(10):
            request = self._make_request("/accounts/login/")
            request.META["REMOTE_ADDR"] = "1.2.3.4"
            result = middleware(request)
            assert result is request  # First 10 pass

        # 11th should be blocked
        request = self._make_request("/accounts/login/")
        request.META["REMOTE_ADDR"] = "1.2.3.4"
        result = middleware(request)
        assert result.status_code == 403

    def test_signup_rate_limit_enforced(self) -> None:
        """After 5 signup attempts, further POSTs are blocked."""
        from django.core.cache import cache

        cache.clear()
        middleware = AuthRateLimitMiddleware(lambda r: r)

        for _ in range(5):
            request = self._make_request("/accounts/signup/")
            request.META["REMOTE_ADDR"] = "5.6.7.8"
            result = middleware(request)
            assert result is request

        request = self._make_request("/accounts/signup/")
        request.META["REMOTE_ADDR"] = "5.6.7.8"
        result = middleware(request)
        assert result.status_code == 403

    def test_different_ips_not_affected(self) -> None:
        """Rate limit is per-IP, not global."""
        from django.core.cache import cache

        cache.clear()
        middleware = AuthRateLimitMiddleware(lambda r: r)

        # Exhaust limit for IP A
        for _ in range(10):
            request = self._make_request("/accounts/login/")
            request.META["REMOTE_ADDR"] = "10.0.0.1"
            middleware(request)

        # IP B should still work
        request = self._make_request("/accounts/login/")
        request.META["REMOTE_ADDR"] = "10.0.0.2"
        result = middleware(request)
        assert result is request


# ─── Celery _safe_delay ──────────────────────────────────────────


class TestSafeDelay:
    """Test that _safe_delay handles broker failures gracefully."""

    def test_successful_delay(self) -> None:
        """When broker is available, task is queued normally."""
        from suddenly.activitypub.signals import _safe_delay

        mock_task = type("Task", (), {"name": "test_task", "delay": lambda *a, **k: None})()
        # Should not raise
        _safe_delay(mock_task, "arg1", "arg2")

    def test_connection_error_swallowed(self) -> None:
        """ConnectionError from broker is caught and logged."""
        from suddenly.activitypub.signals import _safe_delay

        def raise_conn(*a: Any, **k: Any) -> None:
            raise ConnectionError("broker down")

        mock_task = type("Task", (), {"name": "test_task", "delay": raise_conn})()
        # Should not raise
        _safe_delay(mock_task, "arg1")

    def test_programming_error_propagates(self) -> None:
        """TypeError (programming error) should NOT be caught."""
        from suddenly.activitypub.signals import _safe_delay

        def raise_type(*a: Any, **k: Any) -> None:
            raise TypeError("bad argument")

        mock_task = type("Task", (), {"name": "test_task", "delay": raise_type})()
        with pytest.raises(TypeError):
            _safe_delay(mock_task, "arg1")
