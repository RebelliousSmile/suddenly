# Decision: Suppression de compte modèle Mastodon

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-002        |
| Date    | 2026-03-05     |
| Feature | Compte & Profil |
| Status  | Accepted       |

## Context

Quand un joueur supprime son compte, il faut définir le sort de ses personnages, parties et CRs. Les PNJ créés par ce joueur peuvent avoir été adoptés par d'autres.

## Decision

Modèle Mastodon : les PNJ adoptés restent chez leur nouveau propriétaire, les PNJ non-liés sont supprimés avec le compte. Un Tombstone AP est émis pour la fédération.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Anonymiser tous les PNJ | Préserve le contenu | PNJ orphelins sans contexte | Données fantômes inutiles |
| Anonymiser et garder disponibles | Plus de PNJ adoptables | Incohérence narrative (créateur inconnu) | Complexité sans valeur claire |

## Consequences

- Les CharacterLink existants (Adopt/Claim) survivent à la suppression du créateur
- Les PNJ non-liés disparaissent — pas de données orphelines
- Les CRs et parties du joueur sont supprimés
- Les SharedSequences publiées restent (contenu co-créé)
