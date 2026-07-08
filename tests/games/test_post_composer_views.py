"""Tests for the post-composer endpoints and the per-rapport status wall.

Covers scene_post_create (add / add_continue / draft), scene_open, media upload
(kind restriction), and that draft rapports are hidden from the fil.
"""

from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import CharacterStatus
from suddenly.games.models import (
    CastRole,
    Rapport,
    RapportKind,
    RapportMedia,
    RapportStatus,
    Report,
    ReportCast,
    ReportStatus,
    ReportVisibility,
)
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


def _png_bytes() -> bytes:
    """A minimal valid 1x1 PNG (validated by Pillow on full_clean)."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), (255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# scene_post_create — modes + authorisation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_scene_post_add_publishes_and_redirects(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    client.force_login(user)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(url, {"mode": "add", "kind": RapportKind.NARRATION, "content": "Go."})

    assert resp.status_code == 302
    rapport = Rapport.objects.get(report=report)
    assert rapport.status == RapportStatus.PUBLISHED


@pytest.mark.django_db
def test_scene_post_draft_keeps_draft(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    client.force_login(user)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(url, {"mode": "draft", "kind": RapportKind.ACTION, "content": "Wait."})

    assert resp.status_code == 302
    assert Rapport.objects.get(report=report).status == RapportStatus.DRAFT


@pytest.mark.django_db
def test_scene_post_add_continue_returns_composer(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    client.force_login(user)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(
        url,
        {"mode": "add_continue", "kind": RapportKind.NARRATION, "content": "More."},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200  # empty composer, no redirect
    assert Rapport.objects.filter(report=report).count() == 1


@pytest.mark.django_db
def test_scene_post_non_author_forbidden(client: Client) -> None:
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)

    client.force_login(intruder)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(url, {"kind": RapportKind.NARRATION, "content": "Nope."})

    assert resp.status_code == 403
    assert not Rapport.objects.filter(report=report).exists()


@pytest.mark.django_db
def test_scene_post_player_foreign_actor_rejected(client: Client) -> None:
    """Player writing a discussion cannot voice an NPC that is not theirs."""
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    # The scene is authored by the player (their own report in the GM's game).
    report = ReportFactory(game=game, author=player)
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)

    client.force_login(player)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(
        url,
        {"kind": RapportKind.DISCUSSION, "content": "Hi", "actor": npc.slug},
    )

    assert resp.status_code == 422
    assert not Rapport.objects.filter(report=report).exists()


@pytest.mark.django_db
def test_scene_post_gm_owned_npc_accepted(client: Client) -> None:
    gm = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=gm)
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)

    client.force_login(gm)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(
        url,
        {"mode": "add", "kind": RapportKind.DISCUSSION, "content": "Hail.", "actor": npc.slug},
    )

    assert resp.status_code == 302
    rapport = Rapport.objects.get(report=report)
    assert rapport.actor_id == npc.pk


# ---------------------------------------------------------------------------
# scene_open — new scene
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_scene_open_creates_scene_and_cast(client: Client) -> None:
    gm = UserFactory()
    player = UserFactory()
    game = GameFactory(owner=gm)
    pc = CharacterFactory(owner=player, status=CharacterStatus.PC, origin_game=game)

    client.force_login(player)
    url = reverse("games:scene_open", kwargs={"game_pk": game.pk})
    resp = client.post(
        url,
        {"character": pc.slug, "kind": RapportKind.NARRATION, "content": "Curtain up."},
    )

    assert resp.status_code == 302
    report = Report.objects.get(game=game, author=player)
    assert report.status == ReportStatus.DRAFT
    assert report.released_at is None
    cast = ReportCast.objects.get(report=report)
    assert cast.character_id == pc.pk and cast.role == CastRole.MAIN
    assert Rapport.objects.filter(report=report).count() == 1


@pytest.mark.django_db
def test_scene_open_character_wrong_game_rejected(client: Client) -> None:
    player = UserFactory()
    game = GameFactory(owner=UserFactory())
    other_game = GameFactory(owner=UserFactory())
    pc = CharacterFactory(owner=player, status=CharacterStatus.PC, origin_game=other_game)

    client.force_login(player)
    url = reverse("games:scene_open", kwargs={"game_pk": game.pk})
    resp = client.post(url, {"character": pc.slug, "kind": RapportKind.NARRATION, "content": "x"})

    assert resp.status_code == 400
    assert not Report.objects.filter(game=game).exists()


# ---------------------------------------------------------------------------
# rapport_media_add — media, restricted to description kind
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_media_add_on_description_succeeds(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    rapport = Rapport.objects.create(report=report, kind=RapportKind.DESCRIPTION, content="A room.")

    client.force_login(user)
    url = reverse(
        "games:rapport_media_add",
        kwargs={"game_pk": game.pk, "pk": report.pk, "rapport_pk": rapport.pk},
    )
    image = SimpleUploadedFile("shot.png", _png_bytes(), content_type="image/png")
    resp = client.post(url, {"image": image, "alt_text": "A dim room"})

    assert resp.status_code == 201
    media = RapportMedia.objects.get(rapport=rapport)
    assert media.alt_text == "A dim room"


@pytest.mark.django_db
def test_media_add_on_non_description_rejected(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    rapport = Rapport.objects.create(
        report=report, kind=RapportKind.NARRATION, content="Narration."
    )

    client.force_login(user)
    url = reverse(
        "games:rapport_media_add",
        kwargs={"game_pk": game.pk, "pk": report.pk, "rapport_pk": rapport.pk},
    )
    image = SimpleUploadedFile("shot.png", _png_bytes(), content_type="image/png")
    resp = client.post(url, {"image": image})

    assert resp.status_code == 422
    assert not RapportMedia.objects.filter(rapport=rapport).exists()


@pytest.mark.django_db
def test_media_add_non_author_forbidden(client: Client) -> None:
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    rapport = Rapport.objects.create(report=report, kind=RapportKind.DESCRIPTION, content="A room.")

    client.force_login(intruder)
    url = reverse(
        "games:rapport_media_add",
        kwargs={"game_pk": game.pk, "pk": report.pk, "rapport_pk": rapport.pk},
    )
    image = SimpleUploadedFile("shot.png", _png_bytes(), content_type="image/png")
    resp = client.post(url, {"image": image})

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Per-rapport status wall — drafts stay out of the fil
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_draft_rapport_hidden_from_thread_for_non_author(client: Client) -> None:
    author = UserFactory()
    reader = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(
        game=game, author=author, status=ReportStatus.PUBLISHED, visibility=ReportVisibility.PUBLIC
    )
    Rapport.objects.create(
        report=report,
        kind=RapportKind.NARRATION,
        content="PUBLISHED-BEAT",
        status=RapportStatus.PUBLISHED,
    )
    Rapport.objects.create(
        report=report,
        kind=RapportKind.NARRATION,
        content="DRAFT-BEAT",
        status=RapportStatus.DRAFT,
    )

    client.force_login(reader)
    url = reverse("games:report_thread", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.get(url)

    assert resp.status_code == 200
    assert b"PUBLISHED-BEAT" in resp.content
    assert b"DRAFT-BEAT" not in resp.content


@pytest.mark.django_db
def test_draft_rapport_visible_to_author_in_thread(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(
        game=game, author=author, status=ReportStatus.PUBLISHED, visibility=ReportVisibility.PUBLIC
    )
    Rapport.objects.create(
        report=report,
        kind=RapportKind.NARRATION,
        content="DRAFT-BEAT",
        status=RapportStatus.DRAFT,
    )

    client.force_login(author)
    url = reverse("games:report_thread", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.get(url)

    assert resp.status_code == 200
    assert b"DRAFT-BEAT" in resp.content
