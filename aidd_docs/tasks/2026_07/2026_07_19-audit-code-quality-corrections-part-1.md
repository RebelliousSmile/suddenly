---
name: plan
description: Single-source the ActivityPub federation core — canonical actor→model mapping, sign-and-deliver, remote user/game get-or-create, Accept/Reject symmetry.
objective: "The federation core has one canonical implementation each for actor_type→Model mapping, signed delivery, remote-user get_or_create, remote-game synthesis, and Accept/Reject link responses — reused everywhere, with zero behavior change."
success_condition: "ruff check suddenly/activitypub suddenly/characters suddenly/core && mypy suddenly/ && pytest tests/test_activitypub.py tests/test_federation.py tests/characters -q --no-cov -o addopts=''"
iteration: 0
created_at: "2026-07-19T00:05:20Z"
---

<!-- AI INSTRUCTIONS ONLY — do not output. Behavior-preserving refactor only. -->

# Instruction: Single-source the federation core (audit rows 1, 2, 4, 5, 6 + 24, 26)

## Feature

- **Summary**: Extract the federation duplication into canonical helpers and reuse them across inbox/tasks/views. Highest-leverage, most-dispersed debt in the audit; the risk being paid down is silent drift on federated data. No functional change — same wire behavior, same signatures.
- **Stack**: `Django 5.x (Python 3.12)`, `Celery`, `httpx`, `pytest-django`, `mypy (strict)`, `ruff`
- **Branch name**: `refactor/audit-code-quality/federation-core`
- **Parent Plan**: `2026_07_19-audit-code-quality-corrections-master.md`
- **Sequence**: `1 of 6`
- Confidence: 9/10
- Time to implement: ~1 day

## Architecture projection

### Files to modify

- `suddenly/core/utils.py` — add canonical `actor_model_for(type_key)` + `content_type_for_actor(type_key)` with normalized casing; absorb the `get_local_actor` mapping.
- `suddenly/activitypub/_http.py` — host the single `get_or_create_remote_user` (keep `update_or_create` variant); add `sign_and_deliver(activity, inbox_url, *, signer)`.
- `suddenly/activitypub/inbox.py` — replace hand-written actor→model maps (`:235,301,1070`), the divergent `get_or_create_remote_user` (`:1010`), the 3× `Game.get_or_create` remote synthesis (`:361,501,849`) via new `_get_or_create_remote_game`, and the `handle_accept/handle_reject` guard sequence (`:947-957,979-989`).
- `suddenly/activitypub/tasks.py` — reuse `actor_model_for` (`:101,124,146`); replace the outbound `get_actor_signing_keys(...)+deliver_activity.delay(...)` pair with `sign_and_deliver` at the **live** sites `:127,250,281,325` + inbox `:270` (7 sites total). **Excluded**: `:164` lives inside `send_accept_follow`, PRE-DECIDED for deletion in Part 2 — do not refactor it here. `:363,396` (inside `send_accept_activity`/`send_reject_activity`) are **not** touched by this bullet either: they are subsumed by the phase-3 `_send_link_response` collapse below, which calls `sign_and_deliver` once. Also drop the divergent `get_or_create_remote_user` (`:490`); collapse `send_accept_activity`/`send_reject_activity` (`:337-369,372-402`) into `_send_link_response(link_request_id, build_activity)`.
- `suddenly/characters/follow_views.py:39`, `suddenly/characters/views.py:360`, `suddenly/core/serializers.py:398` — reuse `actor_model_for`/`content_type_for_actor` instead of local maps.
- `suddenly/characters/services.py:172-180,283-291` — extract `LinkService._create_fork_character(request)` (fork char create copied in `accept_request` + `reconstruct_remote_accept`).

### Files to create

- none (helpers land in existing `core/utils.py`, `activitypub/_http.py`).

### Files to delete

- none.

## Applicable rules

| Tool | Name | Path | Why it applies |
| ---- | ---- | ---- | -------------- |
| claude | dry-refactor | `.claude/rules/07-quality/dry-refactor.md` | Rule of Three — the core constraint (9 + 8 duplicated sites) |
| claude | django-services | `.claude/rules/03-frameworks-and-libraries/03-django-services.md` | Service-layer extraction; atomic multi-step mutations |
| claude | ap-pivots | `.claude/rules/07-quality/ap-pivots-django-activitypub.md` | SSRF-safe fetch reuse; `on_commit` before `.delay()` preserved |
| claude | file-language-and-style | `.claude/rules/01-standards/file-language-and-style.md` | Plan is human-consumed |

## Risk register

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Key-casing drift (`"user"` vs `"User"`) hidden by the two conventions | wrong model resolved for a federated actor | `actor_model_for` normalizes casing once; add a unit test per known type key + unknown → explicit error |
| The two `get_or_create_remote_user` impls differ (username slicing, create vs update_or_create) | behavior change on remote user ingest | pick the `update_or_create` variant as canonical; add a regression test asserting idempotent re-ingest + username truncation |
| Accept/Reject collapse changes DEC-038 correlation (`origin_offer_id`) | broken cross-instance link responses | `_send_link_response` keeps the exact queryset + guard + correlation; assert via existing federation tests |
| `sign_and_deliver` alters headers/signature | delivery rejected by peers | helper is a pure move of `get_actor_signing_keys + deliver_activity.delay`; no header change; verify with a spy test |

## Implementation phases

### Phase 1: Canonical actor→model mapping

> One helper resolves actor type keys; all 9 sites reuse it.

#### Tasks

1. Add `actor_model_for(type_key: str) -> type[Model]` and `content_type_for_actor(type_key: str) -> ContentType` to `core/utils.py`, casing-normalized, raising on unknown keys.
2. Replace the local maps at inbox `:235,301,1070`, tasks `:101,124,146`, `follow_views.py:39`, `views.py:360`, `core/serializers.py:398`; fold `get_local_actor` onto the helper.
3. Unit-test each supported key + unknown-key error.

#### Acceptance criteria

- [x] Grep shows no inline `{"user": ..., "character": ...}` actor map outside `core/utils.py`.
- [x] `mypy suddenly/` exits 0; tests green.

### Phase 2: sign_and_deliver + single remote-user source

> Signed delivery and remote-user ingest exist once.

#### Tasks

1. Add `sign_and_deliver(activity, inbox_url, *, signer)` to `_http.py`; replace the outbound pairs at the 4 live task sites (`:127,250,281,325`) + inbox `:270` = 7 sites. Skip `:164` (doomed `send_accept_follow`) and `:363,396` (owned by phase-3 collapse).
2. Make `_http.get_or_create_remote_user` the single source; import it from `tasks.py` (drop `:490` copy).
3. Regression tests: idempotent remote-user re-ingest; delivery spy asserts unchanged headers/signature.

#### Acceptance criteria

- [ ] One definition each of `sign_and_deliver` and `get_or_create_remote_user` (grep).
- [ ] Federation tests green.

### Phase 3: Remote-game synthesis + Accept/Reject + fork-char helpers

> Remote-game get_or_create, link-response tasks, and fork-char create each exist once.

#### Tasks

1. Extract `_get_or_create_remote_game(domain, owner)` in `inbox.py`; replace `:361,501,849`.
2. Collapse `send_accept_activity`/`send_reject_activity` into `_send_link_response(link_request_id, build_activity)` preserving DEC-038 correlation.
3. Extract `_resolve_authorized_link_request(activity)` for `handle_accept`/`handle_reject` guard sequence.
4. Extract `LinkService._create_fork_character(request)`; reuse in `accept_request` + `reconstruct_remote_accept`.

#### Acceptance criteria

- [ ] Remote-game synthesis appears once; Accept/Reject share one builder; fork-char create appears once.
- [ ] `pytest tests/test_activitypub.py tests/test_federation.py tests/characters` green.

## Amendments

<!-- 🤖 entries during implementation -->

- 🤖 Phase 1: `get_local_actor` was folded into `core/utils.py` as specified, but its call sites were **not** individually rewired to lazy/local imports — `inbox.py` keeps a single top-level `from suddenly.core.utils import get_local_actor` import and its former local definition (bottom of file) was deleted outright. Behavior-identical (same lookup logic, `remote=False` filter preserved), just a lower-friction import strategy than per-site lazy imports.
- 🤖 Phase 1: `follow_views.py::follow_toggle` resolves the model via `actor_model_for(target_type)` but then computes `ContentType.objects.get_for_model(model_cls)` directly rather than calling `content_type_for_actor(target_type)` a second time — avoids a redundant type-key resolution for a value already in hand. Still single-sourced (the underlying key→model map exists nowhere else).
- 🤖 Phase 1: `inbox.py::handle_undo`'s original guard was `if model_class: ...` (silent no-op on an unrecognized type, since nothing followed the block). Replaced with `try: content_type_for_actor(...) except ValueError: return` — behaviorally identical (function simply ends either way), but now raises-then-catches instead of falsy-checking, matching the new helper's contract.
- 🤖 Phase 1: mypy strict flagged `ActorModel.objects` / `Model.objects` as invalid on the `type[models.Model]` return of `actor_model_for` (django-stubs does not expose `.objects` on the abstract base). Fixed by using `._default_manager` at the two call sites in `tasks.py` (`broadcast_activity`, `send_accept_follow`) — same pattern already used inside `get_local_actor` itself. No behavior change: `_default_manager` and `.objects` resolve to the same manager for these concrete models.
- 🤖 Phase 1: added `tests/core/test_utils.py` (not explicitly named as a new file in "Files to create," but required by task 3 "Unit-test each supported key + unknown-key error"). Covers `actor_model_for`/`content_type_for_actor` casing-insensitivity + unknown-key `ValueError`, plus `get_local_actor` (local/remote filtering, missing row, unknown type) since it was folded into the same helper group this phase.

## Log

<!-- APPEND ONLY -->

- 2026-07-19: Phase 1 complete. `ruff check suddenly/activitypub suddenly/characters suddenly/core` clean; `mypy suddenly/` clean (113 files, 0 errors); `pytest tests/test_activitypub.py tests/test_federation.py tests/characters tests/core/test_utils.py -q --no-cov -o addopts=''` → 187 passed, 3 skipped (baseline was 169 passed/3 skipped; +18 from the new test file, 0 regressions). Grep confirms the only remaining `"user": User` / `"game": Game` style map lives in `core/utils.py:74-75` (the canonical one). Phases 2 and 3 not started this pass.

## Validation flow demonstration

1. Run the federation test suite before/after — identical pass set, no wire-format diff.
2. Trigger a cross-instance Claim → Accept round trip (existing DEC-038 e2e) — link resolves as before.
3. Ingest a remote actor twice — one row, no duplicate, username truncated identically.
