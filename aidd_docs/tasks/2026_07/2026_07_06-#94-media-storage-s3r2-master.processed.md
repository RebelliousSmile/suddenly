# Master Plan: Media storage S3/R2 + federated URL reliability

## Overview

- **Goal**: Make `ImageField` uploads (User.avatar, Character.avatar) persist in production (Railway) via optional S3/Cloudflare R2 storage, and fix ActivityPub icon URL generation so it works with both local and remote storage backends. Resolves #94 (media storage) and #98 (avatar not displaying — confirmed root cause: production serves no `/media/` path and has no persistent volume).
- **Risk Score**: 4/10
- **Branch**: `feature/media-storage-s3r2/`

## Phase 0 — External prerequisites (no code, do first)

> Per planning rule: configurations (API keys, external resources) must be prepared as early as possible — not left as a deploy-time surprise.

- [ ] Create a Cloudflare R2 bucket (or AWS S3 bucket) for media storage
- [ ] Generate access key ID + secret access key scoped to that bucket
- [ ] Configure **public read access** at the bucket level (R2: enable Public Development URL or attach a custom domain — not a per-object ACL, R2 does not support AWS-style ACLs the same way). Without this, avatar URLs will return 403 even though code and settings are correct — this is a required manual step, not optional
- [ ] Note the account ID / endpoint URL and target region (`"auto"` for R2) for use in Phase 1's env vars

## Child Plans

| #   | Plan                                  | File            | Status  | Validated |
| --- | -------------------------------------- | --------------- | ------- | --------- |
| 1   | Conditional S3/R2 storage config       | `./2026_07_06-#94-media-storage-s3r2-part-1.md` | pending | [ ]       |
| 2   | Federated URL reliability (DRY helper) | `./2026_07_06-#94-media-storage-s3r2-part-2.md` | blocked | [ ]       |
| 3   | Operational documentation              | `./2026_07_06-#94-media-storage-s3r2-part-3.md` | blocked | [ ]       |
| 4   | Tests                                  | `./2026_07_06-#94-media-storage-s3r2-part-4.md` | blocked | [ ]       |

<!-- Status values: pending, in-progress, done, blocked -->
<!-- RULE: Plan N+1 blocked until Plan N checkbox checked -->

## Validation Protocol

> Phase 0 runs in parallel with Plans 1-4 (all of Plans 1-4 are testable with dummy env vars, per their own validation flows) — it only gates the **final integration test**, not the start of coding.

0. [ ] Checkpoint 0: Phase 0 prerequisites confirmed available (bucket, keys, public access) — required before step 8, not before step 1
1. Complete Plan 1, run its validations (settings load correctly with/without `AWS_STORAGE_BUCKET_NAME`; `base.STORAGES` unmutated)
2. [ ] Checkpoint 1: User confirms
3. Unblock Plan 2, repeat (federated URLs correct for both storage backends)
4. [ ] Checkpoint 2: User confirms
5. Unblock Plan 3, repeat (`.env.example` complete and accurate)
6. [ ] Checkpoint 3: User confirms
7. Unblock Plan 4, repeat (backend-selection and URL-helper logic covered by tests)
8. [ ] Final: Integration test — deploy to Railway with real R2 bucket, confirm avatar upload persists across a redeploy and displays correctly (including public read access), including in a federated `Actor`/`icon` payload. Note: users who set an avatar before this fix will not have their old file automatically migrated (Railway's ephemeral filesystem never reliably kept it) — expect them to need to re-upload once

## Investigation Findings (informing this plan)

- Django 5.0 already uses the modern `STORAGES` dict (`config/settings/base.py:127-137`) — no legacy `DEFAULT_FILE_STORAGE` migration needed.
- `production.py` already has a conditional-env-var pattern (`REDIS_URL`, `EMAIL_HOST`) to replicate for `AWS_STORAGE_BUCKET_NAME`.
- Self-hosted deployment (`docker-compose.yml`) already has a persistent Docker volume for `media/` — must stay on filesystem storage by default, only switch when `AWS_STORAGE_BUCKET_NAME` is set.
- Issue #94's original env var list is incomplete: `AWS_S3_REGION_NAME` is required by django-storages when a custom `AWS_S3_ENDPOINT_URL` is set (R2), otherwise `AuthorizationQueryParametersError`.
- `avatar.url` is not just a settings concern: `suddenly/activitypub/activities.py:61` and `suddenly/activitypub/serializers.py:54,125` manually concatenate `https://{domain}` in front of `.url`. This is correct only for `FileSystemStorage` (relative path); `S3Storage.url` returns an already-absolute URL, so the current code would produce a corrupted double-domain URL once S3/R2 is active. 3 call sites affected → DRY refactor required (project rule), not 3 identical patches.
- `.env.example` does not exist in the repo — must be created, not edited.
- `AWS_QUERYSTRING_AUTH` (default `True`) would make avatar URLs expire after 1h — breaks federation (remote instances cache `icon.url`). Must be set to `False` — but this only produces working URLs if the bucket is *also* configured for public read at the infrastructure level (Phase 0), otherwise `querystring_auth=False` just trades a 404 for a 403.
- `AWS_S3_FILE_OVERWRITE` (default `True`) can silently overwrite same-named files from different users — must be set to `False`.
- `STORAGES`/`CACHES` are imported into `production.py` via `from .base import *`, which binds the *same* dict object, not a copy. The conditional override must rebind the name to a new dict (as `CACHES` already does), never mutate via item assignment (`STORAGES["default"] = ...`) — the latter would corrupt `base.STORAGES` for every other settings module sharing the reference.
- Existing users who already set an avatar before this fix have a DB reference to a file that never reliably survived Railway's ephemeral filesystem — switching to S3/R2 does not backfill it; they will need to re-upload once.

## Estimations

- **Confidence**: 9/10
- **Duration**: ~2.5 days total (0.5 + 0.5 + 0.5 + 1 day across the 4 parts)

### Confidence detail

- Reasons for high confidence:
  - Full codebase investigation done (2 sub-agent passes) — all touch points identified, including the non-obvious federation URL bug.
  - No DB migration, no breaking change to existing local/self-hosted behavior (conditional fallback preserves current filesystem path).
  - Django/django-storages version compatibility confirmed via official docs (Context7).
  - Existing code conventions (`os.environ` conditional pattern) directly reusable — no new config paradigm introduced.
- Residual risks (not blocking the plan, but flagged for the final integration checkpoint):
  - No real R2 bucket/credentials exist yet — end-to-end upload-to-R2 cannot be verified until deployment (Phase 4 tests only cover backend-selection and URL-helper logic, not a live S3 round-trip).
  - Cloudflare R2's public-access model differs slightly from AWS S3 ACLs — may need a one-off adjustment once real credentials are available, outside this plan's code scope.
