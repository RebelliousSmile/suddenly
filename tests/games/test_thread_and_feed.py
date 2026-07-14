"""
Rendering tests for the scene thread reading view (Front #8) and the Friends
feed shell (Front #9).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import Character, CharacterStatus
from suddenly.games.models import Game, Rapport, RapportKind, Report, ReportStatus
from suddenly.users.models import User


@pytest.fixture(autouse=True)
def _isolated_env(settings: Any) -> Any:
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    cache.clear()
    yield
    cache.clear()


def _published_report(author: User, game: Game) -> Report:
    return Report.objects.create(
        title="The heist",
        content="Full scene body.",
        game=game,
        author=author,
        status=ReportStatus.PUBLISHED,
    )


def _scene_with_rapports(author: User, game: Game) -> Report:
    report = _published_report(author, game)
    actor = Character.objects.create(
        name="Vasquez", status=CharacterStatus.NPC, creator=author, origin_game=game
    )
    Rapport.objects.create(
        report=report, kind=RapportKind.NARRATION, content="The vault door creaks open."
    )
    Rapport.objects.create(
        report=report, kind=RapportKind.DISCUSSION, content="We're in.", actor=actor
    )
    return report


class TestSceneThreadReading:
    def test_thread_renders_reading_hierarchy(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        report = _scene_with_rapports(user, game)
        client.force_login(user)

        url = reverse("games:report_thread", kwargs={"game_pk": game.pk, "pk": report.pk})
        resp = client.get(url)

        assert resp.status_code == 200
        body = resp.content.decode()
        # The rapport text is present as body copy...
        assert "The vault door creaks open." in body
        # ...and the discussion is attributed to its actor.
        assert "We&#x27;re in." in body or "We're in." in body
        assert "Vasquez" in body


class TestFriendsFeedInterventions:
    def test_amis_feed_renders_for_user_without_follows(
        self, db: Any, client: Client, user: User
    ) -> None:
        client.force_login(user)
        resp = client.get("/")
        assert resp.status_code == 200
        # Feed shell renders even with an empty Friends stream.
        assert "feed-content" in resp.content.decode()
