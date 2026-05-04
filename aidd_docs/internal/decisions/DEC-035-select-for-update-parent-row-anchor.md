---
name: DEC-035-select-for-update-parent-row-anchor
description: Verrouiller la ligne parente comme ancre atomique pour les patterns check-then-create
type: decision
---

# Decision: select_for_update() sur la ligne parente comme ancre atomique

| Field   | Value                        |
| ------- | ---------------------------- |
| ID      | DEC-035                      |
| Date    | 2026-05-04                   |
| Feature | Liens / LinkRequest queue    |
| Status  | Accepted                     |

## Context

Pour éviter les race conditions dans les patterns "vérifier puis créer" (ex. : vérifier qu'aucun PENDING n'existe avant de créer une demande), il faut un verrou DB. En PostgreSQL READ COMMITTED (défaut Django), `select_for_update()` sur un queryset vide ne verrouille rien : deux transactions concurrentes peuvent toutes deux passer la vérification et créer un doublon.

## Decision

Toujours verrouiller la **ligne parente** comme ancre de transaction plutôt que le queryset vérifié :

```python
@transaction.atomic
def create_request(cls, ..., target_character: Character, ...) -> LinkRequest:
    locked_char = Character.objects.select_for_update().get(pk=target_character.pk)
    has_pending = LinkRequest.objects.filter(
        target_character=locked_char, status=LinkRequestStatus.PENDING
    ).exists()
    status = LinkRequestStatus.QUEUED if has_pending else LinkRequestStatus.PENDING
    ...
```

Le verrou sur `locked_char` bloque toute transaction concurrente qui tente la même vérification sur le même PNJ.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| `select_for_update()` sur le queryset PENDING | Intuitif | Verrou nul si queryset vide (READ COMMITTED) | Ne protège pas la race condition |
| Contrainte DB UNIQUE sur `(target_character, PENDING)` | Garantie absolue | Impossible : plusieurs QUEUED autorisés sur même NPC | Incompatible avec le modèle de file |

## Consequences

- Toute opération "check-then-create" sur un agrégat doit verrouiller la ligne racine de l'agrégat
- Légère contention possible sous forte charge sur un même PNJ populaire (acceptable)
