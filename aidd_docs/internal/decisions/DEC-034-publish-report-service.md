---
name: DEC-034-publish-report-service
description: publish_report() service partagé — tous les chemins de publication passent par le service
type: decision
---

# Decision: publish_report service partagé

| Field   | Value                     |
| ------- | ------------------------- |
| ID      | DEC-034                   |
| Date    | 2026-05-01                |
| Feature | Games / US-13             |
| Status  | Accepted                  |

## Context

La logique de publication d'un rapport (création des NPCs depuis le cast, création des CharacterAppearances, mise à jour du statut) existait en doublon dans le API ViewSet (`views.py`) et les front views (`front_views.py`). Lors de l'implémentation de US-13, `report_compose` a été oublié et ne passait plus par la logique de publication — les NPCs n'étaient jamais créés via ce chemin.

## Decision

Extraire `publish_report(report, user)` dans `games/services.py` (avec `@transaction.atomic`). Tous les chemins qui publient un rapport — API ViewSet, `report_create`, `report_edit`, `report_compose` — appellent ce service. Aucune logique de publication inline dans les vues.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Logique inline dans chaque vue | Simple localement | Duplication, oubli garanti | Prouvé : `report_compose` a été oublié |
| Signal `post_save` sur Report | Automatique | Couplage implicite, difficile à tester | Services explicites préférés dans ce projet |

## Consequences

- ✅ Un seul endroit à maintenir pour la logique de publication
- ✅ `transaction.atomic` garantit la cohérence NPC + CharacterAppearance
- ✅ Testable indépendamment des vues
- ⚠️ Tout nouveau chemin de publication doit penser à appeler `publish_report()` — documenter dans les code reviews
