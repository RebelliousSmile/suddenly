"""Tests for the post-composer service layer (Rapport composer).

Covers the two role viviers, role deduction, actor revalidation, and the
transactional gestures (create_scene_post / open_new_scene).
"""

from __future__ import annotations

import datetime
import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from suddenly.characters.models import (
    CharacterAppearance,
    CharacterStatus,
)
from suddenly.characters.services import build_owned_pc_queryset
from suddenly.games.models import (
    CastRole,
    GameCast,
    Rapport,
    RapportKind,
    RapportMedia,
    RapportStatus,
    Report,
    ReportCast,
    ReportStatus,
)
from suddenly.games.services import (
    available_kinds,
    build_actor_pool,
    build_composer_context,
    build_composer_feed_context,
    build_game_queryset,
    build_protagonist_pool,
    create_npc_in_cast,
    create_scene_post,
    is_game_master,
    latest_published_scene,
    latest_scene_rapports,
    open_new_scene,
    validate_actor_for_role,
)
from tests.factories import (
    CharacterFactory,
    GameFactory,
    RapportFactory,
    ReportFactory,
    UserFactory,
)


def _png_bytes() -> bytes:
    """A minimal valid 1x1 PNG (validated by Pillow on full_clean)."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), (255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


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
def test_protagonist_pool_excludes_non_pc_and_creator_only() -> None:
    """The free-mode Personnage picker must offer only valid protagonists.

    Regression: a character merely *created* by the user, or owned but not
    ``pc`` (adopted/claimed/forked), leaked into the picker and then failed
    ``open_new_scene``'s ``build_actor_pool`` re-check with a 422.
    """
    user = UserFactory()
    game = GameFactory(owner=user)

    own_pc = CharacterFactory(owner=user, status=CharacterStatus.PC, origin_game=game)
    mastered_npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    GameCast.objects.create(game=game, character=mastered_npc, added_by=user)

    # Excluded: owned but not PC (the reported "adopted" case).
    CharacterFactory(owner=user, status=CharacterStatus.ADOPTED, origin_game=game)
    # Excluded: merely created by the user, owned by someone else.
    CharacterFactory(owner=UserFactory(), creator=user, status=CharacterStatus.PC, origin_game=game)
    # Excluded: an NPC not cast into any game the user masters.
    CharacterFactory(status=CharacterStatus.NPC, origin_game=GameFactory(owner=UserFactory()))

    pks = set(build_protagonist_pool(user).values_list("pk", flat=True))
    assert pks == {own_pc.pk, mastered_npc.pk}


@pytest.mark.django_db
def test_protagonist_pool_excludes_pc_with_no_writable_game() -> None:
    """A PC with no game the user can write in is not offered (empty pick sheet).

    Shouldn't happen — a PC is born in a game — but an own PC whose only game is
    another player's private game (invisible → not writable) with no casting
    would otherwise be listed only to hit an empty partie list. Mirrors the
    "Ce personnage n'a encore aucune partie où écrire" dead end.
    """
    user = UserFactory()
    private_foreign_game = GameFactory(owner=UserFactory(), is_public=False)

    # Own PC born in a game the user cannot see/write, with no casting → excluded.
    CharacterFactory(owner=user, status=CharacterStatus.PC, origin_game=private_foreign_game)

    # Same PC, but cast into a public game → writable there → offered.
    public_game = GameFactory(is_public=True)
    castable = CharacterFactory(
        owner=user, status=CharacterStatus.PC, origin_game=private_foreign_game
    )
    GameCast.objects.create(game=public_game, character=castable, added_by=user)

    pks = set(build_protagonist_pool(user).values_list("pk", flat=True))
    assert pks == {castable.pk}


@pytest.mark.django_db
def test_actor_pool_gm_own_pcs_and_cast_npcs() -> None:
    """A GM voices their own PCs ∪ the NPCs in the game's cast (GameCast)."""
    gm = UserFactory()
    game = GameFactory(owner=gm)
    other_game = GameFactory(owner=UserFactory())

    gm_pc = CharacterFactory(owner=gm, status=CharacterStatus.PC, origin_game=other_game)
    cast_npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    GameCast.objects.create(game=game, character=cast_npc, added_by=gm)
    # Excluded: an NPC that exists but is NOT in this game's cast.
    CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    # Excluded: a PC belonging to another player.
    CharacterFactory(owner=UserFactory(), status=CharacterStatus.PC, origin_game=game)

    pks = set(build_actor_pool(gm, game).values_list("pk", flat=True))
    assert pks == {gm_pc.pk, cast_npc.pk}


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
def test_validate_actor_gm_accepts_cast_npc() -> None:
    gm = UserFactory()
    game = GameFactory(owner=gm)
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    GameCast.objects.create(game=game, character=npc, added_by=gm)
    # Must not raise — the NPC is in the game's cast.
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

    # description accepts an empty actor (optional) — good for a status-only test.
    rapport = create_scene_post(
        report=report,
        kind=RapportKind.DESCRIPTION,
        content="A dim room.",
        status=RapportStatus.DRAFT,
    )
    assert rapport.status == RapportStatus.DRAFT


@pytest.mark.django_db
def test_create_scene_post_action_requires_actor() -> None:
    """Rule 2c: an action needs someone who acts."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    with pytest.raises(ValidationError):
        create_scene_post(report=report, kind=RapportKind.ACTION, content="Runs.")
    assert not Rapport.objects.filter(report=report).exists()


@pytest.mark.django_db
def test_create_scene_post_narration_rejects_actor() -> None:
    """Rule 2c: narration is the narrative voice; it takes no actor."""
    gm = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=gm)
    pc = CharacterFactory(owner=gm, status=CharacterStatus.PC, origin_game=game)

    with pytest.raises(ValidationError):
        create_scene_post(report=report, kind=RapportKind.NARRATION, content="Dawn.", actor=pc)


@pytest.mark.django_db
def test_create_scene_post_action_as_actor_enters_cast() -> None:
    """A GM acting as a cast NPC succeeds, and voicing brings the actor into cast."""
    gm = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=gm)
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    GameCast.objects.create(game=game, character=npc, added_by=gm)

    rapport = create_scene_post(
        report=report, kind=RapportKind.ACTION, content="Draws steel.", actor=npc
    )
    assert rapport.actor_id == npc.pk
    assert GameCast.objects.filter(game=game, character=npc).exists()


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


@pytest.mark.django_db
def test_open_new_scene_any_game_enters_cast() -> None:
    """A PC may open a scene in a game it does not originate from (rule 2b),
    and doing so enters it into that game's cast."""
    player = UserFactory()
    origin = GameFactory(owner=UserFactory())
    other_game = GameFactory(owner=UserFactory())
    pc = CharacterFactory(owner=player, status=CharacterStatus.PC, origin_game=origin)

    report, _rapport = open_new_scene(
        user=player,
        game=other_game,
        character=pc,
        kind=RapportKind.NARRATION,
        content="Elsewhere.",
    )
    assert report.game_id == other_game.pk
    assert GameCast.objects.filter(game=other_game, character=pc).exists()


@pytest.mark.django_db
def test_open_new_scene_attaches_media_for_description() -> None:
    player = UserFactory()
    game = GameFactory(owner=player)
    pc = CharacterFactory(owner=player, status=CharacterStatus.PC, origin_game=game)
    image = SimpleUploadedFile("s.png", _png_bytes(), content_type="image/png")

    _report, rapport = open_new_scene(
        user=player,
        character=pc,
        kind=RapportKind.DESCRIPTION,
        content="Brume.",
        image=image,
        media_alt="Route déserte",
    )

    media = RapportMedia.objects.get(rapport=rapport)
    assert media.alt == "Route déserte"


# ---------------------------------------------------------------------------
# available_kinds — narration is GM-only (rule 2c)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_available_kinds_gm_includes_narration() -> None:
    gm = UserFactory()
    game = GameFactory(owner=gm)
    values = [v for v, _ in available_kinds(gm, game)]
    assert RapportKind.NARRATION in values


@pytest.mark.django_db
def test_available_kinds_player_excludes_narration() -> None:
    player = UserFactory()
    game = GameFactory(owner=UserFactory())
    values = [v for v, _ in available_kinds(player, game)]
    assert RapportKind.NARRATION not in values
    # The others remain available.
    assert RapportKind.ACTION in values
    assert RapportKind.DISCUSSION in values
    assert RapportKind.DESCRIPTION in values


# ---------------------------------------------------------------------------
# create_npc_in_cast — "+ Nouveau PNJ" (rule 2d)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_npc_in_cast_creates_character_and_cast() -> None:
    gm = UserFactory()
    game = GameFactory(owner=gm)

    npc = create_npc_in_cast(user=gm, game=game, name="La Gardienne")

    assert npc.status == CharacterStatus.NPC
    assert npc.origin_game_id == game.pk
    assert npc.creator_id == gm.pk
    entry = GameCast.objects.get(game=game, character=npc)
    assert entry.added_by_id == gm.pk
    # The fresh NPC is immediately incarnable by the GM.
    assert build_actor_pool(gm, game).filter(pk=npc.pk).exists()


# ---------------------------------------------------------------------------
# build_composer_feed_context — free-mode sidebar/composer context
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_build_composer_feed_context_free_mode_unselected() -> None:
    """No game/character picked yet: pickers are populated, role-scoped state is empty."""
    user = UserFactory()
    own_game = GameFactory(owner=user)
    own_pc = CharacterFactory(owner=user, status=CharacterStatus.PC, origin_game=own_game)

    ctx = build_composer_feed_context(user)

    assert ctx["frozen"] is False
    assert ctx["report"] is None
    assert ctx["game"] is None
    assert ctx["kinds"] == []
    assert ctx["can_send"] is False
    assert own_game in ctx["games"]
    assert own_pc in ctx["personnages"]


@pytest.mark.django_db
def test_build_composer_feed_context_with_game_and_character() -> None:
    """Once a game/personnage is picked, role-scoped kinds and actor pool populate."""
    gm = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(owner=gm, status=CharacterStatus.PC, origin_game=game)

    ctx = build_composer_feed_context(gm, game=game, character=pc)

    assert ctx["game"] == game
    assert ctx["is_gm"] is True
    assert RapportKind.NARRATION in [v for v, _ in ctx["kinds"]]
    assert ctx["can_send"] is True


# ---------------------------------------------------------------------------
# build_game_queryset — filtered by character (origin game ∪ GameCast)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_build_game_queryset_character_none_is_unfiltered() -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    assert game in build_game_queryset(user)


@pytest.mark.django_db
def test_build_game_queryset_filters_to_origin_and_cast() -> None:
    """A freshly created character has no GameCast entry yet — its origin game
    must still be offered, or it could never open its first scene."""
    user = UserFactory()
    origin = GameFactory(owner=user)
    cast_game = GameFactory(owner=UserFactory())
    unrelated = GameFactory(owner=UserFactory())
    pc = CharacterFactory(owner=user, status=CharacterStatus.PC, origin_game=origin)
    GameCast.objects.create(game=cast_game, character=pc, added_by=user)

    games = build_game_queryset(user, character=pc)

    assert origin in games
    assert cast_game in games
    assert unrelated not in games


@pytest.mark.django_db
def test_build_composer_feed_context_games_filtered_once_character_picked() -> None:
    user = UserFactory()
    origin = GameFactory(owner=user)
    unrelated = GameFactory(owner=UserFactory())
    pc = CharacterFactory(owner=user, status=CharacterStatus.PC, origin_game=origin)

    ctx = build_composer_feed_context(user, character=pc)

    assert origin in ctx["games"]
    assert unrelated not in ctx["games"]


# ---------------------------------------------------------------------------
# Last-scene preview under the free-mode composer (D1=B: last published scene of
# the game, any author; the link edits when the viewer authored it, reads else).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_latest_published_scene_returns_most_recent_published_any_author() -> None:
    gm = UserFactory()
    other = UserFactory()
    game = GameFactory(owner=gm)
    now = timezone.now()
    ReportFactory(game=game, author=gm, status=ReportStatus.DRAFT)  # drafts excluded
    older = ReportFactory(
        game=game,
        author=gm,
        status=ReportStatus.PUBLISHED,
        published_at=now - datetime.timedelta(days=2),
    )
    newer = ReportFactory(
        game=game,
        author=other,
        status=ReportStatus.PUBLISHED,
        published_at=now - datetime.timedelta(hours=1),
    )

    result = latest_published_scene(game)

    assert result == newer
    assert result != older


@pytest.mark.django_db
def test_latest_published_scene_none_when_only_drafts() -> None:
    game = GameFactory(owner=UserFactory())
    ReportFactory(game=game, status=ReportStatus.DRAFT)

    assert latest_published_scene(game) is None


@pytest.mark.django_db
def test_latest_published_scene_ignores_other_games() -> None:
    game = GameFactory(owner=UserFactory())
    other_game = GameFactory(owner=UserFactory())
    ReportFactory(game=other_game, status=ReportStatus.PUBLISHED, published_at=timezone.now())

    assert latest_published_scene(game) is None


@pytest.mark.django_db
def test_latest_scene_rapports_anti_chrono_and_bounded() -> None:
    scene = ReportFactory(status=ReportStatus.PUBLISHED)
    for i in range(5):
        RapportFactory(report=scene, order=i, status=RapportStatus.PUBLISHED)

    rapports = latest_scene_rapports(scene, limit=3)

    assert len(rapports) == 3  # bounded
    assert [r.order for r in rapports] == [4, 3, 2]  # newest first (-order)


@pytest.mark.django_db
def test_latest_scene_rapports_excludes_drafts() -> None:
    scene = ReportFactory(status=ReportStatus.PUBLISHED)
    published = RapportFactory(report=scene, order=0, status=RapportStatus.PUBLISHED)
    RapportFactory(report=scene, order=1, status=RapportStatus.DRAFT)

    rapports = latest_scene_rapports(scene)

    assert rapports == [published]


@pytest.mark.django_db
def test_feed_context_injects_last_scene_editable_for_author() -> None:
    """Free mode with a game: the author of the last published scene gets it back
    with ``last_scene_can_edit`` true (the link will open the editor, D2)."""
    gm = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(owner=gm, status=CharacterStatus.PC, origin_game=game)
    scene = ReportFactory(
        game=game, author=gm, status=ReportStatus.PUBLISHED, published_at=timezone.now()
    )
    RapportFactory(report=scene, order=0, status=RapportStatus.PUBLISHED)

    ctx = build_composer_feed_context(gm, game=game, character=pc)

    assert ctx["last_scene"] == scene
    assert list(ctx["last_scene_rapports"])
    assert ctx["last_scene_can_edit"] is True


@pytest.mark.django_db
def test_feed_context_last_scene_not_editable_for_non_author() -> None:
    """A viewer who did not author the last scene gets it read-only (D2 → read)."""
    author = UserFactory()
    viewer = UserFactory()
    game = GameFactory(owner=author)
    pc = CharacterFactory(owner=viewer, status=CharacterStatus.PC, origin_game=game)
    ReportFactory(
        game=game, author=author, status=ReportStatus.PUBLISHED, published_at=timezone.now()
    )

    ctx = build_composer_feed_context(viewer, game=game, character=pc)

    assert ctx["last_scene"] is not None
    assert ctx["last_scene_can_edit"] is False


@pytest.mark.django_db
def test_frozen_context_has_no_last_scene() -> None:
    """Frozen mode (a scene is set) never carries the last-scene preview."""
    gm = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=gm, status=ReportStatus.PUBLISHED)

    ctx = build_composer_context(gm, report=report)

    assert ctx["last_scene"] is None
    assert list(ctx["last_scene_rapports"]) == []
    assert ctx["last_scene_can_edit"] is False
