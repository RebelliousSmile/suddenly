---
name: plan
description: Purge dead code and dead "component" templates after the master Decision gate resolves the wire-vs-remove items.
objective: "Every confirmed-dead symbol and orphan template from the audit is removed (or explicitly wired), the fake-authority components/ dead cards are gone, and no phantom HTMX endpoint remains referenced."
success_condition: "ruff check . && mypy suddenly/ && pytest -q --no-cov -o addopts='' && python manage.py makemigrations --check --dry-run"
iteration: 0
created_at: "2026-07-19T00:05:20Z"
---

<!-- AI INSTRUCTIONS ONLY — do not output. BLOCKED on the master Decision gate. -->

# Instruction: Purge dead code + dead templates (audit rows 7, 10, 14, 15, 16-23)

## Feature

- **Summary**: Delete confirmed-dead factories, tasks, properties, enum values, and orphan templates; and for the decision-gated items, apply the user's wire-vs-remove choice. Removes the false authority the `components/` folder lends to dead cards (one of which wires non-existent claim/adopt/fork HTMX endpoints).
- **Precondition**: master Decision gate resolved for `EXPIRED`/`is_expired`, `is_suddenly_instance`, `send_accept_follow`, `build_owned_pc_queryset`, doc↔code drift.
- **Stack**: `Django 5.x (Python 3.12)`, `pytest-django`, `ruff`, `mypy`
- **Branch name**: `refactor/audit-code-quality/dead-code-purge`
- **Parent Plan**: `2026_07_19-audit-code-quality-corrections-master.md`
- **Sequence**: `2 of 6`
- Confidence: 9/10 (pending gate answers)
- Time to implement: ~0.5 day

## Architecture projection

### Files to modify

- `suddenly/activitypub/serializers.py:408,413,453` — delete `create_update_activity`/`create_delete_activity`/`create_offer_activity` (0 callers).
- `suddenly/activitypub/activities.py:40` — delete `build_undo_activity` (0 usage).
- `suddenly/celery.py:23` — delete `debug_task`.
- `suddenly/characters/models.py:281,349` — per gate: remove `is_expired` + `LinkRequestStatus.EXPIRED` (needs a migration) OR implement the cleanup task that assigns them.
- `suddenly/activitypub/models.py:72` — per gate: remove `is_suddenly_instance` + its test OR wire Offer filtering.
- `suddenly/activitypub/tasks.py:138` — per gate: remove `send_accept_follow` + its test OR recable inbox onto it (recommend remove).
- `suddenly/characters/services.py:604` + `suddenly/games/services.py:138,173,239` — per gate: wire `build_owned_pc_queryset` into the composer, replacing the 5 re-inlined `owner=user, status=PC` filters (recommended) OR delete it.
- `.claude/rules/08-domain/08-activitypub.md`, `.claude/rules/08-domain/08-characters.md` — align normative docs with the code once the gate lands. (Both files are **tracked and not gitignored** — verified with `git ls-files` / `git check-ignore`; the audit's "gitignored, edit is local" claim was wrong. Committed edits persist normally.)

### Files to delete

- `templates/components/character_card.html`, `game_card.html`, `quote_card.html`, `report_card.html` — 4 dead components (416 l), `character_card.html:107` wires phantom claim/adopt/fork endpoints.
- `templates/feed/_report_card.html` — dead, 0 references.

### Files to create

- Possibly one migration under `suddenly/characters/migrations/` if `EXPIRED` is removed.

## Applicable rules

| Tool | Name | Path | Why it applies |
| ---- | ---- | ---- | -------------- |
| claude | normative-vs-archive | `.claude/rules/01-standards/normative-vs-archive.md` | Align rules to code; remove stale normative claims |
| claude | dry-refactor | `.claude/rules/07-quality/dry-refactor.md` | Reuse `build_owned_pc_queryset` instead of re-inlining |
| claude | file-language-and-style | `.claude/rules/01-standards/file-language-and-style.md` | Plan human-consumed |

## Risk register

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| A "dead" symbol is referenced dynamically (template `{% include %}`, getattr, admin) | runtime break at delete | grep code + templates + tests + admin before each delete; `manage.py check` + full test run |
| Removing `EXPIRED` enum value without migration | model/migration state diverges | run `makemigrations --check`; ship the migration in this part |
| Wrong doc paths carried from the audit (files live under `08-domain/`, not `.claude/rules/` root) | edit lands nowhere / no-op | use the verified paths `.claude/rules/08-domain/08-{activitypub,characters}.md`; both are tracked, so a normal commit persists the fix |
| Wiring `build_owned_pc_queryset` changes composer output | behavior change beyond "dead code" | wiring is behavior-neutral only if the helper's queryset equals the 5 inlined filters — assert with the existing `test_post_composer_services.py` |

## Implementation phases

### Phase 1: Unconditional dead-code deletions

> Remove the symbols with zero callers and the orphan templates.

#### Tasks

1. Delete the 3 `create_*_activity` factories, `build_undo_activity`, `debug_task`.
2. Delete the 4 `components/*_card.html` and `feed/_report_card.html`; grep-confirm no `{% include %}`/`render` references remain.
3. `manage.py check` + full test run.

#### Acceptance criteria

- [ ] Grep shows zero references to each deleted symbol/template.
- [ ] `ruff`/`mypy`/`pytest` green; `makemigrations --check` clean.

### Phase 2: Decision-gated items

> Apply the user's wire-vs-remove choice per gated symbol.

#### Tasks

1. `build_owned_pc_queryset`: wire into `games/services.py` (replace the 5 filters) or delete — per gate.
2. `send_accept_follow`, `is_suddenly_instance`, `is_expired`/`EXPIRED`: remove (+ tests, + migration if enum) or implement — per gate.
3. Align `08-activitypub.md`/`08-characters.md` to the resulting code.

#### Acceptance criteria

- [ ] Each gated symbol is either reused in prod code or fully removed (symbol + test + doc mention).
- [ ] If `EXPIRED` removed: migration present, `makemigrations --check` clean.
- [ ] Normative docs no longer describe unimplemented behavior.

## Amendments

<!-- 🤖 entries during implementation -->

## Log

<!-- APPEND ONLY -->

## Validation flow demonstration

1. `grep` each removed symbol across `suddenly/`, `templates/`, `tests/` — zero hits.
2. Composer still lists "mes PJs" identically (if `build_owned_pc_queryset` wired).
3. `python manage.py migrate` applies cleanly on a fresh DB; `makemigrations --check` reports no missing migration.
