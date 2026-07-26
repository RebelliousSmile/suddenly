---
objective: >
  Épique #139 — PR 2 (#145) : purge des références Quotes dans la documentation normative
  (mémoire auto-chargée) et les user stories. Complète le hard delete du code (PR 1, #170 mergée).
success_condition: >
  grep -rin "total_quotes|EPHEMERAL_QUOTE|cleanup_expired_quotes|quote_card|US-30|US-08" aidd_docs/memory/ .claude/rules/08-domain/08-activitypub.md aidd_docs/tasks/suddenly-stories.md → vide
plan_kind: simple
confidence: 9
iteration: 1
created_at: 2026-07-22
---

# Épique #139 — retrait des Quotes (PR 2 : docs / mémoire, #145)

## Objectif

Après le hard delete du code (PR 1, #170), purger les mentions Quote de la **doc normative
auto-chargée** et des user stories, pour qu'aucun document décrivant une capacité disparue ne
subsiste dans le contexte chargé à l'implémentation.

## Fichiers purgés

| Fichier | Retrait |
|---------|---------|
| `memory/PROJECT_BRIEF.md` | ligne glossaire Citation, pilier « publier des citations », ligne AP `Quote\|Note` |
| `memory/internal/DATABASE.md` | table `Quote`, arêtes ER, index, `total_quotes` de `UserUsageStats` |
| `memory/CODEBASE_MAP.md` | `Quote` du nœud characters |
| `memory/CODING_ASSERTIONS.md` | assertions éphémères + `EPHEMERAL_QUOTE_TTL_HOURS` (+ section vidée) |
| `memory/VCS.md` | scope de commit `quotes` |
| `memory/internal/DESIGN.md` | `quote_card` + état `quoted` |
| `memory/internal/API_DOCS.md` | verbes AP Quote, `suddenly:quotes`, ligne compat Mastodon |
| `memory/DEPLOYMENT.md` | ligne crontab `cleanup_expired_quotes` |
| `memory/external/alwaysdata-deployment.md` | bloc tâche planifiée « citations éphémères » |
| `memory/architecture.md` | référence `(US-30)` obsolète sur `content_warning` (champ conservé) |
| `memory/external/seeds.md` | ligne seed « Citations ~110 » + mention « citations » |
| `.claude/rules/08-domain/08-activitypub.md` | mapping `Quote=Note` |
| `tasks/suddenly-stories.md` | **US-08 « Citations »** (Domaine 5) + **US-30**, lignes gherkin (fiche perso, Note Mastodon), « CR ou citation » → « CR » dans US-25, lignes des tables de priorité |

## Décisions

- **US-08** (la vraie user story Quote, en français « Citations ») retirée en plus d'US-30 — le
  périmètre initial ne nommait qu'US-30, mais US-08 décrivait la fonctionnalité supprimée.
- **Hors périmètre (archives, laissés)** : `aidd_docs/wireframes/**` (mockups historiques, dont
  `08-quotes.md`), `aidd_docs/tasks/MASTER_PLAN.md` et les plans/audits datés (records historiques
  du build d'origine, où Quote existait), `memory/external/bookwyrm-architecture.md` (référence
  externe). Cohérent avec la règle normative-vs-archive : on ne réécrit pas l'historique.

## Vérification
- Greps #145 (`total_quotes`, `EPHEMERAL_QUOTE`, `cleanup_expired_quotes`, `quote_card`, `US-30`,
  `US-08`, `Domaine 5`) sur mémoire + règle AP + stories = **vide**.
- Refs `quote`/`citation` restantes uniquement dans les archives historiques (MASTER_PLAN,
  wireframes, plans datés) et faux positifs (`blockquote`, « single quotes »).

## Points de vigilance
- **Pas de renumérotation** des US/domaines restants (gap Domaine 4→6 assumé, archive lisible).
- **Aucun code/test/.po touché** — PR strictement documentaire.

## Évaluation de confiance : 9/10
Purge documentaire ciblée sur la couche normative, archives préservées, vérif grep verte.
