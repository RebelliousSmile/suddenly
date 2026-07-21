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
from django.utils import timezone

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
    resp = client.post(url, {"mode": "draft", "kind": RapportKind.DESCRIPTION, "content": "Wait."})

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
def test_scene_post_htmx_appends_inline(client: Client) -> None:
    """Mastodon-style: an HTMX post returns a fresh composer AND the new post
    (OOB) to append to the fil — no redirect."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    client.force_login(user)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(
        url,
        {"mode": "add", "kind": RapportKind.NARRATION, "content": "INLINE-BEAT"},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    # Fresh composer for the same scene …
    assert b'id="composer"' in resp.content
    # … plus the new post, OOB-appended to the fil.
    assert b"INLINE-BEAT" in resp.content
    assert b'hx-swap-oob="beforeend:#rapports-list"' in resp.content
    # …and a client event so the overlay closes reliably.
    assert resp["HX-Trigger"] == "composer-posted"


@pytest.mark.django_db
def test_scene_post_local_reply_creates_link(client: Client) -> None:
    """A discussion can reply to another post of the scene (RapportLink local)."""
    from suddenly.characters.models import CharacterStatus
    from suddenly.games.models import GameCast, RapportLink

    gm = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=gm)
    target = Rapport.objects.create(
        report=report, kind=RapportKind.NARRATION, content="A door creaks.", order=0
    )
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    GameCast.objects.create(game=game, character=npc, added_by=gm)

    client.force_login(gm)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(
        url,
        {
            "mode": "add",
            "kind": RapportKind.DISCUSSION,
            "content": "Who's there?",
            "actor": npc.slug,
            "reply_local": str(target.pk),
        },
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    new = Rapport.objects.exclude(pk=target.pk).get(report=report)
    link = RapportLink.objects.get(rapport=new)
    assert link.parent_rapport_id == target.pk
    assert link.parent_iri is None


@pytest.mark.django_db
def test_scene_post_iri_reply_creates_link(client: Client) -> None:
    from suddenly.characters.models import CharacterStatus
    from suddenly.games.models import GameCast, RapportLink

    gm = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=gm)
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    GameCast.objects.create(game=game, character=npc, added_by=gm)

    client.force_login(gm)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(
        url,
        {
            "mode": "add",
            "kind": RapportKind.DISCUSSION,
            "content": "I answer the fediverse.",
            "actor": npc.slug,
            "reply_iri": "https://dice.town/report/42#r7",
        },
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    link = RapportLink.objects.get(rapport__report=report)
    assert link.parent_iri == "https://dice.town/report/42#r7"
    assert link.parent_rapport_id is None


@pytest.mark.django_db
def test_scene_post_description_with_media(client: Client) -> None:
    """A description posted from the composer carries its image + alt."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)

    client.force_login(user)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    image = SimpleUploadedFile("s.png", _png_bytes(), content_type="image/png")
    resp = client.post(
        url,
        {
            "mode": "add",
            "kind": RapportKind.DESCRIPTION,
            "content": "A dim hall.",
            "image": image,
            "media_alt": "a dim hall",
        },
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    rapport = Rapport.objects.get(report=report)
    assert rapport.media.alt == "a dim hall"


@pytest.mark.django_db
def test_scene_edit_shows_fil_and_composer(client: Client) -> None:
    """The scene-edit page shows the composer next to the fil of posts."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    Rapport.objects.create(
        report=report,
        kind=RapportKind.NARRATION,
        content="EXISTING-BEAT",
        status=RapportStatus.PUBLISHED,
    )

    client.force_login(user)
    resp = client.get(reverse("games:report_edit", kwargs={"game_pk": game.pk, "pk": report.pk}))

    assert resp.status_code == 200
    # The composer sits in the left sidebar (home layout), called as-is…
    assert b'id="composer"' in resp.content
    assert b"Ajouter un post" in resp.content
    # …next to the fil of existing posts.
    assert b'id="rapports-list"' in resp.content
    assert b"EXISTING-BEAT" in resp.content


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
def test_scene_post_gm_cast_npc_accepted(client: Client) -> None:
    from suddenly.games.models import GameCast

    gm = UserFactory()
    game = GameFactory(owner=gm)
    report = ReportFactory(game=game, author=gm)
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    GameCast.objects.create(game=game, character=npc, added_by=gm)

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
def test_scene_open_character_from_another_game_allowed(client: Client) -> None:
    """A PC "peut intervenir dans n'importe quelle partie" (rule 2b): opening a
    scene in a game the PC does not originate from is allowed, not rejected."""
    player = UserFactory()
    game = GameFactory(owner=UserFactory())
    other_game = GameFactory(owner=UserFactory())
    pc = CharacterFactory(owner=player, status=CharacterStatus.PC, origin_game=other_game)

    client.force_login(player)
    url = reverse("games:scene_open", kwargs={"game_pk": game.pk})
    resp = client.post(url, {"character": pc.slug, "kind": RapportKind.NARRATION, "content": "x"})

    assert resp.status_code == 302
    assert Report.objects.filter(game=game, author=player).exists()


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
    resp = client.post(url, {"image": image, "alt": "A dim room"})

    assert resp.status_code == 201
    media = RapportMedia.objects.get(rapport=rapport)
    assert media.alt == "A dim room"


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


@pytest.mark.django_db
def test_media_add_twice_replaces_single_media(client: Client) -> None:
    """OneToOne: a second upload replaces, never appends — one media, always."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    rapport = Rapport.objects.create(report=report, kind=RapportKind.DESCRIPTION, content="Room.")

    client.force_login(user)
    url = reverse(
        "games:rapport_media_add",
        kwargs={"game_pk": game.pk, "pk": report.pk, "rapport_pk": rapport.pk},
    )
    client.post(url, {"image": SimpleUploadedFile("a.png", _png_bytes()), "alt": "first"})
    client.post(url, {"image": SimpleUploadedFile("b.png", _png_bytes()), "alt": "second"})

    assert RapportMedia.objects.filter(rapport=rapport).count() == 1
    assert RapportMedia.objects.get(rapport=rapport).alt == "second"


@pytest.mark.django_db
def test_media_remove(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    rapport = Rapport.objects.create(report=report, kind=RapportKind.DESCRIPTION, content="Room.")
    RapportMedia.objects.create(
        rapport=rapport, image=SimpleUploadedFile("a.png", _png_bytes()), alt="x"
    )

    client.force_login(user)
    url = reverse(
        "games:rapport_media_remove",
        kwargs={"game_pk": game.pk, "pk": report.pk, "rapport_pk": rapport.pk},
    )
    resp = client.post(url)
    assert resp.status_code == 204
    assert not RapportMedia.objects.filter(rapport=rapport).exists()


@pytest.mark.django_db
def test_media_remove_non_author_forbidden(client: Client) -> None:
    """POST rapport_media_remove as a non-author → 403, the media survives."""
    author = UserFactory()
    intruder = UserFactory()
    game = GameFactory(owner=author)
    report = ReportFactory(game=game, author=author)
    rapport = Rapport.objects.create(report=report, kind=RapportKind.DESCRIPTION, content="Room.")
    RapportMedia.objects.create(
        rapport=rapport, image=SimpleUploadedFile("a.png", _png_bytes()), alt="x"
    )

    client.force_login(intruder)
    url = reverse(
        "games:rapport_media_remove",
        kwargs={"game_pk": game.pk, "pk": report.pk, "rapport_pk": rapport.pk},
    )
    resp = client.post(url)

    assert resp.status_code == 403
    assert RapportMedia.objects.filter(rapport=rapport).exists()


# ---------------------------------------------------------------------------
# Unified composer (feed) — selectors, recompute, blocked send (rules 2a/2b/2c)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_composer_get_renders(client: Client) -> None:
    user = UserFactory()
    client.force_login(user)
    # HX request → the bare _composer.html partial (single source, both contexts).
    resp = client.get(reverse("games:composer"), HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert b'id="composer"' in resp.content


@pytest.mark.django_db
def test_composer_change_game_recomputes_kinds(client: Client) -> None:
    """Changing the game recomputes the kinds: narration for a game I own,
    none for a game I don't (rule 2c)."""
    user = UserFactory()
    my_game = GameFactory(owner=user)
    other_game = GameFactory(owner=UserFactory())

    client.force_login(user)
    url = reverse("games:composer")

    resp_gm = client.get(
        url, {"game": str(my_game.pk), "region": "context"}, HTTP_HX_REQUEST="true"
    )
    assert resp_gm.status_code == 200
    # Kinds render as bottom-sheet options (setKind('<value>')), not <option>s.
    assert b"setKind('narration')" in resp_gm.content

    resp_player = client.get(
        url, {"game": str(other_game.pk), "region": "context"}, HTTP_HX_REQUEST="true"
    )
    assert resp_player.status_code == 200
    assert b"setKind('narration')" not in resp_player.content
    assert b"setKind('action')" in resp_player.content


@pytest.mark.django_db
def test_composer_post_without_character_blocked(client: Client) -> None:
    """Rule 2a: nothing leaves without a personnage AND a partie — draft included."""
    user = UserFactory()
    game = GameFactory(owner=user)

    client.force_login(user)
    resp = client.post(
        reverse("games:composer"),
        {"mode": "draft", "game": str(game.pk), "kind": RapportKind.NARRATION, "content": "x"},
    )
    assert resp.status_code == 422
    assert not Report.objects.filter(game=game).exists()


@pytest.mark.django_db
def test_composer_post_opens_scene(client: Client) -> None:
    user = UserFactory()
    game = GameFactory(owner=user)
    pc = CharacterFactory(owner=user, status=CharacterStatus.PC, origin_game=game)

    client.force_login(user)
    resp = client.post(
        reverse("games:composer"),
        {
            "mode": "add",
            "game": str(game.pk),
            "character": pc.slug,
            "kind": RapportKind.NARRATION,
            "content": "Curtain.",
        },
    )
    assert resp.status_code == 302
    assert Report.objects.filter(game=game, author=user).exists()


@pytest.mark.django_db
def test_composer_post_opens_scene_with_media(client: Client) -> None:
    """Free-mode composer: a description opener may carry an image (rule 2e)."""
    user = UserFactory()
    game = GameFactory(owner=user)
    pc = CharacterFactory(owner=user, status=CharacterStatus.PC, origin_game=game)

    client.force_login(user)
    resp = client.post(
        reverse("games:composer"),
        {
            "mode": "add",
            "game": str(game.pk),
            "character": pc.slug,
            "kind": RapportKind.DESCRIPTION,
            "content": "Le vent tourne.",
            "image": SimpleUploadedFile("s.png", _png_bytes(), content_type="image/png"),
            "media_alt": "Ciel bas",
        },
    )
    assert resp.status_code == 302
    rapport = Rapport.objects.get(report__game=game)
    assert RapportMedia.objects.get(rapport=rapport).alt == "Ciel bas"


@pytest.mark.django_db
def test_composer_change_personnage_recomputes_game_field(client: Client) -> None:
    """Picking a personnage restricts the Partie options to its origin game
    plus any game it is already cast into (rule 2b, corrected for free mode)."""
    user = UserFactory()
    origin = GameFactory(owner=user, title="Origine")
    other = GameFactory(owner=UserFactory(), title="Ailleurs")
    pc = CharacterFactory(owner=user, status=CharacterStatus.PC, origin_game=origin)

    client.force_login(user)
    resp = client.get(
        reverse("games:composer"),
        {"character": pc.slug, "region": "game_field"},
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    body = resp.content.decode()
    assert origin.title in body
    assert other.title not in body


# ---------------------------------------------------------------------------
# + Nouveau PNJ — creates the Character AND the GameCast entry (rule 2d)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cast_npc_create_makes_character_and_cast(client: Client) -> None:
    from suddenly.characters.models import Character
    from suddenly.games.models import GameCast

    gm = UserFactory()
    game = GameFactory(owner=gm)

    client.force_login(gm)
    url = reverse("games:cast_npc_create", kwargs={"game_pk": game.pk})
    resp = client.post(url, {"name": "Le Passeur"}, HTTP_HX_REQUEST="true")

    assert resp.status_code == 200
    npc = Character.objects.get(name="Le Passeur")
    assert npc.status == CharacterStatus.NPC
    assert GameCast.objects.filter(game=game, character=npc).exists()
    # Returned region offers the fresh NPC as an actor.
    assert npc.slug.encode() in resp.content


@pytest.mark.django_db
def test_cast_npc_create_forbidden_for_non_gm(client: Client) -> None:
    from suddenly.characters.models import Character

    player = UserFactory()
    game = GameFactory(owner=UserFactory())

    client.force_login(player)
    url = reverse("games:cast_npc_create", kwargs={"game_pk": game.pk})
    resp = client.post(url, {"name": "Nope"})

    assert resp.status_code == 403
    assert not Character.objects.filter(name="Nope").exists()


# ---------------------------------------------------------------------------
# Per-rapport status wall — drafts stay out of the fil
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_draft_rapport_hidden_from_detail_for_non_author(client: Client) -> None:
    author = UserFactory()
    reader = UserFactory()
    game = GameFactory(owner=author)
    # Released so the non-author passes the wall (SUD-V2); the per-rapport draft
    # wall is what we assert here, independently of the scene-level wall.
    report = ReportFactory(
        game=game,
        author=author,
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.PUBLIC,
        released_at=timezone.now(),
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
    url = reverse("games:report_detail", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.get(url)

    assert resp.status_code == 200
    assert b"PUBLISHED-BEAT" in resp.content
    assert b"DRAFT-BEAT" not in resp.content


@pytest.mark.django_db
def test_draft_rapport_visible_to_author_in_detail(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    # Unreleased: the author still reads their own in-progress scene (bypasses
    # the wall) and sees their own draft rapports.
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
    url = reverse("games:report_detail", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.get(url)

    assert resp.status_code == 200
    assert b"DRAFT-BEAT" in resp.content


# ---------------------------------------------------------------------------
# Free-mode composer: last-scene preview (D1=B) refreshed out-of-band on
# ?region=context, with an editor link for the author (D2) or a read link else.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_composer_region_context_returns_last_scene_oob_editable(client: Client) -> None:
    """The author of the game's last published scene gets it back as an OOB swap
    with a link to the scene editor."""
    user = UserFactory()
    game = GameFactory(owner=user)
    pc = CharacterFactory(owner=user, status=CharacterStatus.PC, origin_game=game)
    scene = ReportFactory(
        game=game, author=user, status=ReportStatus.PUBLISHED, published_at=timezone.now()
    )
    RapportFactory(report=scene, order=0, status=RapportStatus.PUBLISHED)

    client.force_login(user)
    resp = client.get(
        reverse("games:composer"),
        {"region": "context", "character": pc.slug, "game": str(game.pk)},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    assert b'id="composer-last-scene"' in resp.content
    assert b"hx-swap-oob" in resp.content
    edit_url = reverse("games:report_edit", kwargs={"game_pk": game.pk, "pk": scene.pk})
    assert edit_url.encode() in resp.content


@pytest.mark.django_db
def test_composer_region_context_last_scene_read_link_for_non_author(client: Client) -> None:
    """A viewer who did not author the last scene gets a read link, not the editor
    (report_edit is author-only — D2)."""
    author = UserFactory()
    viewer = UserFactory()
    game = GameFactory(owner=author)
    pc = CharacterFactory(owner=viewer, status=CharacterStatus.PC, origin_game=game)
    scene = ReportFactory(
        game=game, author=author, status=ReportStatus.PUBLISHED, published_at=timezone.now()
    )
    RapportFactory(report=scene, order=0, status=RapportStatus.PUBLISHED)

    client.force_login(viewer)
    resp = client.get(
        reverse("games:composer"),
        {"region": "context", "character": pc.slug, "game": str(game.pk)},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    detail_url = reverse("games:report_detail", kwargs={"game_pk": game.pk, "pk": scene.pk})
    edit_url = reverse("games:report_edit", kwargs={"game_pk": game.pk, "pk": scene.pk})
    assert detail_url.encode() in resp.content
    assert edit_url.encode() not in resp.content  # never the editor for a non-author


@pytest.mark.django_db
def test_composer_region_context_empty_state_without_published_scene(client: Client) -> None:
    """A game with no published scene: the OOB target is present but shows the
    discreet empty note, no scene link."""
    user = UserFactory()
    game = GameFactory(owner=user)
    pc = CharacterFactory(owner=user, status=CharacterStatus.PC, origin_game=game)
    ReportFactory(game=game, author=user, status=ReportStatus.DRAFT)  # draft only

    client.force_login(user)
    resp = client.get(
        reverse("games:composer"),
        {"region": "context", "character": pc.slug, "game": str(game.pk)},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    assert b'id="composer-last-scene"' in resp.content
    assert "Aucune scène".encode() in resp.content


@pytest.mark.django_db
def test_frozen_composer_never_renders_last_scene_card(client: Client) -> None:
    """The last-scene preview is free-mode only: adding a post to a scene returns a
    fresh composer that never carries the card, even when the game has one."""
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    published = ReportFactory(
        game=game, author=user, status=ReportStatus.PUBLISHED, published_at=timezone.now()
    )
    RapportFactory(report=published, order=0, status=RapportStatus.PUBLISHED)

    client.force_login(user)
    url = reverse("games:scene_post_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(
        url,
        {"mode": "add_continue", "kind": RapportKind.NARRATION, "content": "Beat."},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    assert b'id="composer"' in resp.content
    assert "Dernière scène".encode() not in resp.content


@pytest.mark.django_db
def test_composer_requires_login(client: Client) -> None:
    """The composer is authenticated-only — anonymous requests redirect to login."""
    resp = client.get(reverse("games:composer"))

    assert resp.status_code == 302
    assert "/accounts/login/" in resp["Location"]
