<!-- migrated from docs – verify with /init -->
# Codebase Structure

```mermaid
---
title: Suddenly App Structure
---
flowchart TD
    subgraph "config/"
        S["settings: base / development / production"]
    end

    subgraph "suddenly/"
        subgraph "core/"
            C["BaseModel · Tag · InstanceSettings · utils · mixins · context_processors"]
            CA["admin panel /gmh/ (admin_views · admin_urls · decorators)"]
            CF["feed_views.py — home/instance/fediverse feeds"]
            CN["notification_views.py — list, badge, mark-all-read"]
            CNS["notification_signals.py — signals wiring notifications"]
            CO["onboarding_views.py — 3-step onboarding flow"]
            CCI["cache_invalidation.py — signal-based cache invalidation"]
            CSV["services.py — explorer queries, signal-based cache"]
            CMW["middleware.py — custom middleware"]
            CT["types.py — type aliases"]
            CV["version.py — version constant"]
            CM["Notification · NotificationType · NotificationPreference"]
            CMR["ContentReport · ReportCategory — moderation US-27"]
            CBS["UserBlock · UserMute — user safety US-33"]
            CDP["DonationPrompt · UserUsageStats — donation prompt"]
        end
        subgraph "users/"
            U["User (AbstractUser + AP fields + language prefs + is_admin)"]
            US["signals: AP actor init on signup (user_signed_up)"]
        end
        subgraph "games/"
            G["Game (tags M2M) · Report (tags M2M) · ReportCast"]
            GS["GameSystem — game system taxonomy (FK in Game)"]
            GR["Rapport — structured segment of Report (kind: DESCRIPTION/ACTION/DISCUSSION/NARRATION)"]
            GRL["RapportLink — parent link between Rapport segments (local FK or remote IRI)"]
            GRM["RapportMarker — structural marker (START/END/CHARACTER_APPEARS/CHARACTER_LEAVES/ORACLE)"]
        end
        subgraph "characters/"
            CH["Character (tags M2M) · Quote · CharacterAppearance"]
            CL["LinkRequest · CharacterLink · SharedSequence · Follow"]
            CS["LinkService (claim / adopt / fork)"]
        end
        subgraph "activitypub/"
            AP["views: WebFinger · NodeInfo · actors · inbox · outbox"]
            APS["serializers · signatures · activities · tasks · inbox handler"]
            APM["FederatedServer model"]
        end
    end

    subgraph "tests/"
        T["conftest · factories · test_api · test_models · test_users · test_services · test_activitypub · test_federation"]
    end

    S --> C
    S --> U
    S --> G
    S --> CH
    S --> AP

    C --> U
    C --> G
    C --> CH
    C --> AP

    U --> G
    U --> CH
    G --> CH
    CH --> AP
    U --> AP
    G --> AP

    AP --> PG[("PostgreSQL")]
    CH --> PG
    G --> PG
    U --> PG
```

## Critical Modules

| File | Role | Tests Required |
|------|------|----------------|
| `suddenly/characters/services.py` | Claim/Adopt/Fork logic | Yes |
| `suddenly/activitypub/handlers.py` | Incoming AP activity dispatch | Yes |
| `suddenly/activitypub/signatures.py` | HTTP Signatures verify/sign | Yes |
| `suddenly/activitypub/activities.py` | AP serialization | Yes |
| `suddenly/users/activitypub.py` | User federation | Yes |
| `suddenly/core/models.py` | BaseModel, ActivityPubMixin | Yes |
| `suddenly/core/services.py` | Explorer queries (cached) | Yes |
| `suddenly/core/notification_signals.py` | Notification wiring | Yes |
| `suddenly/core/feed_views.py` | Feed aggregation | Yes |

## App Import Relations

```
core/           ← imported by everything (BaseModel, ActivityPubMixin)
users/          ← imported by games, characters, activitypub
games/          ← imported by characters
characters/     ← imported by activitypub
activitypub/    ← imports users, games, characters (for serialization)
```

**Rule**: No circular imports. `core/` depends on nothing.

## URL / Template Areas

| Prefix | Templates |
|--------|-----------|
| `/feed/` | `templates/feed/` — home, instance, fediverse |
| `/notifications/` | `templates/notifications/` — list |
| `/onboarding/` | `templates/onboarding/` — step1, step2, step3 |
| `/gmh/` | `templates/gmh/` — admin panel pages |
| components | `templates/components/notification_item.html`, `feed_item.html`, etc. |

## Tooling Files

| File | Role |
|------|------|
| `Makefile` | Unified `make check` (lint + typecheck + test + coverage) |
| `.pre-commit-config.yaml` | Pre-commit hooks: ruff + mypy |
| `.github/workflows/ci.yml` | CI pipeline: ruff + mypy + pytest + coverage gate |
| `pyproject.toml` | Project config, pytest addopts with --cov-fail-under=80 |

## Scoped Rules

| Rule file | Scope |
|-----------|-------|
| `.claude/rules/01-standards/1-mermaid.md` | All Mermaid diagrams |
| `.claude/rules/01-standards/file-language-and-style.md` | All project files |
| `.claude/rules/04-tooling/git-main-protection.md` | All git operations on main |
| `.claude/rules/07-quality/dry-refactor.md` | All implementation |
| `.claude/rules/09-other/plan-before-implement.md` | All features/changes |
| `.claude/rules/09-other/challenge-plan.md` | Post-plan phase |
| `.claude/rules/09-other/double-review-after-implement.md` | Post-implement phase |
| `.claude/rules/09-other/harvest-trigger.md` | Task directory maintenance |

## Agents

| Agent | Role |
|-------|------|
| alexia | Autonomous end-to-end implementation |
| iris | Frontend specialist (Figma, UI, journeys) |
| kent | Test-driven development |
| martin | Build/test runner |
| claire | Clarity challenger |
