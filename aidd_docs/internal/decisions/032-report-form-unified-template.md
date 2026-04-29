---
name: decision
description: Template unifié report_form.html pour création et édition
type: decision
---

# Decision: Template unifié pour les formulaires de report

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-032        |
| Date    | 2026-04-29     |
| Feature | Report editor  |
| Status  | Accepted       |

## Context

Les formulaires de création (`report_create`) et d'édition (`report_edit`) d'un report étaient quasi-identiques. Maintenir deux templates séparés introduisait de la duplication et des risques de divergence.

## Decision

Un seul template `games/report_form.html` utilisé par les deux vues. La variable de contexte `report` distingue les deux modes : `report=None` → création, `report=<instance>` → édition.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Deux templates distincts | Indépendance totale | Duplication, divergence silencieuse | Violait DRY |
| Héritage de template Django | Factorisation du HTML commun | Complexité des blocs | Surcharge inutile pour deux vues proches |

## Consequences

- Les vues `report_create` et `report_edit` passent toutes deux `report` dans le contexte (respectivement `None` et l'instance)
- Le template utilise `{{ form_data.field|default:report.field|default:'' }}` pour pré-remplir les champs en édition
- La section Cast n'est affichée qu'en création (`{% if not report %}`)
- Les boutons d'action diffèrent selon `report.status` : draft → "Publish" + "Save draft" ; published → "Save"
