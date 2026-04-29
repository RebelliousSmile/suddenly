---
description: Prevent code duplication — extract shared logic before copying, enforce DRY across views, templates, and services. Apply when writing new views, templates, or business logic that resembles existing code.
---

# DRY — Don't Repeat Yourself

## General

- Search for existing helper/service/component before duplicating
- Extract shared logic into a helper or service when used 2+ times
- Run `/simplify` after implementation to catch remaining duplication

## Django-specific

- Shared queryset logic → `_build_X_queryset()` helper (see `_build_character_queryset`, `_build_game_queryset`)
- Shared template blocks → `{% include "components/..." %}`
- Shared business logic → service layer, not views or models
