# Decision: i18n — fichiers .mo versionnés, compilation via babel

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-023        |
| Date    | 2026-04-28     |
| Feature | i18n           |
| Status  | Accepted       |

## Context

Les fichiers `.mo` étaient dans `.gitignore` (stratégie "généré au déploiement"), mais `gettext` n'est pas installé sur Windows ni dans le Dockerfile de base. Résultat : les traductions françaises n'étaient pas compilées en production sur Railway, et les nouveaux messages ajoutés restaient en anglais.

## Decision

Versionner les `.mo` directement dans git. Les compiler via `babel` (déjà dépendance Python) en développement. Ajouter `gettext` dans le Dockerfile et une étape `compilemessages` dans le build final pour les mises à jour futures.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Générer en entrypoint Docker | Toujours à jour | Requiert `gettext` + accès écriture au runtime | Fragile, ralentit le démarrage |
| Installer gettext sur Windows | Cohérence dev/prod | Installation manuelle, non portable | Friction inutile pour une tâche rare |
| Garder dans .gitignore + doc | Simple | Oublié systématiquement → prod cassée | Déjà arrivé plusieurs fois |

## Consequences

- Les `.mo` sont toujours disponibles sur toutes les plateformes sans pré-requis système
- Compiler via `babel` : `from babel.messages.mofile import write_mo; from babel.messages.pofile import read_po`
- Après chaque modification de `.po`, relancer la compilation et committer les `.mo`
- Dockerfile conserve `gettext` + `compilemessages` pour la cohérence et les rebuilds complets
