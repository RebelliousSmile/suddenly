# Code Review for secure-verify-signature

Harden verify_signature() against DoS: PublicKeyCache with retry, per-instance rate limiting, unified 403 + log warning.

- Status: Approved with minor notes
- Confidence: 9/10

---

- [Main expected Changes](#main-expected-changes)
- [Scoring](#scoring)
- [Code Quality Checklist](#code-quality-checklist)
- [Final Review](#final-review)

## Main expected Changes

- [x] PublicKeyCache model with UUID PK, actor_url (unique, max_length=500), public_key_pem, fetched_at
- [x] verify_signature() refactored with cache lookup + retry on stale key
- [x] Rate limiting per instance domain (100/m known, 10/m unknown)
- [x] Unified 403 + logger.warning on all rejection paths
- [x] django-ratelimit added to federation extras
- [x] Migration generated
- [x] 7 new tests covering cache, retry, rate limiting

## Scoring

### Potentially Unnecessary Elements

- [🟢] No unnecessary code detected

### Standards Compliance

- [🟢] Naming conventions followed — snake_case functions, PascalCase model
- [🟢] Coding rules ok — BaseModel inheritance, UUID PK, Meta.indexes
- [🟡] **Type hints**: `inbox.py:24,34` `_get_request_domain(request)` and `_check_rate_limit(request)` missing `HttpRequest` type annotation (rule: type hints obligatoires)
- [🟡] **Content-Type rule**: `signatures.py:160` fetch uses `Accept: application/activity+json` but AP rule says fetching should use `Accept: application/activity+json, application/ld+json` (missing `ld+json` fallback)

### Architecture

- [🟢] Proper separation of concerns — model in models.py, signature logic in signatures.py, rate limiting in inbox.py
- [🟢] No business logic in models
- [🟡] **Rule violation**: `signatures.py:157` `_fetch_public_key` does a direct HTTP call. AP rule says "No direct HTTP calls in views — use Celery tasks (or sync fallback)". This is in a utility function called from a view, not a Celery task. Acceptable for signature verification (sync is necessary here), but worth documenting as intentional exception.

### Code Health

- [🟢] Functions are small and focused (< 30 lines each)
- [🟢] Cyclomatic complexity acceptable
- [🟢] No magic numbers — rate limits are named constants
- [🟢] Error handling complete on all paths

### Security

- [🟢] SQL injection risks — none, using ORM
- [🟢] No XSS — no HTML rendering
- [🟢] Rate limiting implemented per domain
- [🟢] Timeout enforced on outbound HTTP (10s)
- [🟡] **Domain extraction**: `inbox.py:26-30` `_get_request_domain` parses Signature header manually. A malformed Signature header with crafted keyId could return unexpected domain values. Low risk since rate limiting is defense-in-depth, not sole protection.

### Error management

- [🟢] All failure paths return 403 with log warning
- [🟢] HTTP exceptions caught broadly in `_fetch_public_key`

### Performance

- [🟢] DB query for cache is indexed (actor_url unique)
- [🟡] **Double domain extraction**: `inbox.py:93-94` `_get_request_domain` called twice when rate limit is exceeded (once inside `_check_rate_limit`, once for logging). Minor — only on rejected requests.
- [🟡] **DB query per request**: `inbox.py:42` `FederatedServer.objects.filter().exists()` runs on every request. Could be cached in-memory for known domains, but premature optimization for v1.

### Backend specific

#### Logging

- [🟢] Logging implemented on all rejection paths with structured format

## Final Review

- **Score**: 9/10
- **Feedback**: Clean implementation that follows the plan precisely. All 3 phases are correctly implemented. The code is well-structured with clear separation between cache, rate limiting, and verification logic. The refactoring of verify_signature() into smaller helpers improves testability.
- **Follow-up Actions**:
  - Add `HttpRequest` type annotation to `_get_request_domain` and `_check_rate_limit` (minor)
  - Add `application/ld+json` to Accept header in `_fetch_public_key` (AP rule compliance)
- **Additional Notes**: 6 pre-existing test failures in test_activitypub.py are unrelated to this change (confirmed by running same tests on main branch). The `sign_request` host/Host case mismatch bug predates this PR.
