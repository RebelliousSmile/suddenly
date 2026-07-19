---
name: master_plan
description: Parent plan orchestrating the corrections of audit 2026_07_code-quality (DRY, dead code, refactoring) across 6 sequenced child plans.
objective: "Absorb the duplication + dead-code debt reported by aidd_docs/tasks/audits/2026_07_code-quality.md — single-source the federation core, purge dead symbols/templates (after product decisions), harden inbox dispatch, factor ownership/form handling, deduplicate templates, and split the front_views monolith — with no behavior regression."
success_condition: "ruff check . && mypy suddenly/ && pytest -q (make check exits 0)"
iteration: 0
created_at: "2026-07-19T00:05:20Z"
---

<!-- AI INSTRUCTIONS ONLY — do not output. Sequential execution: child N+1 blocked until child N validated. -->

# Master Plan: Audit code-quality corrections (2026-07-19)

## Overview

- **Goal**: Pay down the duplication + dead-code debt from `aidd_docs/tasks/audits/2026_07_code-quality.md` (0 critical, 15 warning, 12 minor) without changing runtime behavior.
- **Risk Score**: 6/10 (5+ modules touched +3, major refactoring +2, enum-removal no-op migration +1). The `LinkRequestStatus.EXPIRED` removal generates a Django `AlterField` migration because the field uses `choices=LinkRequestStatus.choices`, but it is **no-op at SQL level** (choices are not a DB constraint; zero rows hold `'expired'`) — low risk, not +3.
- **Branch**: `refactor/audit-code-quality/`
- **Source audit**: `aidd_docs/tasks/audits/2026_07_code-quality.md`
- **Constraint**: read-only audit → every change here must be behavior-preserving and green under `make check`. Parts that **add, move, or edit** user-facing strings (Part 5's partial extraction) must additionally run the i18n gate (makemessages/compilemessages + `tests/core/test_i18n.py`), since a `{% trans %}` string moving into an included partial must still be catalogued. Pure deletions of dead templates (Part 2) do not need it — removing an unused msgid cannot fail i18n. Rule of Three governs every extraction.
- **Scope boundary**: this master is refactor-only. Any net-new capability surfaced by the audit (e.g. inbox retry/dead-letter durability) is **out of scope** and spun out to a separate feature plan — see Part 3.
- **Line numbers are indicative**: every `file:line` in the child plans is grep-anchored to a named symbol, not a hard offset. The working tree is dirty (`inbox.py`, `characters/services.py`, `games/services.py` modified) and each part branches from a later `main`, so offsets drift — the implementer locates each site by its symbol/pattern, and acceptance criteria assert via grep, never by line.

## Integration strategy

- Each part ships on its own branch `refactor/audit-code-quality/<name>` cut **from an up-to-date `main`**.
- A part is **merged to `main` once green** (its `success_condition` + review) **before** the next part branches. Sequential parts therefore always build on the previous part's merged helpers — no stacked-branch drift.
- Hard cross-part dependencies made explicit: Part 6 requires Part 4 **merged** (it relocates Part 4's ownership/form helpers); Parts 2 and 4 both edit `front_views.py`/`models.py`, so their linear order (2 before 4) avoids the conflict.
- "Final `make check` on the integrated branch" = `main` after Part 6 merges.

## Decision gate (BLOCKS parts 2 and 4 — user input required)

The audit flags symbols/rules that are either dead OR unfinished features. Each needs a product decision **wire it** vs **remove it** before Part 2/4 touches it:

| Item | Audit row | Options | Recommendation |
| ---- | --------- | ------- | -------------- |
| `LinkRequestStatus.EXPIRED` + `Character.is_expired` + cleanup task | 20, 21 | implement Celery cleanup that assigns EXPIRED / remove enum value + property + doc | decide; removal needs a migration |
| `is_suddenly_instance` (models.py:72) | 19 | wire Offer filtering / delete method + test | decide (real federation gap, not noise) |
| `send_accept_follow` task (tasks.py:138) | 18 | recable inbox onto it / delete task + its test | **PRE-DECIDED: delete** (inbox already inlines the path). Consequence: **Part 1 must NOT refactor `tasks.py:164`** into `sign_and_deliver` — that site lives inside the doomed `send_accept_follow` and is removed by Part 2. Of the 7 original outbound pair sites (`:127,164,250,281,325,363,396`), Part 1 drops `:164`, replaces four directly in phase 2 (`:127,250,281,325`) + inbox `:270`, and folds the last two (`:363,396`) into `_send_link_response` in phase 3 — **6 pre-refactor occurrences addressed, not 8**. If the user overrides to "recable", Part 1 re-includes `:164`. |
| `build_owned_pc_queryset` (services.py:604) | 22 | wire into composer / delete | **wire** — staged composer changes reference the "mes PJs" pool; row 25 shows the filter re-inlined 5× |
| Doc↔code drift (`08-activitypub.md`, `08-characters.md`) | 15 | align rules to code (EXPIRED cleanup, is_suddenly_instance, FORKED) | align after the above decisions land |

## Child Plans

| #   | Plan | File | Status | Validated |
| --- | ---- | ---- | ------ | --------- |
| 1 | Single-source the federation core | `./2026_07_19-audit-code-quality-corrections-part-1.md` | done | [x] |
| 2 | Purge dead code + dead templates | `./2026_07_19-audit-code-quality-corrections-part-2.md` | done | [x] |
| 3 | Inbox dispatch observability + narrow swallowed excepts (behavior-preserving only; retry/dead-letter spun out) | `./2026_07_19-audit-code-quality-corrections-part-3.md` | done | [x] |
| 4 | Factor ownership + form handling | `./2026_07_19-audit-code-quality-corrections-part-4.md` | pending | [ ] |
| 5 | Deduplicate templates | `./2026_07_19-audit-code-quality-corrections-part-5.md` | blocked | [ ] |
| 6 | Split `games/front_views.py` monolith | `./2026_07_19-audit-code-quality-corrections-part-6.md` | blocked | [ ] |

<!-- RULE: Plan N+1 blocked until Plan N checkbox checked. Parts are independent-by-phase (each ships green on its own). -->

## Sequencing rationale

1. **Part 1 first** — highest-leverage, most-dispersed debt (9 + 8 sites), silent-drift risk on federated data. Creates the canonical helpers others reuse.
2. **Part 2** — quick wins, but blocked on the Decision gate for the "wire vs remove" items.
3. **Part 3** — observability-only fix (`logger.exception` + two `except` narrowings), fully behavior-preserving and isolated. The **retry/dead-letter durability** the audit hinted at is a net-new feature, extracted to a separate plan outside this master (it would reuse `ProcessedActivity`, models.py:110, not a new table).
4. **Part 4** — ownership check centralization corrects a misleading helper (`_get_authored_rapport` is docstringed "authored" but does not filter by author).
5. **Part 5** — template deduplication (partials extraction).
6. **Part 6 last** — the `front_views.py` split (1746 l → 4 modules) is done only after the duplication debt inside it is absorbed by Part 4, so the split moves clean code.

## Validation Protocol

1. Complete each child plan; run its `success_condition`.
2. [ ] Checkpoint per child: `make check` green + `git diff` behavior-preserving review.
3. Unblock the next child.
4. [ ] Final: full `make check` (ruff + mypy + pytest + coverage ≥ 80%) on the integrated branch; grep proves each extracted helper has a single definition.

## Estimations

- **Confidence**: 9/10
- **Duration**: ~3-4 days across the 6 parts (Part 1 M, Part 6 L, rest S-M).
