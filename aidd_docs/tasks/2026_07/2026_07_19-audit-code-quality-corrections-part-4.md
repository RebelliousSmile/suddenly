---
name: plan
description: Centralize the scene-author ownership check and the game create/edit form re-render into shared helpers.
objective: "The ~11 copied 'author != request.user → 403' checks route through one place, the misleading _get_authored_rapport helper actually enforces authorship, and game_create/game_edit share one form-render helper."
success_condition: "ruff check suddenly/games && mypy suddenly/ && pytest tests/games -q --no-cov -o addopts=''"
iteration: 0
created_at: "2026-07-19T00:05:20Z"
---

<!-- AI INSTRUCTIONS ONLY — do not output. -->

# Instruction: Factor ownership + form-handling (audit rows 3, 12)

## Feature

- **Summary**: The scene-author ownership check `X.author != request.user → Forbidden` is recopied ~11× in `front_views.py`, while the helper `_get_authored_rapport` is docstringed "authored" but does **not** filter by author (a correctness trap waiting to happen). Centralize the check into the helper (or a `@scene_author_required` decorator) and share the game create/edit form re-render. This part precedes the Part 6 split so the monolith is deduplicated before being moved.
- **Stack**: `Django 5.x (Python 3.12)`, `HTMX`, `pytest-django`
- **Branch name**: `refactor/audit-code-quality/ownership-forms`
- **Parent Plan**: `2026_07_19-audit-code-quality-corrections-master.md`
- **Sequence**: `4 of 6`
- Confidence: 9/10
- Time to implement: ~0.5-1 day

## Architecture projection

### Files to modify

- `suddenly/games/front_views.py` — make `_get_authored_rapport:1546` raise 403 when `author != request.user` (fix the docstring↔behavior gap), or add `@scene_author_required`; remove the ~11 copied checks at `:946,992,1052,1076,1155,1226,1324,1513,1572,1600,1670`; extract `_render_game_form(request, instance, errors)` shared by `game_create:422` and `game_edit:823` (parsing `is_public` + error re-render, `457-461 ≈ 857-859`).

### Files to create

- none (helpers stay local to `front_views.py`; Part 6 relocates them).

### Files to delete

- none.

## Applicable rules

| Tool | Name | Path | Why it applies |
| ---- | ---- | ---- | -------------- |
| claude | htmx-patterns | `.claude/rules/03-frameworks-and-libraries/03-htmx-patterns.md` | `@require_POST` on state-mutating views; partial re-render on error |
| claude | dry-refactor | `.claude/rules/07-quality/dry-refactor.md` | Rule of Three on the ownership check + form render |
| claude | data-pivots-django-orm | `.claude/rules/07-quality/data-pivots-django-orm.md` | Object-level ownership scoping |
| claude | file-language-and-style | `.claude/rules/01-standards/file-language-and-style.md` | Plan human-consumed |

## Risk register

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| `_get_authored_rapport` used somewhere that must NOT 403 | new 403 regressions | grep every caller; if any legitimately needs the unfiltered fetch, keep a separate `_get_rapport` and use the authored one only where the 403 was inline |
| Centralizing the check changes the 403 body/redirect | HTMX flows expecting a specific response break | preserve the exact current 403 response shape (status + partial) in the helper/decorator |
| `_render_game_form` diverges subtly between create/edit contexts | wrong error context rendered | parametrize instance + errors; snapshot the two rendered contexts equal to today via tests |

## Implementation phases

### Phase 1: Centralize the scene-author check

> One authorship gate; the misleading helper now actually enforces it.

#### Tasks

1. Audit all callers of `_get_authored_rapport` and the ~11 inline checks; decide helper-raises-403 vs `@scene_author_required` decorator.
2. Implement the single gate; remove the inline duplicates; preserve the exact current 403 response.
3. Tests: author passes, non-author gets 403 on each previously-inline site (parametrized).

#### Acceptance criteria

- [ ] Grep shows no inline `author != request.user` check left in `front_views.py`.
- [ ] `_get_authored_rapport` (or the decorator) enforces authorship; docstring matches behavior.
- [ ] Non-author → 403 on every affected endpoint (tests).

### Phase 2: Shared game form render

> `game_create` and `game_edit` share one form-render helper.

#### Tasks

1. Extract `_render_game_form(request, instance, errors)` covering `is_public` parsing + error context.
2. Route both `game_create` and `game_edit` through it.
3. Tests: create-with-errors and edit-with-errors re-render identically to today.

#### Acceptance criteria

- [ ] `game_create`/`game_edit` error paths share one helper (grep).
- [ ] `pytest tests/games` green; `mypy` clean.

## Amendments

<!-- 🤖 entries during implementation -->

## Log

<!-- APPEND ONLY -->

## Validation flow demonstration

1. As a non-author, hit each scene-mutating endpoint → 403, identical body to before.
2. As the author → actions succeed unchanged.
3. Submit an invalid game create form, then an invalid game edit form → identical error re-render both paths.
