"""
Tests for the ingest endpoint token check (SUD-F7).

The X-Ingest-Token comparison must be constant-time and behave correctly for
matching, mismatching, and missing tokens.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIRequestFactory

from suddenly.games.ingest import IngestReportView


def _check(token_header: str | None, settings: Any, configured: str = "s3cr3t") -> bool:
    settings.INGEST_TOKEN = configured
    headers = {"HTTP_X_INGEST_TOKEN": token_header} if token_header is not None else {}
    request = APIRequestFactory().post("/api/games/reports/ingest/", **headers)
    return IngestReportView()._check_token(request)


class TestIngestTokenCheck:
    def test_matching_token_accepted(self, settings: Any) -> None:
        assert _check("s3cr3t", settings) is True

    def test_wrong_token_rejected(self, settings: Any) -> None:
        assert _check("nope", settings) is False

    def test_missing_token_rejected(self, settings: Any) -> None:
        assert _check(None, settings) is False

    def test_no_configured_token_rejects_all(self, settings: Any) -> None:
        assert _check("anything", settings, configured="") is False


@pytest.mark.parametrize("provided", ["", "S3CR3T", "s3cr3t "])
def test_near_misses_rejected(provided: str, settings: Any) -> None:
    assert _check(provided, settings) is False
