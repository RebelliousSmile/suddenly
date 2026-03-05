# AIDD Workflow — Conception to Implementation

## Triggers — quand ce workflow s'applique

Ce workflow s'applique à **toute demande qui touche au comportement ou à la structure du code** :

- Nouvelle fonctionnalité (même "petite")
- Modification de comportement existant
- Refactoring ou restructuration
- Invocations explicites : `@claire`, `/brainstorm`, `/create_user_stories`, `/ticket_info`

Ne s'applique PAS à : correction de typo, renommage trivial, modification d'une valeur isolée sans impact fonctionnel.

## Étape 1 — Avant tout : écrire un plan

Dès qu'un trigger est détecté :
1. Lire les fichiers concernés
2. Écrire un plan dans `aidd_docs/tasks/<yyyy_mm>/`
3. Attendre la validation explicite de l'utilisateur
4. Ne pas implémenter avant cette validation

## Étape 2 — Après implémentation

- Mettre à jour les user stories dans `aidd_docs/memory/` si impacté

## Règles absolues

- **Jamais implémenter sans plan validé** — même si la demande semble simple
- **Clarification ≠ autorisation d'implémenter**
- **Reprise de session** : si "l'étape suivante" est un plan, demander avant d'agir
- **Une demande directe de feature est un trigger** — l'absence de `/brainstorm` ne dispense pas du plan
