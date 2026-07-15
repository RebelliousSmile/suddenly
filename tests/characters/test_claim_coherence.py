"""Tests for the Claim coherence analysis (#128)."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import (
    Character,
    CharacterStatus,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
)
from suddenly.games.models import Game
from suddenly.muses.exceptions import MusesUnavailable
from suddenly.users.models import User

pytestmark = pytest.mark.django_db


def _make_claim(
    requester: User, recipient: User, game: Game, *, with_candidate: bool = True
) -> LinkRequest:
    """A PENDING Claim whose target NPC is created by ``recipient``."""
    npc = Character.objects.create(
        name="The Stranger",
        description="A hooded figure at the docks.",
        status=CharacterStatus.NPC,
        creator=recipient,
        origin_game=game,
    )
    candidate = None
    if with_candidate:
        candidate = Character.objects.create(
            name="Mara",
            description="A dockworker with a past.",
            status=CharacterStatus.PC,
            owner=requester,
            creator=requester,
            origin_game=game,
        )
    return LinkRequest.objects.create(
        type=LinkType.CLAIM,
        requester=requester,
        target_character=npc,
        proposed_character=candidate,
        message="Mara was at the docks that night.",
        status=LinkRequestStatus.PENDING,
    )


def _url(lr: LinkRequest) -> str:
    return reverse("characters:link_request_check_coherence", kwargs={"pk": lr.pk})


def test_recipient_gets_analysis_panel(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    # recipient=user owns the NPC; requester=other_user
    lr = _make_claim(requester=other_user, recipient=user, game=game)
    cls = mocker.patch("suddenly.muses.client.MusesClient")
    cls.return_value.analyze.return_value = {
        "compatibility": ["Both grim in tone."],
        "incompatibility": ["Timeline is tight."],
        "plausibility": "medium",
        "harmonization": ["Reconcile the scar detail."],
    }
    client.force_login(user)

    resp = client.post(_url(lr))

    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Both grim in tone." in body
    assert "Timeline is tight." in body
    assert "Reconcile the scar detail." in body
    # Two labelled corpora were sent.
    kwargs = cls.return_value.analyze.call_args.kwargs
    assert kwargs["feature"] == "claim_coherence"
    assert [c.label for c in kwargs["corpora"]] == ["npc", "candidate_pc"]
    assert kwargs["extra"]["argument"] == "Mara was at the docks that night."


def test_non_recipient_gets_404(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    lr = _make_claim(requester=other_user, recipient=user, game=game)
    stranger = User.objects.create(username="nosy")
    client.force_login(stranger)

    resp = client.post(_url(lr))

    assert resp.status_code == 404


def test_non_claim_request_not_reachable(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    npc = Character.objects.create(
        name="Adoptable", status=CharacterStatus.NPC, creator=user, origin_game=game
    )
    lr = LinkRequest.objects.create(
        type=LinkType.ADOPT,
        requester=other_user,
        target_character=npc,
        message="adopt please",
        status=LinkRequestStatus.PENDING,
    )
    client.force_login(user)

    resp = client.post(_url(lr))

    assert resp.status_code == 404  # the view is Claim-only


def test_degraded_note_when_hub_unavailable(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    lr = _make_claim(requester=other_user, recipient=user, game=game)
    cls = mocker.patch("suddenly.muses.client.MusesClient")
    cls.return_value.analyze.side_effect = MusesUnavailable("down")
    client.force_login(user)

    resp = client.post(_url(lr))

    assert resp.status_code == 200
    assert "unavailable" in resp.content.decode().lower()


def test_claim_without_candidate_shows_note(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    lr = _make_claim(requester=other_user, recipient=user, game=game, with_candidate=False)
    cls = mocker.patch("suddenly.muses.client.MusesClient")
    client.force_login(user)

    resp = client.post(_url(lr))

    assert resp.status_code == 200
    assert "nothing to analyse" in resp.content.decode().lower()
    cls.return_value.analyze.assert_not_called()
