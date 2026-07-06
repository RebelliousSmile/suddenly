"""
Tests for the shared absolute_media_url helper.
"""

from __future__ import annotations

from pytest_django.fixtures import SettingsWrapper

from suddenly.activitypub.url_utils import absolute_media_url


class _FakeFileField:
    def __init__(self, url: str) -> None:
        self.url = url


class TestAbsoluteMediaUrl:
    def test_passthrough_for_absolute_url(self) -> None:
        # Simulates S3Storage/R2, which already returns an absolute URL.
        field = _FakeFileField("https://bucket.r2.cloudflarestorage.com/avatars/x.jpg")

        assert absolute_media_url(field) == (
            "https://bucket.r2.cloudflarestorage.com/avatars/x.jpg"
        )

    def test_prefixes_relative_url_with_domain(self, settings: SettingsWrapper) -> None:
        # Simulates FileSystemStorage, which returns a relative /media/ path.
        settings.DOMAIN = "example.com"
        field = _FakeFileField("/media/avatars/x.jpg")

        assert absolute_media_url(field) == "https://example.com/media/avatars/x.jpg"
