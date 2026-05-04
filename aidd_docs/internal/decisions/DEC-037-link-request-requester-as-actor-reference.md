---
name: DEC-037-link-request-requester-as-actor-reference
description: Utiliser link_request.requester plutôt que source.owner pour identifier l'acteur d'un lien
type: decision
---

# Decision: link_request.requester comme référence fiable à l'acteur d'un lien

| Field   | Value                  |
| ------- | ---------------------- |
| ID      | DEC-037                |
| Date    | 2026-05-04             |
| Feature | Liens / Révocation     |
| Status  | Accepted               |

## Context

Pour notifier l'autre partie lors d'une révocation, il faut identifier le joueur qui a établi le lien. `CharacterLink.source.owner` semble naturel, mais pour les liens de type ADOPT, `source == target` (le PNJ lui-même devient le PC) et `owner` peut ne pas être renseigné. `source.owner` est donc un champ fragile selon le type de lien.

## Decision

Toujours utiliser `link.link_request.requester` pour identifier le joueur ayant initié un lien — c'est le champ canonique, toujours défini quel que soit le type (claim, adopt, fork).

```python
recipient = (
    link.link_request.requester
    if actor == link.target.creator
    else link.target.creator
)
```

S'assurer que `link_request__requester` est préchargé via `select_related` avant l'appel au service.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| `link.source.owner` | Intuitif | None pour ADOPT (source == target, owner non garanti) | Crash silencieux |

## Consequences

- Tout code accédant à "l'autre partie" d'un lien doit passer par `link.link_request.requester`
- Requiert `select_related("link_request__requester")` dans les querysets qui appellent des services de révocation
