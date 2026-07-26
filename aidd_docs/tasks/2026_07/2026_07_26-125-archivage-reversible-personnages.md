---
objective: >
  #125 — Archivage réversible (soft-hide) des personnages : masquer un personnage des
  listes publiques / découverte / recherche sans le détruire, de façon réversible.
success_condition: >
  cd app && python manage.py check && python manage.py makemigrations --check --dry-run
  && ruff check . && ruff format --check . && mypy suddenly/
  && pytest tests/characters/test_archive.py (7 passed)
plan_kind: simple
confidence: 9
iteration: 1
created_at: 2026-07-26
---

# #125 — Archivage réversible des personnages

## Objectif

Le retrait d'un personnage depuis la liste était une **suppression définitive** (`character_delete`,
hard delete). L'archivage réversible ajoute une bascule de visibilité locale : le personnage est
masqué des surfaces publiques mais conservé, restaurable à tout moment. La suppression définitive
reste disponible comme action distincte.

## Périmètre livré

| Couche | Détail |
|--------|--------|
| Modèle | `Character.is_archived` BooleanField (default False) + index ; migration `characters/0025_character_is_archived_and_more.py` |
| Service | `build_character_queryset` filtre `is_archived=False` (découverte/recherche) ; `archive_character` / `unarchive_character` (creator-only, garde lien PENDING/QUEUED) ; `owned_archived_characters` (section restauration) |
| Vues | `character_archive` / `character_unarchive` — `@require_POST` + `@login_required`, creator-only, messages Django |
| Routes | `characters:archive` / `characters:unarchive` (`<slug>/archive/`, `<slug>/unarchive/`) |
| UI | bouton « Archiver » sur la carte (creator-only, `_list_results.html`) + section « Archivés » repliable avec « Restaurer » (`list.html`) |
| i18n | 9 chaînes FR ajoutées au `.po`, `.mo` recompilé (babel) |
| Tests | `tests/characters/test_archive.py` — 7 tests (queryset, archive/restore, non-creator 404, GET 405, garde lien PENDING, section liste) |

## Décisions (points « à trancher » de l'issue)

- **Fédération : silencieuse.** Aucun `Delete`/`Update` AP émis à l'archivage. L'archivage est une
  bascule de visibilité **locale et réversible** ; émettre un `Delete` puis re-`Create` à la
  restauration serait bruyant et incorrect vis-à-vis des instances distantes. Documenté sur le
  champ modèle et le service.
- **Liens actifs : archivage interdit tant qu'un `LinkRequest` PENDING/QUEUED cible le personnage.**
  Archiver sous une demande Claim/Adopt/Fork en attente laisserait le demandeur sans cible. Le
  créateur doit résoudre/annuler la demande d'abord (message d'erreur explicite, `ValidationError`).

## Points de vigilance

- Le profil ne liste plus les personnages depuis #154 — la surface de gestion est `characters:list`,
  où vivent le bouton Archiver et la section Archivés (pas le profil).
- La section « Archivés » est rendue par `list.html` (page complète), pas par le partial de
  recherche `_list_results.html` swappé en HTMX — elle ne réapparaît pas à chaque frappe.
- Accès direct à la fiche d'un personnage archivé : non modifié (l'issue vise le masquage des
  *listes*, pas un 404 sur la fiche).

## Évaluation de confiance : 9/10

Périmètre local circonscrit, aucune couture fédérée, vérifié statiquement (check/ruff/mypy/migration)
et par 7 tests ciblés verts.
