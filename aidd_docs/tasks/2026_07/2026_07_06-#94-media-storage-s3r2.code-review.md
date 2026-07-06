# Code Review — Media Storage S3/R2 (#94, #98)

Confidence: 88%

Scope reviewed: `config/settings/production.py`, `suddenly/activitypub/url_utils.py` (new),
`suddenly/activitypub/activities.py`, `suddenly/activitypub/serializers.py`, `.env.example`,
`pyproject.toml`, `tests/core/test_production_storage.py` (new),
`tests/activitypub/test_url_utils.py` (new). Verified against `.claude/rules/` (all subdirs),
`config/settings/base.py`, and a codebase-wide sweep for inline media-URL construction.

Overall: this is a careful, well-reasoned change. The single highest-risk item (mutating the
shared `base.STORAGES` dict) is correctly avoided **and** provably covered by a test. Findings
below are minor/hygiene; none are blocking.

## Score table

| # | Issue | File(s) | Score |
|---|-------|---------|-------|
| 1 | `STORAGES` rebinding correctness (the flagged bug class) | `config/settings/production.py` | 0 (verified correct) |
| 2 | DRY sweep — no remaining inline media-URL duplication | `suddenly/**` | 0 (verified clean) |
| 3 | Unused `settings` fixture param + imprecise `object` typing in passthrough test | `tests/activitypub/test_url_utils.py` | 1 |
| 4 | `absolute_media_url(file_field: Any)` weak type hint (mypy blind) | `suddenly/activitypub/url_utils.py` | 1 |
| 5 | `importlib.reload(production)` leaves module globally mutated (test isolation) | `tests/core/test_production_storage.py` | 1 |
| 6 | Pre-existing hardcoded `mediaType: "image/jpeg"` now more exposed by arbitrary S3 uploads | `suddenly/activitypub/serializers.py` | 1 (pre-existing, out of diff scope) |
| 7 | `querystring_auth=False` requires a public bucket — deployment coupling | `config/settings/production.py` | 0–1 (documented; informational) |
| 8 | factory-boy pytest rule vs `_FakeFileField` stub | `tests/activitypub/test_url_utils.py` | 0 (considered, acceptable) |

(0 = no fix needed, 1 = minor improvement, 2 = major issue, 3 = critical problem)

## Details

### 1 — STORAGES rebinding is correct (score 0, verified)

The exact bug class called out in the task — mutating `base.STORAGES` in place via
`STORAGES["default"] = ...` — is **not** present. `config/settings/production.py:77` rebinds
to a brand-new dict via `{**STORAGES, "default": {...}}`, leaving the object imported from
`base` untouched. The inline comment (lines 71–74) documents exactly why. This is the right
pattern.

Better still, the test suite proves it: `test_base_storages_unmutated_after_s3_override`
(`tests/core/test_production_storage.py:76`) asserts `base.STORAGES["default"]["BACKEND"]` is
still `FileSystemStorage` after the S3 override runs, and `test_storages_is_not_rebound_when_bucket_unset`
(line 46) asserts identity (`production.STORAGES is base.STORAGES`) in the fallback path. The
tests assert the failure mode that matters, not just the happy path. No action needed.

Note also the deliberate fail-fast asymmetry: `access_key`/`secret_key` use `os.environ[...]`
(KeyError if a bucket is set without credentials) while `endpoint_url`/`region_name` use
`.get()` (optional — correct, since real AWS S3 needs no endpoint and R2 supplies `region_name="auto"`).
This matches the module's "fail fast on missing secrets" docstring. Good.

### 2 — DRY sweep: no remaining inline media-URL duplication (score 0, verified)

Swept `suddenly/` for `f"https://{settings.DOMAIN}{...}"` over a FileField/ImageField `.url`.
The only two federation sites that built absolute media URLs (`build_actor` in `activities.py`,
`serialize_user`/`serialize_character` in `serializers.py`) were both converted to
`absolute_media_url()`. The other `settings.DOMAIN` f-strings that remain
(`serializers.py:45,82,114,154,209,230,238`, `views.py:106`) are **entity/page** URLs
(`/@user`, `/games/{pk}`, `/reports/{pk}`), not storage-backed FileFields — they must not use
the helper. The other ImageFields in the model layer (`games.Game.cover`,
`users.User.default_character_background`) are never serialized to an absolute URL anywhere, so
there is no missed call site. `suddenly/users/views.py:91` uses `user.avatar.url` directly, but
that is a relative URL for on-page `<img src>` display (works for both filesystem and S3), not a
federation absolute URL — correctly left alone. DRY is clean.

Also confirmed: `settings` import in `activities.py` is still needed (used by `AP_BASE_URL`
f-strings at lines 83+), so the conversion did not create a dead import.

### 3 — Unused `settings` fixture + imprecise typing (score 1)

`tests/activitypub/test_url_utils.py:16` — `test_passthrough_for_absolute_url(self, settings: object)`
requests the `settings` fixture but never uses it (the passthrough path never touches
`settings.DOMAIN`). Dead parameter. Additionally both tests type the pytest-django fixture as
`object`, forcing a `# type: ignore[attr-defined]` on line 26.

Why it matters: an unused fixture is noise and a false signal that the test depends on Django
settings; the `object` annotation defeats the type checker on the fixture.

Fix: drop the parameter from `test_passthrough_for_absolute_url`; in
`test_prefixes_relative_url_with_domain` type it as pytest-django's wrapper, e.g.
`from pytest_django.fixtures import SettingsWrapper` → `settings: SettingsWrapper`, removing the
`type: ignore`.

### 4 — `absolute_media_url(file_field: Any)` weak type hint (score 1)

`suddenly/activitypub/url_utils.py:12` types the parameter as `Any`, so mypy cannot catch a
caller passing a non-file object, and `url: str = file_field.url` is unchecked. The project
mandates type hints + mypy (CLAUDE.md).

Mitigation/caveat: the surrounding `activitypub` module already types every model argument as
`Any` (`serialize_user(user: Any)`, `build_actor(...: Any)`), so this is consistent with local
convention — hence score 1, not higher.

Fix (optional, if tightening is desired): `from django.db.models.fields.files import FieldFile`
and annotate `file_field: FieldFile`. Return type `-> str` is already correct.

### 5 — `importlib.reload(production)` mutates the module globally (score 1)

`tests/core/test_production_storage.py:33` reloads `config.settings.production` in place.
`monkeypatch` reverts the env vars after each test, but the reloaded module object persists in
`sys.modules` in whatever state the **last** reload left it. If the S3 test runs last, any later
test that imports `config.settings.production` sees an S3-configured `STORAGES`. The docstring
acknowledges the reload is "safe" re: `django.conf.settings`, but not this cross-test residue.

Why it matters: order-dependent, hard-to-trace flakiness the day another test touches
`production`.

Fix: reload the module back to a clean state in a fixture teardown (e.g. an autouse fixture that
`importlib.reload(production)` with no bucket env after yield), or snapshot/restore
`sys.modules["config.settings.production"]`. Low urgency today (no other importer exists), but
cheap insurance.

### 6 — Hardcoded `mediaType: "image/jpeg"` now more exposed (score 1, pre-existing / out of scope)

`serializers.py:55,126` emit `"mediaType": "image/jpeg"` for every avatar icon. With S3/R2 now
accepting arbitrary uploads (and `file_overwrite=False` preserving original extensions), a PNG or
WebP avatar will be advertised to remote instances as `image/jpeg`. This predates the diff (the
change touched only the `url` line) so it is not a regression, but it sits squarely in the media
surface being reviewed. `build_actor` in `activities.py:61` notably omits `mediaType` entirely —
inconsistent with `serializers.py`. Suggest deriving the type from the file (or the model's
content type) or dropping the field; track separately from this PR.

### 7 — `querystring_auth=False` couples to a public bucket (score 0–1, documented)

`production.py:89` disables signed URLs so `.url` returns a stable, non-expiring URL — correct
and necessary, because remote instances cache `icon.url` (the comment says so). The implicit
requirement is that the bucket/R2 binding is publicly readable; a private bucket makes every
federated avatar 403. This is a deployment contract, not a code defect — flagging only so the
handoff/ops checklist records "bucket must be public-read" alongside the `.env` vars. No code
change.

### 8 — factory-boy rule vs `_FakeFileField` stub (score 0, considered & accepted)

`.claude/rules/05-testing/05-pytest.md` says "use factory-boy factories, not manual object
creation." `test_url_utils.py` uses a hand-rolled `_FakeFileField`. This is acceptable and
arguably better here: the rule targets **model** object creation, whereas the unit under test is
a pure function needing only a `.url` attribute; a real `ImageField` factory would drag in
storage/DB for no benefit. No change recommended.

## Notes for the caller

- Rule compliance: `.env.example` comments in French are correct per
  `.claude/rules/01-standards/file-language-and-style.md` (human-consumed path → French); code
  files/docstrings in English are correct (code-style). No language-rule violation.
- No secrets are logged; `LOGGING` config does not touch storage settings. No SSRF: the
  passthrough branch only accepts a `.url` produced by the trusted storage backend, and the
  relative branch prefixes the trusted `settings.DOMAIN`. Security surface is clean.
- Suggested next step: apply findings 3–5 (all one-liners), decide separately on #6. None block a
  commit.
