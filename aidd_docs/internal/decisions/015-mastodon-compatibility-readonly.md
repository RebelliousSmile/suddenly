# Decision: Compatibilité Mastodon read-only

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-015        |
| Date    | 2026-03-05     |
| Feature | Fédération     |
| Status  | Accepted       |

## Context

US-24 veut que les CR et citations soient visibles depuis Mastodon. La question est de savoir si Mastodon peut aussi interagir (commenter, liker).

## Decision

Read-only : les utilisateurs Mastodon voient les CR (Article) et citations (Note) dans leur fil, mais ne peuvent pas commenter ni interagir avec les fonctionnalités Suddenly.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Bidirectionnel | Engagement accru | Commentaires Mastodon mélangés au gameplay | Confusion entre social et narratif |
| Pas de compatibilité | Simplicité | Pas de visibilité externe | Perd l'effet réseau du Fediverse |

## Consequences

- Les Like/Announce de Mastodon sont ignorés (ou comptés silencieusement)
- Les Reply de Mastodon ne créent pas de contenu dans Suddenly
- Les CR sont formatés pour être lisibles dans un client Mastodon standard
