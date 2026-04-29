# Code Review — Explorer Nav Refactor

**Date**: 2026-04-29
**Branch**: feat/explorer-nav-refactor (commits on main, unstaged changes)
**Reviewer**: Claude Code

---

## Score Table

| # | Titre | Fichiers | Score |
|---|---|---|---|
| 1 | Services reçoivent `HttpRequest` — viole la règle services | `characters/services.py`, `games/services.py` | 2 |
| 2 | Commentaires "WHAT" dans `build_character_queryset` | `characters/services.py` | 1 |
| 3 | Module docstring `characters/services.py` ne reflète plus le contenu | `characters/services.py` | 1 |

---

## Détail des issues

### Issue 1 — Score 2 (major)

**Règle violée** (`rules/custom/03-django-services.md`) :
> Service methods receive domain objects, not request objects

`build_character_queryset(request: HttpRequest)` et `build_game_queryset(request: HttpRequest)` reçoivent le `HttpRequest` directement. Les services ne doivent pas dépendre du protocole HTTP — ils doivent recevoir des paramètres métier.

**Fix** : changer les signatures pour accepter des paramètres nommés extraits dans les vues :

```python
# service
def build_character_queryset(
    q: str = "",
    status: str = "",
    system: str = "",
    tag: str = "",
) -> QuerySet[Character]: ...

# appelants (views)
qs = build_character_queryset(
    q=request.GET.get("q", ""),
    status=request.GET.get("status", ""),
    system=request.GET.get("system", ""),
    tag=request.GET.get("tag", ""),
)
```

Même fix pour `build_game_queryset` (params : `system`, `tag`, `q`).

---

### Issue 2 — Score 1 (minor)

`build_character_queryset` contient 3 commentaires qui expliquent le WHAT :

```python
# Status filter       ← remove
# Game system filter  ← remove
# Tag filter          ← remove
# FTS search (uses GIN index from T13)  ← keep (WHY non-obvious)
```

**Règle** (`CLAUDE.md`) : "Default to writing no comments. Only add one when the WHY is non-obvious."

---

### Issue 3 — Score 1 (minor)

Le docstring module de `characters/services.py` :
```python
"""
Character link services.

Business logic for claim, adopt, and fork workflows.
"""
```

La fonction `build_character_queryset` n'est pas un workflow claim/adopt/fork. Le docstring est devenu inexact.

**Fix** : `"Character services — link workflows and queryset builders."`

---

## Éléments corrects

- Nav desktop + mobile : Explorer/Jouer bien placés hors du bloc auth ✅
- `x-data="{ selectMode: false }"` sur container outer (pas sur `#explorer-results`) ✅
- Résultats pré-rendus, pas de `hx-trigger="load"` ✅
- FTS complet dans `build_character_queryset` (SearchQuery/SearchVector/SearchRank) ✅
- `build_game_queryset` inclut filtre text `q` (title + description icontains) ✅
- Type hints complets, mypy clean ✅
- Pas de duplication — `_build_*` supprimés des front_views ✅
- i18n complet — toutes les chaînes traduites, .po et .mo à jour ✅
