"""
Tests for UserLanguageMiddleware thread-safety and language activation.
"""

from __future__ import annotations

import concurrent.futures
from typing import Any

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from suddenly.core.middleware import UserLanguageMiddleware


def make_middleware(captured: list[str]) -> UserLanguageMiddleware:
    """Build a middleware instance that captures the active language during the request."""

    def get_response(request: HttpRequest) -> HttpResponse:
        from django.utils import translation

        captured.append(translation.get_language() or "")
        return HttpResponse("ok")

    return UserLanguageMiddleware(get_response)


class TestUserLanguageMiddleware:
    def test_anonymous_no_override(self, rf: RequestFactory, mocker: Any) -> None:
        request = rf.get("/")
        request.user = mocker.MagicMock(is_authenticated=False)
        captured: list[str] = []
        mock_trans = mocker.patch("suddenly.core.middleware.translation")
        mock_trans.get_language.return_value = "fr"

        make_middleware(captured)(request)

        mock_trans.activate.assert_not_called()
        mock_trans.deactivate.assert_not_called()

    def test_authenticated_empty_pref_no_override(self, rf: RequestFactory, mocker: Any) -> None:
        request = rf.get("/")
        request.user = mocker.MagicMock(is_authenticated=True, interface_language="")
        mock_trans = mocker.patch("suddenly.core.middleware.translation")

        make_middleware([])(request)

        mock_trans.activate.assert_not_called()

    def test_authenticated_valid_pref_activates(self, rf: RequestFactory, mocker: Any) -> None:
        request = rf.get("/")
        request.user = mocker.MagicMock(is_authenticated=True, interface_language="en")
        mock_trans = mocker.patch("suddenly.core.middleware.translation")

        make_middleware([])(request)

        mock_trans.activate.assert_called_once_with("en")
        assert request.LANGUAGE_CODE == "en"
        mock_trans.deactivate.assert_called_once()

    def test_authenticated_invalid_pref_no_exception(self, rf: RequestFactory, mocker: Any) -> None:
        request = rf.get("/")
        request.user = mocker.MagicMock(is_authenticated=True, interface_language="xx-yy")
        mock_trans = mocker.patch("suddenly.core.middleware.translation")
        mock_trans.activate.side_effect = Exception("bad lang")

        response = make_middleware([])(request)

        assert response.status_code == 200
        mock_trans.deactivate.assert_not_called()  # activated=False on exception

    def test_deactivate_called_in_finally(self, rf: RequestFactory, mocker: Any) -> None:
        request = rf.get("/")
        request.user = mocker.MagicMock(is_authenticated=True, interface_language="en")
        mock_trans = mocker.patch("suddenly.core.middleware.translation")

        def failing_get_response(req: HttpRequest) -> HttpResponse:
            raise ValueError("view crashed")

        with pytest.raises(ValueError):
            UserLanguageMiddleware(failing_get_response)(request)

        mock_trans.deactivate.assert_called_once()


@pytest.mark.django_db
class TestUserLanguageMiddlewareConcurrency:
    def test_no_language_leak_between_concurrent_requests(self, rf: RequestFactory) -> None:
        """Thread with en must not contaminate a concurrent thread with no pref."""
        from unittest.mock import MagicMock

        captured: dict[str, str] = {}

        def run(interface_language: str, key: str) -> None:
            request = rf.get("/")
            request.user = MagicMock(
                is_authenticated=bool(interface_language),
                interface_language=interface_language,
            )
            langs: list[str] = []
            mw = make_middleware(langs)
            mw(request)
            captured[key] = langs[0] if langs else ""

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(run, "en", "en_request")
            f2 = executor.submit(run, "", "anon_request")
            concurrent.futures.wait([f1, f2])

        assert captured.get("en_request") == "en"
        assert captured.get("anon_request") != "en", "Language leaked from en thread to anon thread"
