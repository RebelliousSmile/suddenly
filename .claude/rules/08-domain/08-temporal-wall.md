---
paths:
  - "suddenly/games/**/*.py"
  - "suddenly/characters/**/*.py"
  - "suddenly/core/**/*.py"
---

# Temporal wall — gating reports (SUD-V1)

## Two canonical wall filters

- `Report.objects.released()` — strict, **local-only**: `released_at` set + `PUBLISHED` + `PUBLIC`
- `Report.objects.feed_visible()` — listings/feeds, **remote-tolerant**: `PUBLISHED` + `PUBLIC` + `Q(remote=True) | Q(released_at__isnull=False)`
- Never re-express either filter inline — call the queryset method
- Never add a third wall filter — extend one of these two

## Which one

- End-to-end reading, Stories, single-story aggregation → `released()` (SUD-V3)
- Any *listing* of reports (feeds, API querysets, appearances, onboarding) → `feed_visible()`
- Federation axis ≠ liberation axis: remote reports never get `released_at` (set only on local liberation), so `released()` would wrongly drop all remote content

## Listings are gated, not just detail

- The wall gates listings too — a published-but-unreleased report must not surface to anyone but its author
- A new report-listing surface that skips `feed_visible()` leaks behind-wall reports
- Owner-aware exception (`game_detail`): owner sees own still-behind-wall reports; every other visitor → `feed_visible()`

## Direct-URL 404 is deliberate

- Unreleased report by direct URL → 404 for non-author/non-GM
- Never render a "behind the wall" placeholder page — it discloses the report's existence
