# Code Review — US-01 Créer mon compte

- **Branch**: `feat/us01-create-account`
- **Base**: `main`
- **Date**: 2026-03-06
- **Files changed**: 9 (+522 / -27)

## Summary

Implementation of user registration with ActivityPub actor initialization, factory-boy test tooling, and allauth templates.

## Findings

### Critical (blocks merge)

_None._

### Major

_None._

### Minor

| # | File | Line(s) | Rule | Finding |
|---|------|---------|------|---------|
| 1 | `suddenly/users/signals.py` | 24 | `03-django-services` | Signal handler contains business logic (keypair generation + AP URL construction). Rule says "services contain all business logic". However, this is a single-purpose signal wiring allauth to model fields — extracting a service would add indirection without benefit at this stage. **Accept as-is.** |
| 2 | `suddenly/users/signals.py` | 20-23 | `07-agentic-type-safety` | `request: object` and `**kwargs: object` are loose types. `request` should be `HttpRequest` and `kwargs` could use `Any`. Minor — signal handlers have variable signatures from allauth. **Low priority.** |
| 3 | `tests/test_users.py` | 212-268 | `05-pytest` | `TestSignupAPInitialization` uses `@pytest.mark.django_db` at class level, while other test classes in the same file rely on fixtures with `db` dependency. Inconsistent but both are correct. **Cosmetic.** |
| 4 | `templates/account/signup.html` | 31 | — | `value="{{ form.username.value|default:'' }}"` — Django's `default` filter on `None` renders `None` as string in some edge cases. Safer: `value="{{ form.username.value|default_if_none:'' }}"`. **Low priority.** |

### Positive

- Factories follow factory-boy best practices (`Sequence`, `LazyAttribute`, `SubFactory`, `PostGenerationMethodCall`)
- Signal uses `update_fields` to avoid full model save — good practice
- `user_signed_up` signal preferred over `post_save` — fires once, only for real signups
- Guard clause for remote users is defensive and correct
- Test coverage: signup success, duplicate username, duplicate email, weak password, remote user, factory smoke
- Templates consistent with existing project style (Tailwind classes, `card card-body`, `btn-primary`)
- `_celery_eager` autouse fixture prevents broker connection in tests

## Rules Compliance

| Rule | Status |
|------|--------|
| `03-django-models` | OK — No model changes |
| `03-django-services` | Minor (#1) — accepted |
| `03-django-views` | OK — No view changes |
| `05-pytest` | OK — factories, assertions, one behavior per test |
| `06-agentic-tests` | OK — no network, meaningful assertions |
| `07-agentic-type-safety` | Minor (#2) — signal signature |
| `08-activitypub` | OK — RSA 2048, PKCS8/SPKI, AP URL format |
| PEP 8 + type hints | OK |
| Commit conventions | OK — `test()`, `feat()`, `test()` |

## Verdict

**APPROVE** — No blocking issues. 4 minor findings, all acceptable for merge.
