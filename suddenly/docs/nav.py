from pathlib import Path
from typing import TypedDict

from django.conf import settings

BASE: Path = settings.BASE_DIR


class NavEntry(TypedDict):
    slug: str
    label: str
    path: Path


class NavSection(TypedDict):
    section: str
    slug: str
    entries: list[NavEntry]


NAV: list[NavSection] = [
    {
        "section": "Documentation",
        "slug": "doc",
        "entries": [
            {"slug": "index", "label": "Introduction", "path": BASE / "docs/index.md"},
            {
                "slug": "design-system",
                "label": "Design System",
                "path": BASE / "docs/design-system.md",
            },
            {
                "slug": "translations",
                "label": "Traductions",
                "path": BASE / "docs/translations.md",
            },
            {
                "slug": "import-export",
                "label": "Import / Export",
                "path": BASE / "docs/import-export.md",
            },
        ],
    },
    {
        "section": "Projet",
        "slug": "projet",
        "entries": [
            {
                "slug": "brief",
                "label": "Brief",
                "path": BASE / "aidd_docs/memory/project_brief.md",
            },
            {
                "slug": "architecture",
                "label": "Architecture",
                "path": BASE / "aidd_docs/memory/architecture.md",
            },
            {
                "slug": "codebase",
                "label": "Codebase Map",
                "path": BASE / "aidd_docs/memory/codebase_map.md",
            },
            {
                "slug": "deployment",
                "label": "Déploiement",
                "path": BASE / "aidd_docs/memory/deployment.md",
            },
        ],
    },
    {
        "section": "Standards",
        "slug": "standards",
        "entries": [
            {
                "slug": "coding",
                "label": "Coding Guidelines",
                "path": BASE / "aidd_docs/memory/coding_assertions.md",
            },
            {
                "slug": "testing",
                "label": "Tests",
                "path": BASE / "aidd_docs/memory/testing.md",
            },
            {
                "slug": "vcs",
                "label": "Git / VCS",
                "path": BASE / "aidd_docs/memory/vcs.md",
            },
        ],
    },
    {
        "section": "Référence",
        "slug": "reference",
        "entries": [
            {
                "slug": "api",
                "label": "API",
                "path": BASE / "aidd_docs/memory/internal/api_docs.md",
            },
            {
                "slug": "database",
                "label": "Base de données",
                "path": BASE / "aidd_docs/memory/internal/database.md",
            },
            {
                "slug": "bookwyrm",
                "label": "BookWyrm (référence)",
                "path": BASE / "aidd_docs/memory/external/bookwyrm-architecture.md",
            },
            {
                "slug": "claim-fork",
                "label": "Claim / Adopt / Fork",
                "path": BASE / "aidd_docs/memory/external/claim-adopt-fork.md",
            },
            {
                "slug": "alwaysdata",
                "label": "Alwaysdata",
                "path": BASE / "aidd_docs/memory/external/alwaysdata-deployment.md",
            },
            {
                "slug": "vps",
                "label": "VPS",
                "path": BASE / "aidd_docs/memory/external/vps-deployment.md",
            },
            {
                "slug": "docker",
                "label": "Docker",
                "path": BASE / "aidd_docs/memory/external/docker-deployment.md",
            },
            {
                "slug": "pr-template",
                "label": "Pull Request",
                "path": BASE / "aidd_docs/memory/external/pr-template.md",
            },
            {
                "slug": "task-workflow",
                "label": "Task Workflow",
                "path": BASE / "aidd_docs/memory/external/task-workflow.md",
            },
        ],
    },
    {
        "section": "Wireframes",
        "slug": "wireframes",
        "entries": [
            {
                "slug": "overview",
                "label": "Index",
                "path": BASE / "aidd_docs/wireframes/README.md",
            },
            {
                "slug": "ux-patterns",
                "label": "UX Patterns",
                "path": BASE / "aidd_docs/wireframes/00-ux-patterns.md",
            },
            {
                "slug": "layout",
                "label": "Layout",
                "path": BASE / "aidd_docs/wireframes/01-layout.md",
            },
            {
                "slug": "home",
                "label": "Accueil",
                "path": BASE / "aidd_docs/wireframes/02-home.md",
            },
            {
                "slug": "auth",
                "label": "Auth",
                "path": BASE / "aidd_docs/wireframes/03-auth.md",
            },
            {
                "slug": "profile",
                "label": "Profil",
                "path": BASE / "aidd_docs/wireframes/04-profile.md",
            },
            {
                "slug": "games",
                "label": "Parties",
                "path": BASE / "aidd_docs/wireframes/05-games.md",
            },
            {
                "slug": "reports",
                "label": "CRs",
                "path": BASE / "aidd_docs/wireframes/06-reports.md",
            },
            {
                "slug": "characters",
                "label": "Personnages",
                "path": BASE / "aidd_docs/wireframes/07-characters.md",
            },
            {
                "slug": "links",
                "label": "Liens",
                "path": BASE / "aidd_docs/wireframes/09-links.md",
            },
            {
                "slug": "feed",
                "label": "Feed",
                "path": BASE / "aidd_docs/wireframes/10-feed.md",
            },
            {
                "slug": "notifications",
                "label": "Notifications",
                "path": BASE / "aidd_docs/wireframes/11-notifications.md",
            },
            {
                "slug": "gm-dashboard",
                "label": "Dashboard GM",
                "path": BASE / "aidd_docs/wireframes/12-gm-dashboard.md",
            },
            {
                "slug": "admin",
                "label": "Admin",
                "path": BASE / "aidd_docs/wireframes/13-admin.md",
            },
            {
                "slug": "federation",
                "label": "Fédération",
                "path": BASE / "aidd_docs/wireframes/14-federation.md",
            },
            {
                "slug": "settings",
                "label": "Paramètres",
                "path": BASE / "aidd_docs/wireframes/15-settings.md",
            },
            {
                "slug": "misc",
                "label": "Divers",
                "path": BASE / "aidd_docs/wireframes/16-misc.md",
            },
            {
                "slug": "instance-about",
                "label": "À propos instance",
                "path": BASE / "aidd_docs/wireframes/17-instance-about.md",
            },
            {
                "slug": "report-links",
                "label": "CR — Liens perso",
                "path": BASE / "aidd_docs/wireframes/18-report-character-links.md",
            },
            {
                "slug": "component-map",
                "label": "Component Map",
                "path": BASE / "aidd_docs/wireframes/COMPONENT_MAP.md",
            },
            {
                "slug": "style-guide",
                "label": "Style Guide",
                "path": BASE / "aidd_docs/wireframes/STYLE_GUIDE.md",
            },
            {
                "slug": "fediverse-audit",
                "label": "Audit Fediverse",
                "path": BASE / "aidd_docs/wireframes/PERSONA_FEDIVERSE_AUDIT.md",
            },
        ],
    },
]


def resolve(section_slug: str, entry_slug: str) -> Path | None:
    for section in NAV:
        if section["slug"] == section_slug:
            for entry in section["entries"]:
                if entry["slug"] == entry_slug:
                    return entry["path"]
    return None
