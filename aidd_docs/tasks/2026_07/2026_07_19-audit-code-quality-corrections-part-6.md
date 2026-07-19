---
name: plan
description: Split the games/front_views.py monolith (1746 l) into domain modules and extract the POST→validate→re-render scaffolding.
objective: "games/front_views.py is decomposed into game/report/rapport/composer view modules with no URL or behavior change, and the repeated POST→validate→re-render scaffolding is extracted."
success_condition: "ruff check suddenly/games && mypy suddenly/ && pytest tests/games -q --no-cov -o addopts='' && python manage.py check"
iteration: 0
created_at: "2026-07-19T00:05:20Z"
---

<!-- AI INSTRUCTIONS ONLY — do not output. Runs LAST — after Part 4 deduplicates the monolith. -->

# Instruction: Split games/front_views.py monolith (audit row 11)

## Feature

- **Summary**: `games/front_views.py` is 1746 l with 71 `request.POST.get` and 9 functions > 68 l. Split by domain into `game_views.py` / `report_views.py` / `rapport_views.py` / `composer_views.py`, and extract the recurring POST→validate→re-render scaffolding. Pure structural move — URLs, view names, and behavior unchanged. Sequenced last so the ownership/form duplication (Part 4) is already gone before the code is relocated.
- **Stack**: `Django 5.x (Python 3.12)`, `HTMX`, `pytest-django`, `mypy`, `ruff`
- **Branch name**: `refactor/audit-code-quality/front-views-split`
- **Parent Plan**: `2026_07_19-audit-code-quality-corrections-master.md`
- **Sequence**: `6 of 6`
- Confidence: 8/10 (large mechanical move; import fan-out is the risk)
- Time to implement: ~1 day

## Architecture projection

### Files to modify

- `suddenly/games/front_urls.py` — update view imports to the new modules; keep every URL name identical.
- Any module importing `from suddenly.games.front_views import …` — re-point imports (or keep `front_views.py` as a thin re-export shim to avoid a big import churn — decide at phase 1).
- `tests/games/**` — update imports if they reference `front_views` symbols directly.

### Files to create

- `suddenly/games/game_views.py` — game CRUD views (`game_create`, `game_edit`, …).
- `suddenly/games/report_views.py` — report/scene views (`report_compose`, `report_edit`, `report_detail`, …).
- `suddenly/games/rapport_views.py` — rapport-segment views.
- `suddenly/games/composer_views.py` — composer views.
- `suddenly/games/_view_helpers.py` — extracted POST→validate→re-render scaffolding (+ the Part 4 form/ownership helpers relocated here).

### Files to delete

- `suddenly/games/front_views.py` — after the split (or keep as a re-export shim; decide at phase 1).

## Applicable rules

| Tool | Name | Path | Why it applies |
| ---- | ---- | ---- | -------------- |
| claude | htmx-patterns | `.claude/rules/03-frameworks-and-libraries/03-htmx-patterns.md` | Front views return HTML partials; `@require_POST` ordering preserved |
| claude | dry-refactor | `.claude/rules/07-quality/dry-refactor.md` | Extract the POST scaffolding once |
| claude | ide-mapping | `.claude/rules/04-tooling/ide-mapping.md` | snake_case module names, project structure |
| claude | file-language-and-style | `.claude/rules/01-standards/file-language-and-style.md` | Plan human-consumed |

## Risk register

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Import fan-out — external modules import `front_views` symbols | ImportError across the app | grep every `front_views` import first; keep a thin re-export shim if churn is large |
| Circular imports between the new view modules | app fails to load | keep shared helpers in `_view_helpers.py`; views import helpers, never each other |
| A view silently loses a decorator during the move | auth/CSRF/`@require_POST` regression | move decorators with the function verbatim; assert decorators present via a test or grep |
| URL name drift | `NoReverseMatch` in templates | `front_urls.py` names unchanged; `manage.py check` + full template-reversing test run |

## Implementation phases

### Phase 1: Decide shim vs hard-cut; scaffold modules

> Choose import strategy and create empty domain modules + helper module.

#### Tasks

1. Grep all importers of `games.front_views`; decide re-export shim vs hard re-point.
2. Create the 4 view modules + `_view_helpers.py`; relocate the Part 4 ownership/form helpers here.
3. Extract the POST→validate→re-render scaffolding into `_view_helpers.py`.

#### Acceptance criteria

- [ ] New modules exist; `_view_helpers.py` holds the shared scaffolding + relocated helpers.
- [ ] Import strategy decided and recorded in the Log.

### Phase 2: Move views by domain

> Relocate each view group; wire URLs; keep names/behavior.

#### Tasks

1. Move game/report/rapport/composer views into their modules with decorators verbatim.
2. Update `front_urls.py` imports; keep all URL names.
3. Remove/replace `front_views.py` (delete or shim per phase-1 decision).

#### Acceptance criteria

- [ ] `pytest tests/games` green; `manage.py check` clean; no `NoReverseMatch`.
- [ ] `mypy suddenly/` + `ruff` clean; each view module < ~500 l.
- [ ] Every URL name resolves to the same view behavior as before.

## Amendments

<!-- 🤖 entries during implementation -->

## Log

<!-- APPEND ONLY -->

## Validation flow demonstration

1. Full `pytest tests/games` before/after — identical pass set.
2. Exercise game create/edit, scene compose/edit, rapport actions, composer in the browser — all work unchanged.
3. `manage.py check` + a URL-reversing smoke over `front_urls.py` names → all resolve.
