"""Tests for reversible character archival (#125)."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import (
    Character,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
)
from suddenly.characters.services import build_character_queryset
from suddenly.users.models import User


@pytest.fixture
def logged_client(client: Client, user: User) -> Client:
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestArchiveQueryset:
    def test_archived_character_hidden_from_discovery(self, character: Character) -> None:
        assert character in build_character_queryset()
        character.is_archived = True
        character.save(update_fields=["is_archived"])
        assert character not in build_character_queryset()


@pytest.mark.django_db
class TestArchiveViews:
    def test_creator_can_archive(self, logged_client: Client, character: Character) -> None:
        url = reverse("characters:archive", kwargs={"slug": character.slug})
        resp = logged_client.post(url)
        assert resp.status_code == 302
        assert resp.url == reverse("characters:list")
        character.refresh_from_db()
        assert character.is_archived is True

    def test_creator_can_restore(self, logged_client: Client, character: Character) -> None:
        character.is_archived = True
        character.save(update_fields=["is_archived"])
        url = reverse("characters:unarchive", kwargs={"slug": character.slug})
        resp = logged_client.post(url)
        assert resp.status_code == 302
        character.refresh_from_db()
        assert character.is_archived is False

    def test_non_creator_cannot_archive(
        self, client: Client, other_user: User, character: Character
    ) -> None:
        client.force_login(other_user)
        url = reverse("characters:archive", kwargs={"slug": character.slug})
        resp = client.post(url)
        assert resp.status_code == 404
        character.refresh_from_db()
        assert character.is_archived is False

    def test_get_not_allowed(self, logged_client: Client, character: Character) -> None:
        url = reverse("characters:archive", kwargs={"slug": character.slug})
        resp = logged_client.get(url)
        assert resp.status_code == 405

    def test_archive_blocked_by_pending_link(
        self, logged_client: Client, other_user: User, character: Character
    ) -> None:
        LinkRequest.objects.create(
            type=LinkType.CLAIM,
            requester=other_user,
            target_character=character,
            status=LinkRequestStatus.PENDING,
        )
        url = reverse("characters:archive", kwargs={"slug": character.slug})
        resp = logged_client.post(url)
        # Redirected back to detail (blocked), character NOT archived.
        assert resp.status_code == 302
        assert resp.url == reverse("characters:detail", kwargs={"slug": character.slug})
        character.refresh_from_db()
        assert character.is_archived is False


@pytest.mark.django_db
class TestArchiveListSection:
    def test_archived_section_lists_owned_archived(
        self, settings: Any, logged_client: Client, character: Character
    ) -> None:
        settings.STORAGES = {
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
        character.is_archived = True
        character.save(update_fields=["is_archived"])
        resp = logged_client.get(reverse("characters:list"))
        assert resp.status_code == 200
        body = resp.content.decode()
        # Restore control present for the archived character.
        assert reverse("characters:unarchive", kwargs={"slug": character.slug}) in body
