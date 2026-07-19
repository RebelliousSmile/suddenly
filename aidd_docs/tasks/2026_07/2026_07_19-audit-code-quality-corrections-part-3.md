---
name: plan
description: Inbox dispatch observability (logger.exception) + narrow two over-broad swallowed exceptions. Behavior-preserving only — no retry/dead-letter.
objective: "A failing inbox handler is logged with its stack (instead of a stackless logger.error) while still returning 202; over-broad except clauses in URL validation and signature verification are narrowed to the exceptions actually raised. No control-flow or durability change."
success_condition: "ruff check suddenly/activitypub suddenly/games && mypy suddenly/ && pytest tests/test_activitypub.py tests/test_federation.py -q --no-cov -o addopts=''"
iteration: 0
created_at: "2026-07-19T00:05:20Z"
---

<!-- AI INSTRUCTIONS ONLY — do not output. Behavior-preserving only. -->

# Instruction: Inbox dispatch observability + narrow swallowed excepts (audit rows 13, 27 + signatures.py:213)

## Feature

- **Summary**: Today a handler bug inside the inbox dispatch `try/except Exception` logs without a stack (`logger.error`) and returns 202 regardless — the error is invisible. This part fixes only the **observability** (stack in the log) and tightens two over-broad exception filters that collapse real bugs into "false"/"ignored". **All three changes are behavior-preserving**: same HTTP status, same control flow, same return values.
- **Out of scope (spun out)**: the **retry/dead-letter durability** the audit hinted at is a net-new capability, not a refactor — it lives in a separate feature plan outside this master (per the master's Scope boundary). It would reuse `ProcessedActivity` (models.py:110), not a new table. Do **not** add a model, migration, or retry classification here.
- **Stack**: `Django 5.x (Python 3.12)`, `cryptography`, `pytest-django`
- **Branch name**: `refactor/audit-code-quality/inbox-hardening`
- **Parent Plan**: `2026_07_19-audit-code-quality-corrections-master.md`
- **Sequence**: `3 of 6`
- Confidence: 9/10
- Time to implement: ~0.5 day

## Architecture projection

### Files to modify

- `suddenly/activitypub/inbox.py` (≈:197 — the `logger.error(f"Error handling {activity_type}: {e}")` inside the dispatch `except Exception`) — change `logger.error` → `logger.exception` so the caught handler failure logs with its stack. **Keep the `try/except Exception` and the 202 return exactly as they are** — observability only, no control-flow change.
- `suddenly/games/front_views.py` (≈:1242 — the `except Exception` immediately after `validate_url = URLValidator()`) — narrow to `except ValidationError` (that is all it raises).
- `suddenly/activitypub/signatures.py:213` — narrow `except Exception: return False` in `_verify_with_key` to `except (InvalidSignature, ValueError, TypeError, binascii.Error)` so crypto failure returns False but real bugs surface.

### Files to create

- none.

## Applicable rules

| Tool | Name | Path | Why it applies |
| ---- | ---- | ---- | -------------- |
| claude | ap-pivots | `.claude/rules/07-quality/ap-pivots-django-activitypub.md` | Inbox dispatch reliability; exception handling |
| claude | file-language-and-style | `.claude/rules/01-standards/file-language-and-style.md` | Plan human-consumed |

## Risk register

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| `logger.exception` outside an `except` block raises | log call itself errors | the call stays inside the existing `except Exception` block — it already has an active exception context |
| Narrowing signature except lets an unexpected exception escape | 500 on a malformed inbound signature | include the full crypto exception set (`InvalidSignature, ValueError, TypeError, binascii.Error`); add a malformed-signature test asserting False, not 500 |
| Narrowing `front_views.py:1234` misses an exception `URLValidator` actually raises | uncaught 500 on invalid URL | `URLValidator` raises only `ValidationError`; the malformed-URL test asserts the same user-facing path as before |

## Implementation phases

### Phase 1: Dispatch observability

> The handler failure is visible (stack) — same 202, same control flow.

#### Tasks

1. `logger.error` → `logger.exception` at the dispatch `except Exception` in `inbox.py` (grep `Error handling {activity_type}`), inside the existing block; leave the `try/except` structure and the 202 return untouched.
2. Test: a handler raising inside dispatch → `logger.exception` called (stack captured) **and** the endpoint still returns 202 (behavior unchanged).

#### Acceptance criteria

- [ ] The caught handler failure logs with a stack; HTTP status and control flow are identical to before (test asserts 202 still returned).
- [ ] No new model, migration, or retry logic introduced (`makemigrations --check` clean).

### Phase 2: Narrow swallowed exceptions

> Two over-broad `except` clauses only catch what they should.

#### Tasks

1. `front_views.py` `except Exception` after `URLValidator()` (≈:1242) → `except ValidationError`.
2. `signatures.py:213` → `except (InvalidSignature, ValueError, TypeError, binascii.Error)`; add `import binascii` if absent.
3. Test: malformed signature → verification returns False (no 500); invalid URL → handled path unchanged.

#### Acceptance criteria

- [ ] No `except Exception` remains at `front_views.py:1234` or `signatures.py:213`.
- [ ] Malformed-signature and invalid-URL tests green; `mypy` clean.

## Amendments

<!-- 🤖 entries during implementation -->

## Log

<!-- APPEND ONLY -->

## Validation flow demonstration

1. Post an inbox activity that makes a handler raise → server logs a full stack (`logger.exception`), still returns 202 — identical outward behavior, now diagnosable.
2. Send a malformed HTTP signature → verification returns False, not a 500.
3. Submit an invalid URL to the view at `front_views.py:1234` → same user-facing behavior as before.
