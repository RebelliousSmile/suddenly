# Decision: SharedSequence en discussion asynchrone libre

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-010        |
| Date    | 2026-03-05     |
| Feature | SharedSequence |
| Status  | Accepted       |

## Context

US-18/19 décrivent la co-écriture d'une scène après acceptation d'un lien. Le brief envisageait un éditeur type Etherpad. Il faut choisir le format MVP.

## Decision

MVP : interface type discussion narrative. Chaque joueur poste des blocs Markdown librement (pas de tours imposés). Chacun voit ce que l'autre écrit en temps réel (lecture seule). Publication par double validation. Etherpad reporté à v0.4+.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Etherpad intégré | Temps réel, collaboratif | Dépendance lourde, complexité | Reporté à v0.4+ |
| Tour par tour strict | Structure claire | Rigide, lent | Bride la créativité |
| Champ unique partagé | Simple | Conflits d'édition | Mauvaise UX |

## Consequences

- Modèle : SharedSequence contient N entrées (type messages) avec auteur et contenu
- WebSocket ou polling pour la mise à jour en temps réel
- Double validation requise : les deux joueurs cliquent "publier"
- Cross-instance : hébergé sur l'instance du créateur du PNJ
