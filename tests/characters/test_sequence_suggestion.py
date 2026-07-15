"""Tests for the shared-sequence opening suggestion (#127)."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import (
    Character,
    CharacterLink,
    CharacterStatus,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
    SharedSequence,
    SharedSequenceStatus,
)
from suddenly.games.models import Game
from suddenly.muses.exceptions import MusesUnavailable
from suddenly.users.models import User

pytestmark = pytest.mark.django_db


def _make_sequence(
    user: User, other_user: User, game: Game, *, content: str = ""
) -> SharedSequence:
    """A DRAFT shared sequence whose PC is owned by ``user`` (a participant)."""
    pc = Character.objects.create(
        name="Ada the PC", status=CharacterStatus.PC, owner=user, creator=user, origin_game=game
    )
    npc = Character.objects.create(
        name="Bo the NPC", status=CharacterStatus.NPC, creator=other_user, origin_game=game
    )
    lr = LinkRequest.objects.create(
        type=LinkType.CLAIM,
        requester=user,
        target_character=npc,
        proposed_character=pc,
        message="let me in",
        status=LinkRequestStatus.ACCEPTED,
    )
    link = CharacterLink.objects.create(type=LinkType.CLAIM, source=pc, target=npc, link_request=lr)
    return SharedSequence.objects.create(
        link=link, content=content, status=SharedSequenceStatus.DRAFT
    )


def _url(seq: SharedSequence) -> str:
    return reverse("characters:sequence_suggest_opening", kwargs={"pk": seq.pk})


def _activate(u: User, *, credits: int = 5) -> None:
    u.muses_enabled = True
    u.muses_credits = credits
    u.save(update_fields=["muses_enabled", "muses_credits"])


def test_suggestion_rendered_for_empty_draft(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    seq = _make_sequence(user, other_user, game)
    _activate(user)
    cls = mocker.patch("suddenly.muses.client.MusesClient")
    cls.is_enabled.return_value = True
    cls.return_value.suggest.return_value = {"kind": "description", "text": "A dim crossroads inn."}
    client.force_login(user)

    resp = client.post(_url(seq))

    assert resp.status_code == 200
    body = resp.content.decode()
    assert "A dim crossroads inn." in body
    # Context carried both sheets + the link type.
    ctx = cls.return_value.suggest.call_args.args[0]
    assert len(ctx.characters) == 2
    assert ctx.link_type == LinkType.CLAIM
    # One credit spent on the successful suggestion (5 → 4).
    user.refresh_from_db()
    assert user.muses_credits == 4


def test_dialogue_downgraded_to_narration(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    seq = _make_sequence(user, other_user, game)
    _activate(user)
    cls = mocker.patch("suddenly.muses.client.MusesClient")
    cls.is_enabled.return_value = True
    cls.return_value.suggest.return_value = {"kind": "dialogue", "text": "Hello there."}
    client.force_login(user)

    resp = client.post(_url(seq))

    body = resp.content.decode()
    assert "Hello there." in body
    assert "dialogue" not in body  # never presented as dialogue (#127)


def test_not_offered_when_sequence_has_content(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    seq = _make_sequence(user, other_user, game, content="Already written.")
    suggest = mocker.patch("suddenly.muses.client.MusesClient")
    client.force_login(user)

    resp = client.post(_url(seq))

    assert resp.status_code == 302  # redirected back to the editor
    suggest.return_value.suggest.assert_not_called()


def test_degraded_note_when_hub_unavailable(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    seq = _make_sequence(user, other_user, game)
    _activate(user)
    cls = mocker.patch("suddenly.muses.client.MusesClient")
    cls.return_value.suggest.side_effect = MusesUnavailable("down")
    client.force_login(user)

    resp = client.post(_url(seq))

    assert resp.status_code == 200
    assert "unavailable" in resp.content.decode().lower()


def test_disabled_user_gets_unavailable(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    # muses_enabled left False — the hub is never called.
    seq = _make_sequence(user, other_user, game)
    cls = mocker.patch("suddenly.muses.client.MusesClient")
    client.force_login(user)

    resp = client.post(_url(seq))

    assert resp.status_code == 200
    assert "unavailable" in resp.content.decode().lower()
    cls.return_value.suggest.assert_not_called()


def test_no_credits_shows_note_without_calling_hub(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    seq = _make_sequence(user, other_user, game)
    _activate(user, credits=0)  # enabled but empty balance
    cls = mocker.patch("suddenly.muses.client.MusesClient")
    cls.is_enabled.return_value = True
    client.force_login(user)

    resp = client.post(_url(seq))

    assert resp.status_code == 200
    assert "credit" in resp.content.decode().lower()
    cls.return_value.suggest.assert_not_called()


def test_non_participant_gets_404(
    client: Client, mocker: Any, user: User, other_user: User, game: Game
) -> None:
    seq = _make_sequence(user, other_user, game)
    stranger = User.objects.create(username="stranger")
    client.force_login(stranger)

    resp = client.post(_url(seq))

    assert resp.status_code == 404
