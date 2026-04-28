"""Tests for games.tasks — sync_foundry_systems Celery task."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from suddenly.games.models import GameSystem
from suddenly.games.tasks import _extract_systems, _parse_total_pages, sync_foundry_systems


def _make_listing_html(systems: list[tuple[str, str]], page: int = 1, total: int = 1) -> str:
    """Build a minimal FoundryVTT-style listing page HTML."""
    links = "\n".join(f'<a href="/packages/{slug}">{name}</a>' for slug, name in systems)
    return f"""
    <html><body>
    <p>Page {page} of {total}</p>
    {links}
    </body></html>
    """


class TestParseTotalPages:
    """Unit tests for _parse_total_pages."""

    def test_extracts_total_from_pagination(self) -> None:
        html = "<p>Page 1 of 10</p>"
        soup = BeautifulSoup(html, "html.parser")
        assert _parse_total_pages(soup) == 10

    def test_returns_1_when_no_pagination(self) -> None:
        html = "<p>No pagination here</p>"
        soup = BeautifulSoup(html, "html.parser")
        assert _parse_total_pages(soup) == 1

    def test_handles_multi_digit_pages(self) -> None:
        html = "<p>Page 3 of 42</p>"
        soup = BeautifulSoup(html, "html.parser")
        assert _parse_total_pages(soup) == 42


class TestExtractSystems:
    """Unit tests for _extract_systems."""

    def test_extracts_slug_and_name(self) -> None:
        html = '<a href="/packages/dnd5e">D&amp;D 5th Edition</a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_systems(soup)
        assert result == {"dnd5e": "D&D 5th Edition"}

    def test_ignores_non_package_links(self) -> None:
        html = '<a href="/articles/news">News</a><a href="/packages/mist-engine">Mist Engine</a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_systems(soup)
        assert result == {"mist-engine": "Mist Engine"}

    def test_ignores_deeper_package_paths(self) -> None:
        # /packages/dnd5e/download — 3 parts, should be skipped
        html = '<a href="/packages/dnd5e/download">Download</a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_systems(soup)
        assert result == {}

    def test_ignores_empty_name(self) -> None:
        html = '<a href="/packages/empty-slug">   </a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_systems(soup)
        assert result == {}

    def test_multiple_systems(self) -> None:
        html = _make_listing_html([("dnd5e", "D&D 5e"), ("pf2e", "Pathfinder 2e")])
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_systems(soup)
        assert "dnd5e" in result
        assert "pf2e" in result
        assert result["dnd5e"] == "D&D 5e"


class TestSyncFoundrySystems:
    """Integration-style tests for sync_foundry_systems (mocked HTTP)."""

    def _mock_response(self, html: str) -> MagicMock:
        resp = MagicMock()
        resp.text = html
        resp.raise_for_status = MagicMock()
        return resp

    @pytest.mark.django_db
    def test_creates_new_systems(self, mocker: Any) -> None:
        html = _make_listing_html([("dnd5e", "D&D 5e")], page=1, total=1)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._mock_response(html)
        mocker.patch("suddenly.games.tasks.httpx.Client", return_value=mock_client)

        result = sync_foundry_systems()

        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["deprecated"] == 0
        assert GameSystem.objects.filter(slug="dnd5e").exists()

    @pytest.mark.django_db
    def test_updates_existing_system(self, mocker: Any) -> None:
        GameSystem.objects.create(slug="dnd5e", name="Old Name", is_deprecated=False)
        html = _make_listing_html([("dnd5e", "D&D 5e")], page=1, total=1)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._mock_response(html)
        mocker.patch("suddenly.games.tasks.httpx.Client", return_value=mock_client)

        result = sync_foundry_systems()

        assert result["created"] == 0
        assert result["updated"] == 1
        gs = GameSystem.objects.get(slug="dnd5e")
        assert gs.name == "D&D 5e"

    @pytest.mark.django_db
    def test_deprecates_missing_systems(self, mocker: Any) -> None:
        GameSystem.objects.create(slug="old-system", name="Old System", is_deprecated=False)
        html = _make_listing_html([("dnd5e", "D&D 5e")], page=1, total=1)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._mock_response(html)
        mocker.patch("suddenly.games.tasks.httpx.Client", return_value=mock_client)

        result = sync_foundry_systems()

        assert result["deprecated"] == 1
        old = GameSystem.objects.get(slug="old-system")
        assert old.is_deprecated is True

    @pytest.mark.django_db
    def test_paginates_multiple_pages(self, mocker: Any) -> None:
        page1 = _make_listing_html([("dnd5e", "D&D 5e")], page=1, total=2)
        page2 = _make_listing_html([("pf2e", "Pathfinder 2e")], page=2, total=2)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [
            self._mock_response(page1),
            self._mock_response(page2),
        ]
        mocker.patch("suddenly.games.tasks.httpx.Client", return_value=mock_client)

        result = sync_foundry_systems()

        assert result["created"] == 2
        assert GameSystem.objects.filter(slug__in=["dnd5e", "pf2e"]).count() == 2

    @pytest.mark.django_db
    def test_sets_synced_at(self, mocker: Any) -> None:
        html = _make_listing_html([("dnd5e", "D&D 5e")], page=1, total=1)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._mock_response(html)
        mocker.patch("suddenly.games.tasks.httpx.Client", return_value=mock_client)

        before = datetime.now(tz=UTC)
        sync_foundry_systems()
        after = datetime.now(tz=UTC)

        gs = GameSystem.objects.get(slug="dnd5e")
        assert gs.synced_at is not None
        assert before <= gs.synced_at <= after

    @pytest.mark.django_db
    def test_retries_on_http_error(self, mocker: Any) -> None:
        import httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.HTTPError("connection failed")
        mocker.patch("suddenly.games.tasks.httpx.Client", return_value=mock_client)

        # Patch the task's retry method so we can verify it is called
        mocker.patch.object(
            sync_foundry_systems,
            "retry",
            side_effect=RuntimeError("retry called"),
        )

        with pytest.raises(RuntimeError, match="retry called"):
            sync_foundry_systems()
