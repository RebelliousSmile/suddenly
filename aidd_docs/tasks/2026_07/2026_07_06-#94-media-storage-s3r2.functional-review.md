# Functional review — #94 media-storage-s3r2

Confidence: 92%

## Score table

| Title | Files | Confidence Score |
|-------|-------|-------------------|
| Part 1 — Conditional S3/R2 storage config | `config/settings/production.py`, `pyproject.toml` | 0 |
| Part 2 — Federated URL DRY helper | `suddenly/activitypub/url_utils.py`, `activities.py`, `serializers.py` | 0 |
| Part 3 — Operational documentation | `.env.example` | 2 |
| Part 4 — Tests | `tests/core/test_production_storage.py`, `tests/activitypub/test_url_utils.py` | 1 |

Legend: 0 = no fix needed · 1 = minor improvements suggested · 2 = major issues found · 3 = critical problems.

Scope note: this review verifies plan-conformance only (Plans 1–4 + master). Phase 0 (external R2 bucket/keys/public-access) and the master Validation Protocol step 8 (live Railway integration test) are out of code scope and not judged here.

---

## Part 1 — Conditional S3/R2 storage config — Score 0

Fully implemented, matches the plan precisely.

- Phase 1: `django-storages[s3]>=1.14` added to `pyproject.toml` dependencies (`>=1.14` is the correct floor — OPTIONS-based storage config requires django-storages 1.14+).
- Phase 2: `production.py:69-94` reads `AWS_STORAGE_BUCKET_NAME` via `os.environ.get`, and on presence **rebinds** `STORAGES` to a new dict via `{**STORAGES, "default": {...}}` — never a `STORAGES["default"] = ...` mutation. This is the exact anti-mutation requirement from part-1 Phase 2 and master finding line 54. Confirmed by tests (see Part 4).
- `OPTIONS` matches the spec item-for-item: `bucket_name`, `endpoint_url` (via `AWS_S3_ENDPOINT_URL`), `region_name` (default `"auto"`), `access_key`, `secret_key`, `querystring_auth=False`, `file_overwrite=False`, and **no** `default_acl` key.
- The mandatory explanatory comment about the shared-reference hazard is present verbatim (`production.py:70-74`).
- `manage.py check` behavior with/without the env var is covered by the reload tests, which pass.

Minor observations (not defects): `access_key`/`secret_key` use `os.environ[...]` (fail-fast KeyError if the bucket is set but keys are absent) while `endpoint_url` uses `.get()`. The plan did not prescribe required-vs-optional per key, so this is an acceptable, arguably correct, fail-fast choice.

## Part 2 — Federated URL DRY helper — Score 0

Fully implemented, matches the plan.

- New file `suddenly/activitypub/url_utils.py` defines `absolute_media_url(file_field) -> str`: returns `.url` unchanged when it starts with `http://`/`https://`, else prefixes `f"https://{settings.DOMAIN}{url}"`. Exactly the part-2 Phase 1 signature and branch logic.
- All three call sites replaced with the helper: `activities.py:61` (was `f"https://{settings.DOMAIN}{obj.avatar.url}"`), `serializers.py:54` (User), `serializers.py:125` (Character). No manual `https://{domain}{.url}` concatenation for avatars remains — Rule of Three satisfied, no residual duplication.
- Verified the `from django.conf import settings` imports in both edited files are still needed (many other `settings.DOMAIN` / `settings.AP_BASE_URL` uses remain), so no dead import was introduced by the refactor.

## Part 3 — Operational documentation — Score 2 (major)

The plan's investigation (master line 51, part-3 summary) assumed `.env.example` **did not exist** and had to be **created** from scratch. It does exist, and the implementer correctly appended rather than overwriting. That course-correction is fine — but because Phase 1 was framed as "create the file with all vars", **Phase 1 was effectively skipped** and **Phase 2 was only partially done**. The pre-existing file is docker-compose-oriented, not aligned with what `production.py` actually reads.

### 3a — Part-3 Phase 1 not performed; validation-flow step 1 fails

Part-3 Phase 1 requires documenting every var `production.py` reads, and validation-flow step 1 demands **zero mismatches** between `.env.example` names and `os.environ[...]` calls in `production.py`. That is not met:

- **`DATABASE_URL` — required by `production.py:35` (`os.environ["DATABASE_URL"]`), absent from `.env.example`.** The file instead documents `POSTGRES_PASSWORD` / `POSTGRES_USER` / `POSTGRES_DB`, which `production.py` never reads. An operator following only `.env.example` (part-3 validation step 2's stated goal) cannot deploy — the app fails fast with `KeyError: 'DATABASE_URL'`.
- `ALLOWED_HOSTS` (`production.py:18`) — undocumented.
- `DJANGO_LOG_LEVEL` (`production.py:127`) — undocumented.
- `RAILWAY_PUBLIC_DOMAIN` (`production.py:21`) — undocumented (part-3 Phase 1 item 3 explicitly asked for it, informational).

Fix: add a `DATABASE_URL=postgres://user:pass@host:5432/db` entry to the REQUIRED block (and reconcile it with the existing `POSTGRES_*` docker vars — either document both and explain which deployment target uses which, or note that docker-compose composes `DATABASE_URL` from the `POSTGRES_*` vars). Add `ALLOWED_HOSTS`, `DJANGO_LOG_LEVEL`, and an informational `RAILWAY_PUBLIC_DOMAIN` note. Then re-run part-3 validation step 1 (diff names against `production.py`).

### 3b — Part-3 Phase 2 comment items 3, 4, 5 missing; item 1 comment incomplete

The appended S3 block (`.env.example:52-59`) covers Phase 2 item 1 (the five `AWS_*` vars present) and item 2 (the "leave empty → filesystem fallback" comment). The remaining prescribed comments are absent:

- **Item 3 missing**: no note that `AWS_QUERYSTRING_AUTH=False` and `AWS_S3_FILE_OVERWRITE=False` are hardcoded in settings (not env-configurable) and why (non-expiring public avatar URLs for federation; no silent cross-user overwrite).
- **Item 4 missing**: no warning that these env vars alone are **not sufficient** — the bucket must also have public read access configured at the infrastructure level (R2 Public Development URL or custom domain; master Phase 0), otherwise avatar URLs 403 despite correct settings. This is the highest-value operational warning in the plan and it is not present.
- **Item 5 missing**: no note that avatars set before this fix are not auto-migrated and users must re-upload once.
- **Item 1 comment incomplete**: `AWS_S3_REGION_NAME=auto` is listed with no comment explaining `"auto"` is R2-specific and real AWS S3 must set an explicit region.

Fix: extend the appended block with the four missing comment groups, wording per part-3 Phase 2 items 1, 3, 4, 5.

## Part 4 — Tests — Score 1 (minor)

Both test files exist and all 6 tests pass (`pytest tests/core/test_production_storage.py tests/activitypub/test_url_utils.py` → 6 passed; the coverage-gate failure is an artifact of running a 2-file subset, not a test failure).

Coverage of the planned cases is complete and faithful:

- `test_production_storage.py`: filesystem fallback when bucket unset (part-4 Phase 1 test 2), `production.STORAGES is base.STORAGES` no-rebind identity guard (test 2), S3 backend + `OPTIONS` assertions incl. `querystring_auth is False`, `file_overwrite is False`, `"default_acl" not in options` (test 3), and `base.STORAGES` unmutated after override (test 4 — the regression guard for the mutation risk). The module-reload approach matches the part-4 Phase 1 preamble exactly.
- `test_url_utils.py`: passthrough for absolute URL (Phase 2 test 1) and domain-prefix for relative URL (Phase 2 test 2).

Minor gap (why 1, not 0):

- Part-4 Phase 2 **test 3** — "existing ActivityPub serializer tests (User/Character) still pass unchanged after the part-2 refactor" — is a regression guard the plan calls for. No evidence it was run/confirmed as part of this change, and no new assertion ties the helper back to real serializer output. Recommend running the full existing `tests/activitypub/` suite and recording it green (part-4 validation step 2), or adding one serializer-level assertion that `icon.url` is a single well-formed URL. Note the two new URL-helper tests use a hand-rolled `_FakeFileField` rather than a factory-boy factory; acceptable for a pure-function unit test, but slightly off the `05-pytest.md` "use factories" convention.

---

## Overall

- Code deliverables (Parts 1, 2) are correct and match the accepted spec with no divergence — including the non-obvious anti-mutation rebind and the double-domain federation-URL fix, both verified by passing tests.
- The documentation deliverable (Part 3) is the weak point: Phase 1 was skipped due to the "file doesn't exist" planning assumption being wrong, leaving the required `DATABASE_URL` undocumented and the plan's own zero-mismatch validation criterion unmet; three of the five Phase 2 operational comments (including the critical public-read-access 403 warning) are absent.
- Tests (Part 4) are solid; only the cross-check regression guard (Phase 2 test 3) is unaddressed.

No code changes were made and no fix sub-agents were spawned, per instructions. A human gate follows before any fixes.
