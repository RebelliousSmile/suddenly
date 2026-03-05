# Decision: Migration de compte complète

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-003        |
| Date    | 2026-03-05     |
| Feature | Compte & Profil |
| Status  | Accepted       |

## Context

En fédération, les utilisateurs doivent pouvoir changer d'instance. Mastodon ne migre que le profil et les followers. Suddenly a plus de données liées au compte (parties, CRs, personnages, liens).

## Decision

Migration complète : profil, followers, parties, CRs, personnages (PJ), et liens. Tout le contenu suit le joueur sur la nouvelle instance.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Profil + followers only (Mastodon) | Simple | Perte de tout le contenu narratif | Inacceptable pour des joueurs investis |
| Export/import manuel | Pas de protocole inter-instance | UX terrible | Trop de friction |

## Consequences

- Protocole de migration custom au-delà de Move AP standard
- Complexité technique significative — post-MVP probable
- Les ap_id de tous les objets migrés doivent être réécrits
- Les instances distantes doivent mettre à jour leurs caches
