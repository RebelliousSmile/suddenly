# DEC-038 — Format canonique de l'Offer fédéré (Claim / Adopt / Fork)

- **Date** : 2026-07-18
- **Statut** : Accepté (partiellement implémenté — voir *Reste à faire*)
- **Portée** : `suddenly/activitypub/` — réception des liens Claim/Adopt/Fork en fédération
- **Liés** : DEC-035 (transition de statut à l'acceptation), règles `08-activitypub.md`

## Contexte

Les liens Claim / Adopt / Fork se fédèrent via une activité ActivityPub de type `Offer`. En auditant le code, on a trouvé **deux implémentations parallèles de l'Offer qui avaient divergé**, au point de rendre la réception cross-instance non fonctionnelle.

### La divergence

| Rôle | Fichier | Forme produite / attendue | État |
|------|---------|---------------------------|------|
| Émission (vivante) | `serializers.py::serialize_link_request` | `object.type = "suddenly:Claim"`, cible dans `target` (top-level), message dans `object.content`, PJ dans `object.proposedCharacter` | branchée via signal `post_save` sur `LinkRequest` |
| Émission (morte) | `activities.py::build_offer_activity` | `object.type = "Relationship"` + `object.relationship` | **aucun appelant** |
| Réception | `inbox.py::handle_offer` | parsait la forme `Relationship` | branchée sur l'inbox HTTP |

L'émission suivait la 1ʳᵉ ligne, la réception attendait la 2ᵉ. Conséquences concrètes, telles que le code se lisait :

1. **Type non reconnu** : `handle_offer` faisait `if obj.get("type") != "Relationship": return` → un Offer réellement émis (`suddenly:Claim`) était rejeté d'emblée. Aucune `LinkRequest` créée côté récepteur.
2. **Cible introuvable** : la cible était lue dans `object.object`, alors qu'elle est en top-level `target`. De plus, la résolution se faisait par `ap_id`, or un personnage **local** n'a pas d'`ap_id` stocké (son actor_url est calculé) → jamais trouvé.
3. **Message perdu** : lu dans `activity.summary`, alors qu'il est dans `object.content`.

## Décision

**Le format émis par `serialize_link_request` est le format canonique.** Il est plus riche (types namespacés `suddenly:Claim/Adopt/Fork`, PJ proposé fédéré) et c'est celui qui circule réellement sur le fil.

- La réception (`handle_offer`) est réécrite pour parser ce format.
- Les trois builders morts de `activities.py` (`build_offer_activity`, `build_accept_activity`, `build_reject_activity`) sont **supprimés** pour éliminer la source de confusion. `build_follow_activity` (utilisé) reste.

### Contrat du format canonique

```json
{
  "@context": ["https://www.w3.org/ns/activitystreams", "…", {"suddenly": "https://suddenly.social/ns#"}],
  "type": "Offer",
  "id": "https://<instance>/link-requests/<pk>",
  "actor": "<actor_url du demandeur>",
  "target": "<actor_url du PNJ ciblé>",
  "object": {
    "type": "suddenly:Claim | suddenly:Adopt | suddenly:Fork",
    "content": "<message narratif>",
    "proposedCharacter": "<actor_url du PJ proposé — Claim uniquement>"
  }
}
```

### Règles de réception

- Mapping `object.type` → `LinkType` : `suddenly:Claim→CLAIM`, `suddenly:Adopt→ADOPT`, `suddenly:Fork→FORK`. Type inconnu → ignoré.
- Cible résolue par `_resolve_character_by_actor_url` : d'abord par `ap_id` (distant), sinon en parsant l'`actor_url` local (`{AP_BASE_URL}/characters/{pk}`). La cible doit être **locale**.
- Demandeur résolu via `get_or_create_remote_user`.
- `proposedCharacter` résolu **best-effort** (null si le PJ distant n'est pas encore connu localement).
- Invariant « un seul PENDING à la fois » préservé (miroir de `LinkService.create_request`) : un 2ᵉ Offer sur le même PNJ entre en `QUEUED`.

## Alternatives écartées

- **Aligner l'émission sur la forme `Relationship`** (`activities.py`) : régression fonctionnelle (perte des types namespacés et du PJ proposé), et il aurait fallu réécrire l'émission déjà en production. La forme `suddenly:X` est plus expressive et déjà émise.
- **Garder les deux parsers en réception** (compat ascendante `Relationship` + `suddenly:X`) : la forme `Relationship` n'a **jamais** été émise → aucun trafic à préserver. Code mort inutile.

## Conséquences

- ✅ Un Offer Claim/Adopt/Fork reçu reconstruit désormais une `LinkRequest` correcte (type, demandeur, PNJ cible, PJ proposé, message) côté instance de la cible.
- ✅ Garde-fou anti-régression : test **round-trip** `TestLinkOfferFederation.test_serialized_claim_offer_round_trips_into_a_link_request` — ce qu'on émet doit être ré-ingérable. Toute future divergence des deux chemins casse ce test.
- ⚠️ La réception **bypasse** `LinkService.create_request` (donc pas de `validate_claim`) : on fait confiance à la validation faite sur l'instance émettrice. Choix assumé pour la fédération.

## Reste à faire (hors périmètre de ce correctif — la boucle cross-instance complète)

Ce correctif règle la **réception de l'Offer**. La boucle Claim fédérée de bout en bout reste incomplète :

1. **Round-trip de l'id à l'Accept** : l'`id` de l'Offer est local à l'instance émettrice (`https://<instance>/link-requests/<pk>`). À l'acceptation, `send_accept_activity` renvoie un Accept référençant l'`id` de la **`LinkRequest` de l'instance qui accepte** — dont la PK n'existe pas sur l'instance du demandeur. `handle_accept` cherche par PK → `DoesNotExist` → l'Accept ne matche rien côté demandeur. À corriger (corréler par l'`id` de l'Offer d'origine, pas par la PK locale).
2. **Reconstruction d'état à l'Accept** : `handle_accept` se contente de flipper `LinkRequest.status`. Il ne rejoue **pas** `LinkService.accept_request` → côté demandeur, ni `CharacterLink`, ni `SharedSequence`, ni transition de statut ne sont reconstruits.
3. **Résolution du PJ distant** : pas encore de fetch d'un `Character` distant inconnu (`proposedCharacter` best-effort → null si absent).
4. **Doublon mort** : `tasks.py::handle_offer` (ligne ~171) est un no-op qui logge seulement — candidat à suppression pour lever l'ambiguïté avec `inbox.py::handle_offer`.

## Extrait normatif à propager

Ajouter à `.claude/rules/08-domain/08-activitypub.md` (contexte auto-chargé) :

- Format Offer canonique = `serialize_link_request` (`object.type = suddenly:Claim/Adopt/Fork`, cible en `target`, message en `object.content`, PJ en `object.proposedCharacter`).
- Réception via `inbox.py::handle_offer` uniquement ; ne jamais réintroduire la forme `Relationship`.
- Résoudre un personnage cible par `_resolve_character_by_actor_url` (ap_id distant, sinon parse de l'URL locale).
