# Decision: Fork en chaîne sans limite de profondeur

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-009        |
| Date    | 2026-03-05     |
| Feature | Liens          |
| Status  | Accepted       |

## Context

US-17 autorise le fork d'un personnage déjà forké. La question est de savoir si on limite la profondeur de la chaîne et si on interdit les forks circulaires (A fork B, B fork A).

## Decision

Pas de limite de profondeur. Les forks "circulaires" sont autorisés (ce ne sont pas de vrais cycles — chaque fork crée un nouveau personnage distinct).

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Limite à 3 niveaux | Évite les abus | Arbitraire, bride la créativité | Pas de justification narrative |
| Interdire forks circulaires | Arbre propre | Restriction artificielle | Chaque fork est un personnage distinct |

## Consequences

- La lignée est un DAG (graphe orienté acyclique) car chaque fork crée un noeud unique
- L'UI doit afficher un arbre de parenté potentiellement profond
- Performance : requête récursive pour afficher la lignée complète
