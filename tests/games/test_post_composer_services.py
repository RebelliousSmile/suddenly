"""Tests for the post-composer service layer (Rapport composer).

Covers the two role viviers, role deduction, actor revalidation, and the
transactional gestures (create_scene_post / open_new_scene).
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from suddenly.characters.models import (
    CharacterAppearance,
    CharacterStatus,
)
from suddenly.characters.services import build_owned_pc_queryset
from suddenly.games.models import (
    CastRole,
    Rapport,
    RapportKind,
    RapportStatus,
    Report,
    ReportCast,
    ReportStatus,
)
from suddenly.games.services import (
    build_actor_pool,
    create_scene_post,
    is_game_master,
    open_new_scene,
    validate_actor_for_role,
)
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory

# ---------------------------------------------------------------------------
# build_owned_pc_queryset — "mes PJs" (player)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_owned_pc_queryset_only_my_pcs() -> None:
    player = UserFactory()
    other = UserFactory()
    game = GameFactory(owner=other)

    my_pc = CharacterFactory(owner=player, status=CharacterStatus.PC, origin_game=game)
    # Noise that must be excluded:
    CharacterFactory(owner=other, status=CharacterStatus.PC, origin_game=game)  # not mine
    CharacterFactory(owner=player, status=CharacterStatus.NPC, origin_game=game)  # not a PC
    CharacterFactory(status=CharacterStatus.NPC, origin_game=game)  # unowned NPC

    pks = set(build_owned_pc_queryset(player).values_list("pk", flat=True))
    assert pks == {my_pc.pk}


# ---------------------------------------------------------------------------
# is_game_master — role deduction
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_is_game_master_true_for_owner() -> None:
    gm = UserFactory()
    game = GameFactory(owner=gm)
    assert is_game_master(gm, game) is True


@pytest.mark.django_db
def test_is_game_master_false_for_player() -> None:
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    assert is_game_master(player, game) is False


# ---------------------------------------------------------------------------
# build_actor_pool — role vivier
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_actor_pool_player_only_own_pcs() -> None:
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)

    my_pc = CharacterFactory(owner=player, status=CharacterStatus.PC, origin_game=game)
    CharacterFactory(status=CharacterStatus.NPC, origin_game=game)  # NPC — not for a player
    CharacterFactory(owner=gm, status=CharacterStatus.PC, origin_game=game)  # GM's PC

    pks = set(build_actor_pool(player, game).values_list("pk", flat=True))
    assert pks == {my_pc.pk}


@pytest.mark.django_db
def test_actor_pool_gm_own_pcs_and_owned_npcs() -> None:
    gm = UserFactory()
    game = GameFactory(owner=gm)
    other_game = GameFactory(owner=UserFactory())

    gm_pc = CharacterFactory(owner=gm, status=CharacterStatus.PC, origin_game=other_game)
    owned_npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    # Excluded: an NPC of a game the GM does not own.
    CharacterFactory(status=CharacterStatus.NPC, origin_game=other_game)
    # Excluded: a PC belonging to another player.
    CharacterFactory(owner=UserFactory(), status=CharacterStatus.PC, origin_game=game)

    pks = set(build_actor_pool(gm, game).values_list("pk", flat=True))
    assert pks == {gm_pc.pk, owned_npc.pk}


# ---------------------------------------------------------------------------
# validate_actor_for_role — server revalidation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validate_actor_none_always_ok() -> None:
    player = UserFactory()
    game = GameFactory(owner=UserFactory())
    # Must not raise.
    validate_actor_for_role(player, game, None)


@pytest.mark.django_db
def test_validate_actor_player_rejects_foreign_npc() -> None:
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)

    with pytest.raises(ValidationError) as exc:
        validate_actor_for_role(player, game, npc)
    assert "actor" in exc.value.message_dict


@pytest.mark.django_db
def test_validate_actor_gm_accepts_owned_npc() -> None:
    gm = UserFactory()
    game = GameFactory(owner=gm)
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    # Must not raise.
    validate_actor_for_role(gm, game, npc)


# ---------------------------------------------------------------------------
# create_scene_post — status per mode + clean rule
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_scene_post_published_default() -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    rapport = create_scene_post(report=report, kind=RapportKind.NARRATION, content="It begins.")
    assert rapport.status == RapportStatus.PUBLISHED
    assert rapport.report_id == report.pk


@pytest.mark.django_db
def test_create_scene_post_draft() -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    rapport = create_scene_post(
        report=report,
        kind=RapportKind.ACTION,
        content="Held back.",
        status=RapportStatus.DRAFT,
    )
    assert rapport.status == RapportStatus.DRAFT


@pytest.mark.django_db
def test_create_scene_post_discussion_requires_actor() -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    with pytest.raises(ValidationError):
        create_scene_post(report=report, kind=RapportKind.DISCUSSION, content="Hi?")
    assert not Rapport.objects.filter(report=report).exists()


@pytest.mark.django_db
def test_create_scene_post_rejects_foreign_actor() -> None:
    """Author is a player; actor is an NPC they may not voice → rejected."""
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=player)
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)

    with pytest.raises(ValidationError):
        create_scene_post(report=report, kind=RapportKind.DISCUSSION, content="Hi", actor=npc)
    assert not Rapport.objects.filter(report=report).exists()


# ---------------------------------------------------------------------------
# open_new_scene — transactional scene opening
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_open_new_scene_creates_report_rapport_cast() -> None:
    player = UserFactory()
    gm = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(owner=player, status=CharacterStatus.PC, origin_game=game)

    report, rapport = open_new_scene(
        user=player, character=pc, kind=RapportKind.NARRATION, content="A new scene."
    )

    report.refresh_from_db()
    assert report.game_id == game.pk
    assert report.author_id == player.pk
    assert report.status == ReportStatus.DRAFT
    assert report.released_at is None  # wall stays closed

    assert rapport.report_id == report.pk
    assert rapport.status == RapportStatus.PUBLISHED

    cast = ReportCast.objects.get(report=report)
    assert cast.character_id == pc.pk
    assert cast.role == CastRole.MAIN

    # Appearance is NOT materialised eagerly — it is born at publication.
    assert not CharacterAppearance.objects.filter(report=report).exists()


@pytest.mark.django_db
def test_open_new_scene_rolls_back_on_invalid_rapport() -> None:
    """A discussion opener without an actor fails clean → nothing is created."""
    player = UserFactory()
    gm = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(owner=player, status=CharacterStatus.PC, origin_game=game)

    reports_before = Report.objects.count()
    with pytest.raises(ValidationError):
        open_new_scene(user=player, character=pc, kind=RapportKind.DISCUSSION, content="Hi?")

    assert Report.objects.count() == reports_before
    assert not ReportCast.objects.filter(character=pc).exists()


@pytest.mark.django_db
def test_open_new_scene_rejects_character_outside_pool() -> None:
    """A player cannot open a scene featuring a character that is not theirs."""
    player = UserFactory()
    gm = UserFactory()
    game = GameFactory(owner=gm)
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)

    reports_before = Report.objects.count()
    with pytest.raises(ValidationError):
        open_new_scene(user=player, character=npc, kind=RapportKind.NARRATION, content="Nope.")
    assert Report.objects.count() == reports_before
