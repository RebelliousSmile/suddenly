---
name: plan
description: Deduplicate templates — extract claim/adopt/fork actions and avatar-or-placeholder partials, consolidate the quote-card templates.
objective: "Claim/Adopt/Fork actions and the avatar-or-placeholder motif each live in one included partial reused everywhere, and a single canonical quote-card template remains."
success_condition: "node design/lint/lint-files.mjs templates/characters/partials/_claim_adopt_fork_actions.html templates/games/partials/_actor_avatar.html && python manage.py check && python manage.py makemessages -l fr -l en --no-wrap --ignore=venv --ignore=node_modules --ignore=staticfiles && python manage.py compilemessages -l fr -l en && pytest tests/characters tests/games tests/core/test_i18n.py -q --no-cov -o addopts=''"
iteration: 0
created_at: "2026-07-19T00:05:20Z"
---

<!-- AI INSTRUCTIONS ONLY — do not output. -->

# Instruction: Deduplicate templates (audit rows 8, 9, 10)

## Feature

- **Summary**: Extract the Claim/Adopt/Fork action trio (duplicated on 4 sites) into a parameterized partial, generalize the existing `_actor_avatar.html` avatar-or-placeholder partial across the ~9 templates that re-inline it, and remove the dead `components/quote_card.html` duplicate so a single canonical quote card remains. Behavior/markup preserved per surface.
- **Stack**: `Django templates`, `HTMX`, `UnoCSS (design contract)`, `pytest-django`
- **Branch name**: `refactor/audit-code-quality/template-dedup`
- **Parent Plan**: `2026_07_19-audit-code-quality-corrections-master.md`
- **Sequence**: `5 of 6`
- Confidence: 9/10
- Time to implement: ~0.5-1 day

## Architecture projection

### Files to modify

- `templates/characters/_character_card.html:44-63`, `templates/characters/_list_results.html:85-104`, `templates/feed/_promo_card.html:38-45`, `templates/characters/_link_suggestions.html:51-63` — replace the inline Claim/Adopt/Fork trio with `{% include %}` of the new partial (params `slug`, `variant`).
- `templates/characters/character_form.html`, `detail.html`, `_character_card.html`, `_list_results.html`, `templates/components/npc_highlight.html`, `templates/feed/_promo_card.html`, `templates/quotes/_quote_card.html` — replace inline avatar-or-placeholder with the generalized avatar partial.
- `templates/characters/_quote_card.html`, `templates/quotes/_quote_card.html` — keep the canonical quote card + the HTMX front_views fragment; drop the dead one.

### Files to create

- `templates/characters/partials/_claim_adopt_fork_actions.html` — parameterized Claim/Adopt/Fork actions (`slug`, `variant`).
- Possibly `templates/games/partials/_avatar.html` — if generalizing `_actor_avatar.html` warrants a rename for cross-domain use (else reuse `_actor_avatar.html` as-is).

### Files to delete

- `templates/components/quote_card.html` — dead (`href="#"`), contradicts the "canonical" note (also covered by Part 2's dead-template purge; delete in whichever part runs first, skip in the other).

## Applicable rules

| Tool | Name | Path | Why it applies |
| ---- | ---- | ---- | -------------- |
| claude | dry-refactor | `.claude/rules/07-quality/dry-refactor.md` | Rule of Three on the action trio + avatar motif |
| claude | enforce | `.claude/rules/08-design/01-enforce.md` | Contract utilities/tokens only, Lucide icons, no raw hex |
| claude | display-vocabulary | `.claude/rules/08-domain/08-display-vocabulary.md` | UI wording consistency in extracted markup |
| claude | file-language-and-style | `.claude/rules/01-standards/file-language-and-style.md` | Plan human-consumed |

## Risk register

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Per-surface variants differ (classes, size) | visual regression after extraction | expose a `variant` param; diff each surface's rendered markup before/after |
| Avatar partial assumes a field the caller lacks | template render error | make the partial tolerant (guarded `if avatar`), pass a normalized `entity`/`url` param |
| Deleting the dead quote card twice (Part 2 + Part 5) | merge conflict / double-delete error | delete in one part only; the other grep-confirms it is already gone |
| Design lint fails on new partials | contract violation | run `design/lint/lint-files.mjs` on every new/edited template |

## Implementation phases

### Phase 1: Claim/Adopt/Fork actions partial

> One partial renders the action trio on all 4 sites.

#### Tasks

1. Create `templates/characters/partials/_claim_adopt_fork_actions.html` (`slug`, `variant`).
2. Replace the 4 inline blocks with `{% include %}`, passing the per-site `variant`.
3. Verify each surface renders unchanged (badge/buttons, HTMX targets).

#### Acceptance criteria

- [ ] Grep shows the action trio markup in exactly one partial.
- [ ] Each of the 4 surfaces renders the same actions as before; design lint 0.

### Phase 2: Avatar partial generalization + quote-card consolidation

> One avatar-or-placeholder partial everywhere; one canonical quote card.

#### Tasks

1. Generalize `_actor_avatar.html` (guarded, normalized param); include it in the ~9 templates.
2. Delete the dead `components/quote_card.html` (unless Part 2 already did); keep canonical + HTMX fragment.
3. Design lint + template render tests.

#### Acceptance criteria

- [ ] Avatar-or-placeholder markup inlined in ≤1 place (the partial); all callers include it.
- [ ] Only the canonical quote card + its HTMX fragment remain.
- [ ] `design/lint/lint-files.mjs` on touched templates exits 0; `manage.py check` green.

## Amendments

<!-- 🤖 entries during implementation -->

## Log

<!-- APPEND ONLY -->

## Validation flow demonstration

1. Load each of the 4 claim/adopt/fork surfaces → identical actions, HTMX still targets the right endpoints.
2. Load the ~9 avatar surfaces → avatar or placeholder renders identically.
3. Grep `components/quote_card.html` → gone; quote pages still render via the canonical card.
