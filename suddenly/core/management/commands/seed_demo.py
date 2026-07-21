"""
Management command: populate the local database with demo content.

Generates a coherent, bilingual (fr/en) graph of games, characters, reports,
rapports, quotes, follows and character links — enough volume to exercise
pagination, infinite scroll and the language filters.

Every generated user is prefixed with ``demo_``, which makes ``--flush``
a safe, targeted cleanup (cascades remove their games/characters/reports).

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --flush
    python manage.py seed_demo --users 60 --games 40 --reports 800
    make docker-seed
"""

from __future__ import annotations

import io
import random
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from suddenly.characters.models import (
    Character,
    CharacterStatus,
    Follow,
    LinkType,
    Quote,
    QuoteVisibility,
    SharedSequence,
    SharedSequenceStatus,
)
from suddenly.characters.services import LinkService
from suddenly.core.models import Tag
from suddenly.games.models import (
    CastRole,
    Game,
    GameCast,
    MarkerKind,
    Rapport,
    RapportKind,
    RapportLink,
    RapportMarker,
    RapportMedia,
    RapportStatus,
    Report,
    ReportCast,
    ReportVisibility,
)
from suddenly.games.services import publish_report

User = get_user_model()

DEMO_PREFIX = "demo_"
DEMO_PASSWORD = "demo1234"

# --- Content pools ---------------------------------------------------------
# Two independent pools: a game (and its reports) is either French or English,
# so language filters and `contentMap` have something real to discriminate on.

TAGS = [
    "cyberpunk",
    "gothique",
    "enquete",
    "huis-clos",
    "post-apo",
    "space-opera",
    "horror",
    "investigation",
    "low-fantasy",
    "steampunk",
    "oneshot",
    "campagne",
]

SYSTEMS = [
    "Mist Engine",
    "Blades in the Dark",
    "Ecryme",
    "Cypher System",
    "Apocalypse World",
    "Vampire: la Mascarade",
    "Cthulhu Hack",
    "Ironsworn",
]

GIVEN_NAMES = [
    "Alma",
    "Cassian",
    "Ivo",
    "Nadia",
    "Bastien",
    "Thea",
    "Oskar",
    "Livia",
    "Enzo",
    "Mireille",
    "Soren",
    "Yasmin",
    "Garrett",
    "Isadora",
    "Milo",
    "Nora",
    "Rafael",
    "Ondine",
    "Viktor",
    "Clémence",
    "Ezra",
    "Solveig",
    "Aurel",
    "Perle",
]
SURNAMES = [
    "Vance",
    "Brissaud",
    "Kowal",
    "Delarue",
    "Ashworth",
    "Ferran",
    "Novak",
    "Maldini",
    "Thorne",
    "Ravel",
    "Okonkwo",
    "Sandoval",
    "Winter",
    "Lazare",
    "Corvin",
    "Bellamy",
    "Duchesne",
    "Halloran",
    "Sarkissian",
    "Volkov",
]

GAME_TITLES_FR = [
    "Les Cendres de Vaugirard",
    "La Ligne Brisée",
    "Sous la Cendre",
    "Le Dernier Tramway",
    "Chroniques de la Rive Morte",
    "Onze Nuits Blanches",
    "Le Pacte des Faubourgs",
    "Cartographie d'un Naufrage",
]
GAME_TITLES_EN = [
    "The Ashfall Compact",
    "Nine Doors Down",
    "Salt and Static",
    "The Quiet Ledger",
    "Hollow Tide",
    "Every Debt Comes Due",
    "The Grey Hour",
    "Cold Harbour Blues",
]

REPORT_TITLES_FR = [
    "La rencontre du pont",
    "Ce que la pluie n'a pas lavé",
    "Un marché de dupes",
    "La nuit où tout a basculé",
    "Retour au quartier bas",
    "Le prix du silence",
    "Personne ne dort ici",
    "L'entrepôt numéro sept",
]
REPORT_TITLES_EN = [
    "The bridge, at last",
    "What the rain left behind",
    "A crooked bargain",
    "The night it all turned",
    "Back to the low quarter",
    "The price of silence",
    "Nobody sleeps here",
    "Warehouse number seven",
]

NARRATION_FR = [
    "La brume s'accroche aux réverbères ; personne ne parle depuis dix minutes.",
    "Le quartier s'est vidé d'un coup, comme si la ville retenait son souffle.",
    "Derrière la porte, quelque chose racle le sol, lentement, sans se presser.",
]
NARRATION_EN = [
    "Fog clings to the streetlamps; nobody has spoken for ten minutes.",
    "The district emptied all at once, as if the city were holding its breath.",
    "Behind the door something drags across the floor, slow and unhurried.",
]
DESCRIPTION_FR = [
    "Une pièce basse de plafond, saturée de fumée froide et de vieux papiers.",
    "Le fleuve charrie des débris ; l'odeur de rouille prend à la gorge.",
]
DESCRIPTION_EN = [
    "A low-ceilinged room, thick with cold smoke and old paper.",
    "The river carries debris; the smell of rust catches in the throat.",
]
ACTION_FR = [
    "Je pousse la porte de l'épaule et je entre sans annoncer.",
    "Je fouille le tiroir, méthodiquement, sans quitter la fenêtre des yeux.",
]
ACTION_EN = [
    "I shoulder the door open and step through without announcing myself.",
    "I go through the drawer, methodically, never taking my eyes off the window.",
]
DISCUSSION_FR = [
    "« Tu savais. Depuis le début, tu savais, et tu n'as rien dit. »",
    "« On ne repart pas sans elle. Ce n'était pas le marché. »",
]
DISCUSSION_EN = [
    "“You knew. You knew all along, and you said nothing.”",
    "“We are not leaving without her. That was not the deal.”",
]
QUOTES_FR = [
    "On ne rachète pas une dette pareille avec des excuses.",
    "J'ai déjà été mort une fois. Ça ne s'améliore pas.",
]
QUOTES_EN = [
    "You do not settle a debt like that with an apology.",
    "I have been dead once already. It does not improve.",
]

MEDIA_ALT_FR = [
    "Une ruelle noyée sous la pluie, éclairée par une seule enseigne.",
    "Un entrepôt vide ; la lumière tombe en biais par une verrière brisée.",
    "Le fleuve, à l'aube, couvert d'une brume grasse.",
]
MEDIA_ALT_EN = [
    "A rain-drowned alley, lit by a single sign.",
    "An empty warehouse; light slants through a broken skylight.",
    "The river at dawn, under a greasy mist.",
]
# Deep, desaturated palette — legible behind white initials in both UI themes.
PALETTE: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = [
    ((28, 37, 65), (86, 63, 105)),
    ((59, 31, 43), (122, 70, 62)),
    ((22, 56, 58), (61, 110, 96)),
    ((45, 42, 61), (110, 92, 116)),
    ((17, 45, 78), (52, 105, 129)),
    ((66, 45, 26), (128, 92, 51)),
    ((40, 27, 54), (95, 60, 110)),
    ((30, 51, 41), (88, 117, 79)),
]

LANG_POOLS: dict[str, dict[str, list[str]]] = {
    "fr": {
        "game_titles": GAME_TITLES_FR,
        "report_titles": REPORT_TITLES_FR,
        "narration": NARRATION_FR,
        "description": DESCRIPTION_FR,
        "action": ACTION_FR,
        "discussion": DISCUSSION_FR,
        "quotes": QUOTES_FR,
        "media_alt": MEDIA_ALT_FR,
    },
    "en": {
        "game_titles": GAME_TITLES_EN,
        "report_titles": REPORT_TITLES_EN,
        "narration": NARRATION_EN,
        "description": DESCRIPTION_EN,
        "action": ACTION_EN,
        "discussion": DISCUSSION_EN,
        "quotes": QUOTES_EN,
        "media_alt": MEDIA_ALT_EN,
    },
}


def make_image(label: str, width: int, height: int, key: str) -> ContentFile[bytes]:
    """Procedural JPEG: vertical gradient + initials. No network, no binary assets.

    Deterministic in ``key`` — the same character always gets the same avatar,
    so screenshots and visual baselines stay stable across reseeds.
    """
    rng = random.Random(key)
    top, bottom = rng.choice(PALETTE)

    image = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        draw.line(
            [(0, y), (width, y)],
            fill=tuple(int(top[c] + (bottom[c] - top[c]) * ratio) for c in range(3)),
        )

    # A couple of translucent shapes to break the flatness.
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for _ in range(3):
        radius = rng.randint(width // 6, width // 2)
        cx, cy = rng.randint(0, width), rng.randint(0, height)
        odraw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(255, 255, 255, rng.randint(8, 22)),
        )
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    initials = "".join(word[0] for word in label.split()[:2]).upper() or "?"
    font = ImageFont.load_default(size=max(16, int(min(width, height) * 0.34)))
    draw = ImageDraw.Draw(image)
    box = draw.textbbox((0, 0), initials, font=font)
    draw.text(
        ((width - (box[2] - box[0])) / 2 - box[0], (height - (box[3] - box[1])) / 2 - box[1]),
        initials,
        font=font,
        fill=(255, 255, 255, 220),
    )

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=78, optimize=True)
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = "Populate the local (dev) database with a bilingual demo dataset."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--users", type=int, default=30)
        parser.add_argument("--games", type=int, default=20)
        parser.add_argument("--reports", type=int, default=400)
        parser.add_argument("--characters-per-game", type=int, default=10)
        parser.add_argument("--seed", type=int, default=20260714, help="RNG seed (reproducible).")
        parser.add_argument(
            "--flush", action="store_true", help="Delete demo data (demo_* users) and exit."
        )
        parser.add_argument("--force", action="store_true", help="Allow running with DEBUG=False.")
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Skip avatars/covers/rapport media (faster, no files written to MEDIA_ROOT).",
        )

    # --- entrypoint --------------------------------------------------------

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to seed with DEBUG=False. This command is for local dev only. "
                "Pass --force if you really mean it."
            )

        if options["flush"]:
            self._flush()
            return

        existing = User.objects.filter(username__startswith=DEMO_PREFIX).count()
        if existing:
            raise CommandError(
                f"{existing} demo users already exist — seeding again would collide on "
                f"username uniqueness. Run `seed_demo --flush` first."
            )

        self.rng = random.Random(options["seed"])
        self.images = not options["no_images"]
        self.image_count = 0
        self.used_slugs: set[str] = set(Character.objects.values_list("slug", flat=True))
        # Game has no `language` field (only Report does): the scene language is
        # a property of the campaign here, so we carry it alongside, keyed by id.
        self.game_lang: dict[str, str] = {}

        with transaction.atomic():
            users = self._create_users(options["users"])
            games = self._create_games(users, options["games"])
            characters = self._create_characters(games, users, options["characters_per_game"])
            self._create_reports(games, characters, options["reports"])
            self._create_quotes(characters)
            self._create_follows(users, characters, games)
            self._create_links(characters, users)

        demo_users = User.objects.filter(username__startswith=DEMO_PREFIX).count()
        self.stdout.write(self.style.SUCCESS("\nSeed complete."))
        self.stdout.write(f"  users       {demo_users}")
        self.stdout.write(f"  games       {Game.objects.count()}")
        self.stdout.write(f"  characters  {Character.objects.count()}")
        self.stdout.write(f"  reports     {Report.objects.count()}")
        self.stdout.write(f"  rapports    {Rapport.objects.count()}")
        self.stdout.write(f"  images      {self.image_count}")
        self.stdout.write(f"\nLogin with any demo user, password: {DEMO_PASSWORD}")

    def _flush(self) -> None:
        demo_users = User.objects.filter(username__startswith=DEMO_PREFIX)
        count = demo_users.count()
        if not count:
            self.stdout.write(self.style.WARNING("No demo data found."))
            return

        # Django cascades rows, never files: delete the media explicitly first,
        # or MEDIA_ROOT slowly fills up with orphans across reseeds.
        files = self._delete_media_files()

        with transaction.atomic():
            demo_users.delete()  # cascades to games, reports, characters, links
            for tag in Tag.objects.filter(name__in=TAGS):
                if not (tag.games.exists() or tag.reports.exists() or tag.characters.exists()):
                    tag.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Flushed {count} demo users, their content, and {files} media files."
            )
        )

    def _delete_media_files(self) -> int:
        deleted = 0
        targets: list[tuple[Any, tuple[str, ...]]] = [
            (
                User.objects.filter(username__startswith=DEMO_PREFIX),
                ("avatar", "default_character_background"),
            ),
            (Game.objects.filter(owner__username__startswith=DEMO_PREFIX), ("cover",)),
            (Character.objects.filter(creator__username__startswith=DEMO_PREFIX), ("avatar",)),
            (
                RapportMedia.objects.filter(
                    rapport__report__author__username__startswith=DEMO_PREFIX
                ),
                ("image",),
            ),
        ]
        for queryset, fields in targets:
            for obj in queryset.iterator(chunk_size=500):
                for field in fields:
                    file = getattr(obj, field)
                    if file:
                        file.delete(save=False)
                        deleted += 1
        return deleted

    # --- helpers -----------------------------------------------------------

    def _unique_character_name(self) -> str:
        """Names must be unique: Character.save() resolves slug collisions by
        catching IntegrityError, which would abort the surrounding transaction."""
        for _attempt in range(200):
            name = f"{self.rng.choice(GIVEN_NAMES)} {self.rng.choice(SURNAMES)}"
            if slugify(name) not in self.used_slugs:
                self.used_slugs.add(slugify(name))
                return name
        name = f"{self.rng.choice(GIVEN_NAMES)} {self.rng.choice(SURNAMES)} {len(self.used_slugs)}"
        self.used_slugs.add(slugify(name))
        return name

    def _tags(self, n: int) -> list[Tag]:
        return [Tag.objects.get_or_create(name=name)[0] for name in self.rng.sample(TAGS, k=n)]

    def _attach_image(
        self, obj: Any, field: str, label: str, size: tuple[int, int], key: str
    ) -> None:
        """Write a generated image into an ImageField (save=False: caller persists)."""
        if not self.images:
            return
        getattr(obj, field).save(
            f"{slugify(key) or 'demo'}.jpg",
            make_image(label, size[0], size[1], key),
            save=False,
        )
        self.image_count += 1

    # --- generators --------------------------------------------------------

    def _create_users(self, n: int) -> list[Any]:
        users = []
        for i in range(n):
            lang = "fr" if i % 2 == 0 else "en"
            user = User(
                username=f"{DEMO_PREFIX}{lang}_{i:03d}",
                email=f"{DEMO_PREFIX}{lang}_{i:03d}@example.test",
                display_name=f"{self.rng.choice(GIVEN_NAMES)} {self.rng.choice(SURNAMES)}",
                bio="Joueur de démo." if lang == "fr" else "Demo player.",
                content_language=lang,
                preferred_languages=["fr", "en"] if i % 3 == 0 else [lang],
                interface_language=lang if i % 4 else "",  # some inherit instance default
                show_unlabeled_content=i % 5 != 0,
            )
            user.set_password(DEMO_PASSWORD)
            # Some users deliberately have no avatar — the initials fallback in the
            # UI has to be exercised too.
            if i % 5 != 0:
                self._attach_image(
                    user, "avatar", user.display_name, (256, 256), f"avatar-{user.username}"
                )
            if i % 7 == 0:
                self._attach_image(
                    user,
                    "default_character_background",
                    user.display_name,
                    (1200, 400),
                    f"bg-{user.username}",
                )
            users.append(user)
        User.objects.bulk_create(users)
        self.stdout.write(f"users       {len(users)}")
        return users

    def _create_games(self, users: list[Any], n: int) -> list[Game]:
        games = []
        for i in range(n):
            lang = "fr" if i % 2 == 0 else "en"
            pool = LANG_POOLS[lang]
            title = f"{self.rng.choice(pool['game_titles'])} #{i + 1}"
            game = Game.objects.create(
                title=title,
                description=(
                    "Une campagne de démonstration." if lang == "fr" else "A demo campaign."
                ),
                game_system=self.rng.choice(SYSTEMS),
                owner=self.rng.choice(users),
                is_public=self.rng.random() > 0.15,
                started_at=timezone.now().date() - timedelta(days=self.rng.randint(30, 900)),
            )
            if i % 6 != 0:  # leave a few games without a cover
                self._attach_image(game, "cover", title, (1200, 400), f"cover-{game.id}")
                game.save(update_fields=["cover"])
            game.tags.set(self._tags(self.rng.randint(1, 3)))
            self.game_lang[str(game.id)] = lang
            games.append(game)
        self.stdout.write(f"games       {len(games)}")
        return games

    def _create_characters(
        self, games: list[Game], users: list[Any], per_game: int
    ) -> dict[str, list[Character]]:
        """Returns {game_id: [characters]}. Mix of owned PCs and unclaimed NPCs."""
        by_game: dict[str, list[Character]] = {}
        total = 0
        for game in games:
            lang = self.game_lang[str(game.id)]
            chars = []
            for i in range(per_game):
                is_pc = i < per_game // 3
                owner = self.rng.choice(users) if is_pc else None
                char = Character.objects.create(
                    name=self._unique_character_name(),
                    description=(
                        "Personnage de démonstration." if lang == "fr" else "Demo character."
                    ),
                    status=CharacterStatus.PC if is_pc else CharacterStatus.NPC,
                    owner=owner,
                    creator=owner or game.owner,
                    origin_game=game,
                )
                if i % 4 != 0:  # some characters keep the initials fallback
                    self._attach_image(char, "avatar", char.name, (256, 256), f"char-{char.id}")
                    char.save(update_fields=["avatar"])
                char.tags.set(self._tags(self.rng.randint(0, 2)))
                GameCast.objects.create(game=game, character=char, added_by=game.owner)
                chars.append(char)
            by_game[str(game.id)] = chars
            total += len(chars)
        self.stdout.write(f"characters  {total}")
        return by_game

    def _create_reports(
        self, games: list[Game], characters: dict[str, list[Character]], n: int
    ) -> None:
        per_game = max(1, n // len(games))
        rapport_count = 0
        report_count = 0

        for game in games:
            lang = self.game_lang[str(game.id)]
            pool = LANG_POOLS[lang]
            cast = characters[str(game.id)]
            session: date = game.started_at or timezone.now().date()

            for i in range(per_game):
                session = session + timedelta(days=self.rng.randint(7, 21))
                published = self.rng.random() > 0.15
                report = Report.objects.create(
                    title=f"{self.rng.choice(pool['report_titles'])} ({i + 1})",
                    content=self.rng.choice(pool["narration"]),
                    game=game,
                    author=game.owner,
                    language=lang,
                    visibility=self.rng.choice(
                        [ReportVisibility.PUBLIC] * 6
                        + [ReportVisibility.UNLISTED, ReportVisibility.FOLLOWERS]
                    ),
                    session_date=session,
                    content_warning=("Violence" if self.rng.random() > 0.9 else ""),
                )
                report.tags.set(self._tags(self.rng.randint(1, 3)))

                scene_cast = self.rng.sample(cast, k=min(len(cast), self.rng.randint(2, 4)))
                for idx, char in enumerate(scene_cast):
                    ReportCast.objects.create(
                        report=report,
                        character=char,
                        role=CastRole.MAIN if idx == 0 else CastRole.SUPPORTING,
                    )

                if published:
                    publish_report(report, game.owner)
                    if self.rng.random() > 0.4:  # some scenes crossed the wall
                        report.released_at = timezone.now() - timedelta(
                            days=self.rng.randint(1, 200)
                        )
                        report.save(update_fields=["released_at"])

                rapport_count += self._create_rapports(report, scene_cast, pool, published)
                report_count += 1

        self.stdout.write(f"reports     {report_count}")
        self.stdout.write(f"rapports    {rapport_count}")

    def _create_rapports(
        self,
        report: Report,
        cast: list[Character],
        pool: dict[str, list[str]],
        published: bool,
    ) -> int:
        """Build a thread respecting Rapport.clean(): narration takes no actor,
        action/discussion require one, description's actor is optional."""
        status = RapportStatus.PUBLISHED if published else RapportStatus.DRAFT
        previous: Rapport | None = None
        created = 0
        has_media = False

        opening = Rapport.objects.create(
            report=report,
            kind=RapportKind.NARRATION,
            actor=None,
            content=self.rng.choice(pool["narration"]),
            status=status,
        )
        RapportMarker.objects.create(rapport=opening, kind=MarkerKind.START, character=None)
        RapportMarker.objects.create(
            rapport=opening, kind=MarkerKind.CHARACTER_APPEARS, character=cast[0]
        )
        previous, created = opening, created + 1

        for _turn in range(self.rng.randint(3, 7)):
            kind = self.rng.choice(
                [RapportKind.ACTION, RapportKind.DISCUSSION, RapportKind.DESCRIPTION]
            )
            actor = self.rng.choice(cast) if kind != RapportKind.DESCRIPTION else None
            rapport = Rapport.objects.create(
                report=report,
                kind=kind,
                actor=actor,
                content=self.rng.choice(pool[kind]),
                status=status,
            )
            RapportLink.objects.create(rapport=rapport, parent_rapport=previous)
            # A medium *is* a mood: one image, on a description rapport only,
            # and at most one per scene (OneToOne enforces the rest).
            if kind == RapportKind.DESCRIPTION and not has_media and self.rng.random() < 0.55:
                media = RapportMedia(
                    rapport=rapport,
                    alt=self.rng.choice(pool["media_alt"]),
                )
                self._attach_image(media, "image", report.title, (1024, 576), f"media-{rapport.id}")
                if self.images:
                    media.save()
                    has_media = True
            previous, created = rapport, created + 1

        closing = Rapport.objects.create(
            report=report,
            kind=RapportKind.NARRATION,
            actor=None,
            content=self.rng.choice(pool["narration"]),
            status=status,
        )
        RapportLink.objects.create(rapport=closing, parent_rapport=previous)
        RapportMarker.objects.create(rapport=closing, kind=MarkerKind.END, character=None)
        return created + 1

    def _create_quotes(self, characters: dict[str, list[Character]]) -> None:
        count = 0
        for chars in characters.values():
            for char in chars:
                if self.rng.random() > 0.6:
                    continue
                lang = self.game_lang[str(char.origin_game_id)]
                Quote.objects.create(
                    content=self.rng.choice(LANG_POOLS[lang]["quotes"]),
                    context="",
                    character=char,
                    author=char.creator,
                    visibility=self.rng.choice(
                        [QuoteVisibility.PUBLIC] * 4 + [QuoteVisibility.PRIVATE]
                    ),
                )
                count += 1
        self.stdout.write(f"quotes      {count}")

    def _create_follows(
        self, users: list[Any], characters: dict[str, list[Character]], games: list[Game]
    ) -> None:
        char_ct = ContentType.objects.get_for_model(Character)
        game_ct = ContentType.objects.get_for_model(Game)
        all_chars = [c for chars in characters.values() for c in chars]
        count = 0

        for user in users:
            for char in self.rng.sample(all_chars, k=min(len(all_chars), 5)):
                _, made = Follow.objects.get_or_create(
                    follower=user, content_type=char_ct, object_id=char.id
                )
                count += int(made)
            for game in self.rng.sample(games, k=min(len(games), 3)):
                _, made = Follow.objects.get_or_create(
                    follower=user, content_type=game_ct, object_id=game.id
                )
                count += int(made)
        self.stdout.write(f"follows     {count}")

    def _create_links(self, characters: dict[str, list[Character]], users: list[Any]) -> None:
        """Drive the real workflow through LinkService — claims, adopts, forks,
        left in every state: pending, accepted, and accepted-then-published."""
        npcs = [
            c for chars in characters.values() for c in chars if c.status == CharacterStatus.NPC
        ]
        pcs = [
            c
            for chars in characters.values()
            for c in chars
            if c.status == CharacterStatus.PC and c.owner is not None
        ]
        self.rng.shuffle(npcs)
        stats = {"pending": 0, "accepted": 0, "published": 0}

        # One request per NPC at most: a second one would be QUEUED, not PENDING.
        for npc in npcs[: min(len(npcs), 40)]:
            pc = self.rng.choice(pcs)
            requester = pc.owner
            if requester is None or requester == npc.creator:
                continue  # never request against your own NPC

            link_type = self.rng.choice([LinkType.CLAIM, LinkType.ADOPT, LinkType.FORK])
            request = LinkService.create_request(
                requester=requester,
                target_character=npc,
                link_type=link_type,
                message="Ce PNJ était mon PJ depuis le début."
                if link_type == LinkType.CLAIM
                else "Je reprends ce personnage.",
                proposed_character=pc if link_type == LinkType.CLAIM else None,
            )

            if self.rng.random() < 0.4:  # leave it pending, to exercise the inbox
                stats["pending"] += 1
                continue

            link = LinkService.accept_request(request, response_message="D'accord, il est à toi.")
            stats["accepted"] += 1

            if self.rng.random() < 0.6:  # publish the shared sequence
                sequence: SharedSequence = link.shared_sequence
                sequence.content = "Nous nous étions déjà croisés, une nuit, sans le savoir."
                sequence.status = SharedSequenceStatus.PUBLISHED
                sequence.last_edited_by = requester
                sequence.last_edited_at = timezone.now()
                sequence.save()
                stats["published"] += 1

        self.stdout.write(
            f"links       {stats['accepted']} accepted "
            f"({stats['published']} with published sequence), {stats['pending']} pending"
        )
