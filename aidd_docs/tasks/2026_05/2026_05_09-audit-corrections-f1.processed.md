# Instruction: Audit corrections F1 — perf + data audits

## Feature

- **Summary**: Apply remaining F1 quick wins from the 2026-05-08 perf audit and 2026-05-09 data audit. Closes the heartbeat `setInterval` leak, migrates fonts to self-hosted via Django static, and wires explicit cache invalidation signals so the service-level caches reflect mutations immediately instead of waiting for TTL expiry.
- **Stack**: `Django 5.x`, `Python 3.12+`, `WhiteNoise + CompressedManifestStaticFilesStorage`, `Alpine.js 3.14`, `Vite 5.4`, `PostgreSQL`
- **Branch name**: `fix/audit-corrections-f1`
- **Parent Plan**: `none`
- **Sequence**: `standalone`
- Confidence: 9.5/10
- Time to implement: ~2h45 total (Phase 0: 10 min, Phase 1: 1h30, Phase 2: 1h)

## Existing files

- @frontend/src/main.js
- @templates/base.html
- @suddenly/core/services.py
- @suddenly/core/apps.py
- @suddenly/characters/models.py
- @suddenly/games/models.py
- @suddenly/users/models.py
- @suddenly/games/models.py
- @suddenly/activitypub/models.py

### New file to create

- templates/components/_fonts.html
- static/fonts/ (Inter 400/600/700 + Crimson Text 400 [+ italic if above-fold])
- suddenly/core/cache_invalidation.py
- tests/core/test_cache_invalidation.py

## User Journey

```mermaid
flowchart TD
  A[Visitor lands on /] --> B[base.html renders <head>]
  B --> C[_fonts.html @font-face from /static/fonts/ hashed]
  B --> D[preload Inter 400 + 600 above-fold]
  C --> E[FOUT bref puis Inter rendered]
  D --> E
  A --> F[/explorer/ loaded]
  F --> G[get_distinct_tag_names cache hit]
  A --> H[User edits Character + adds tag]
  H --> I[Tag.set on M2M through]
  I --> J[m2m_changed signal fires]
  J --> K[cache.delete explorer_tags:characters.character]
  K --> L[Next /explorer/ hit recomputes + caches]
  A --> M[User navigates SharedSequence page]
  M --> N[Alpine presence component init]
  N --> O[poll interval + heartbeat interval started]
  O --> P[User navigates away]
  P --> Q[destroy clears BOTH intervals]
```

## Implementation phases

### Phase 0 — Heartbeat setInterval leak fix

> Stop the orphan interval after navigation by storing the heartbeat handle and clearing it in destroy().

1. Add `heartbeatInterval: null,` next to `interval: null,` in the `presence` Alpine component data object (`frontend/src/main.js` near line 386)
2. Replace bare `setInterval(() => this.heartbeat(), 10000)` with `this.heartbeatInterval = setInterval(() => this.heartbeat(), 10000)` (line 393)
3. Append `clearInterval(this.heartbeatInterval)` inside `destroy()` after the existing `clearInterval(this.interval)` (line 397)

### Phase 1 — Self-host Inter + Crimson Text fonts (Django static, no Vite)

> Eliminate the render-blocking Google Fonts request and let Manifest serve hashed woff2 with immutable Cache-Control.

1. Audit italic usage: `grep -rn "italic\|font-style" templates/ frontend/src/` to decide whether Crimson Text italic 400 is above-fold or skipable
2. Download woff2 files from google-webfonts-helper for Inter (400, 600, 700) and Crimson Text (400 + italic if needed), Latin + Latin-ext subsets
3. Place all woff2 in `static/fonts/`
4. Create `templates/components/_fonts.html` with:
   - One `<style>` block declaring `@font-face` for each weight, `src: url("{% static 'fonts/<file>.woff2' %}") format('woff2')`, `font-display: swap`
   - One `<link rel="preload" as="font" type="font/woff2" crossorigin href="{% static 'fonts/inter-400.woff2' %}">` per above-fold weight (Inter 400 + 600 only)
5. Edit `templates/base.html`:
   - `{% include 'components/_fonts.html' %}` in `<head>` **before** `{% vite_css %}` so @font-face declarations register before any rule using `font-family`
   - Remove `<link rel="preconnect" href="https://fonts.googleapis.com">` and `https://fonts.gstatic.com` (lines 20-21)
   - Remove the synchronous `<link href="https://fonts.googleapis.com/css2?family=...">` (line 24)
6. Local validation: `python manage.py collectstatic --noinput` then a `DEBUG=False` smoke run to confirm Manifest resolves every `{% static 'fonts/...' %}`

### Phase 2 — Cache invalidation centralisée + signal wiring

> Replace TTL-only freshness with explicit invalidation so admin actions reflect immediately on public pages.

1. Create `suddenly/core/cache_invalidation.py`:
   - One handler function per cache key family (5 handlers): `invalidate_explorer_tags_character`, `invalidate_explorer_tags_game`, `invalidate_explorer_game_systems`, `invalidate_recent_public_reports`, `invalidate_instance_stats`
   - Each handler imports its models lazily (inside the function) to avoid app-load cycles
   - `invalidate_recent_public_reports` calls `cache.delete_many([f"recent_public_reports:{n}" for n in RECENT_REPORTS_LIMITS])`
2. Expose `RECENT_REPORTS_LIMITS = (3,)` in `suddenly/core/services.py` (single caller today, default `limit=3`); document inline that adding a non-default caller requires adding the limit here
3. Wire signals in `suddenly/core/apps.py` `CoreConfig.ready()`:
   - Each `signal.connect(handler, sender=Model, dispatch_uid="suddenly.cache.<handler_name>")` — every connect MUST carry a unique `dispatch_uid` to survive `--reuse-db` and dev autoreload
   - Add a comment block at the top: `# Renaming a handler? Rename its dispatch_uid too — stale handlers stay connected in the dev process otherwise.`
   - For `m2m_changed` connections, the handler filters `if action not in {"post_add", "post_remove", "post_clear"}: return` (skip pre_* and avoid double work)
4. Mappings to wire:
   - `m2m_changed` on `Character.tags.through` → `invalidate_explorer_tags_character`
   - `m2m_changed` on `Game.tags.through` → `invalidate_explorer_tags_game`
   - `post_save` on `Game` → `invalidate_explorer_game_systems`
   - `post_save` + `post_delete` on `Report` → `invalidate_recent_public_reports` (no status filter, KISS)
   - `post_save` + `post_delete` on `User`, `Character`, `Report`, `FederatedServer` → `invalidate_instance_stats`
5. Create `tests/core/test_cache_invalidation.py`:
   - For each handler, the test pattern is: `cache.set(<key>, sentinel, 600)` → trigger the model mutation → `assert cache.get(<key>) is None`
   - Cover the 5 handlers + the `m2m_changed action` filter (assert that `pre_add` does NOT invalidate)
6. DEC inline in the Phase 1 + Phase 2 commit messages:
   - `WHITENOISE_MAX_AGE` not added — redundant with `CompressedManifestStaticFilesStorage` which already serves hashed files with `Cache-Control: max-age=31536000, public, immutable` automatically
   - `@cache_page` rejected — risk of caching navbar auth state, django messages framework conflicts, and Accept-Language vary complexity. Cache moved to service layer in `core/services.py`, invalidation via signals.

## Validation flow

1. **Phase 0** — Open the SharedSequence page hosting the `presence` component, then navigate to another page 5 times. Open DevTools Performance → record → no orphan timer should remain after navigation. Check `setInterval`/`clearInterval` balance under Performance > Timings.
2. **Phase 1** —
   - `pnpm --dir frontend build && python manage.py collectstatic --noinput` succeeds, woff2 listed in collectstatic output
   - `DEBUG=False python manage.py runserver --insecure 0.0.0.0:8000` boots without `Missing staticfiles manifest entry`
   - Open `http://localhost:8000/`, DevTools Network filtered on `font` → woff2 served from `/static/fonts/inter-...woff2` (or hashed equivalent) with `200`, no calls to `fonts.googleapis.com` or `fonts.gstatic.com`
   - Visual check: no FOIT (invisible text), brief FOUT acceptable
   - Optional `curl -I` on the deployed hashed font URL → `Cache-Control: max-age=31536000, public, immutable`
3. **Phase 2** —
   - Edit a Character via admin → add a brand new tag in the CSV field → reload `/explorer/` → tag appears in the filter list immediately (no 5-min TTL wait)
   - Publish a Report (status PUBLISHED) → reload `/` → report appears in `recent_reports` block immediately
   - Create a new Character → reload `/about/` → `characters` counter incremented immediately
   - `pytest tests/core/test_cache_invalidation.py -v` → 5+ tests pass
   - `make check` → ruff + mypy + pytest all green
