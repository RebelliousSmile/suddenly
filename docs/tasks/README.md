# Tâches de Développement — Suddenly

Ce dossier contient les définitions de tâches pour le développement de Suddenly.

## Phase 1 : Fondations

| Tâche | Durée | Statut | Description |
|-------|-------|--------|-------------|
| [00-init-projet](./00-init-projet.md) | 30 min | [ ] | Structure projet, venv, dépendances |
| [01-config-django](./01-config-django.md) | 1h | [ ] | Settings modulaires, urls, wsgi |
| [02-app-core](./02-app-core.md) | 30 min | [ ] | BaseModel, ActivityPubMixin |
| [03-app-users](./03-app-users.md) | 2h | [ ] | User étendu, auth allauth |
| [04-app-federation](./04-app-federation.md) | 30 min | [ ] | FederatedServer, Follow (structure) |
| [05-app-games](./05-app-games.md) | 2h | [ ] | Game, Report, vues HTMX |
| [06-templates-base](./06-templates-base.md) | 1h | [ ] | Layout, navbar, composants |
| [07-premiere-migration](./07-premiere-migration.md) | 30 min | [ ] | Migration, superuser, validation |

**Durée totale Phase 1 : ~8h**

## Phases Suivantes (à définir)

- **Phase 2** : Characters, Appearances, Quotes
- **Phase 3** : LinkRequest, CharacterLink, SharedSequence, workflow Claim/Adopt/Fork
- **Phase 4** : ActivityPub, HTTP Signatures, fédération

## Convention des Fichiers

Chaque tâche suit le format :

```markdown
# Tâche XX : Titre

## Objectif
[Ce que la tâche accomplit]

## Prérequis
[Tâches précédentes, outils nécessaires]

## Fichiers à Créer/Modifier
[Liste des fichiers avec leur contenu attendu]

## Étapes
[Instructions détaillées]

## Validation
[Critères de succès]

## Références
[Documentation liée]
```
