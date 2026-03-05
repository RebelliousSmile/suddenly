# Flows — Claim / Adopt / Fork

| Type | Signification | Résultat | PNJ original |
|------|--------------|----------|--------------|
| **Claim** | "Ce PNJ était mon PJ depuis le début" — rétcon | PNJ remplacé par le PJ existant | Remplacé |
| **Adopt** | "Je reprends ce PNJ comme mon PJ" — transfert | PNJ devient le PJ du demandeur | Transféré |
| **Fork** | "Mon PJ est inspiré de ce PNJ" — dérivation | Nouveau PJ lié, PNJ reste intact | Conservé |

## Statuts Character

```mermaid
stateDiagram-v2
    [*] --> NPC : Créé dans un CR
    NPC --> CLAIMED : Claim accepté (PNJ remplacé)
    NPC --> ADOPTED : Adopt accepté (PNJ transféré)
    NPC --> FORKED : Fork accepté (PNJ conservé)
```

## Flow Adopt

```mermaid
sequenceDiagram
    participant Bob
    participant System
    participant Alice

    Bob->>System: Voit PNJ "Viktor" dans un CR d'Alice
    Bob->>System: Envoie Adopt Request + message narratif
    System->>Alice: Notification "Bob veut adopter Viktor"
    Alice->>System: Accepte avec réponse narrative
    System->>System: Crée CharacterLink (Adopt)
    System->>Bob: Viktor est maintenant ton PJ
    System-->>Bob: Demande SharedSequence
    Note over System: Viktor.status = ADOPTED, Viktor.owner = Bob
```

## Flow Cross-Instance (fédération)

```mermaid
sequenceDiagram
    participant Bob as Bob (instance B)
    participant InstanceB as Suddenly B
    participant InstanceA as Suddenly A
    participant Alice as Alice (instance A)

    Bob->>InstanceB: Envoie Adopt Request pour Viktor
    InstanceB->>InstanceA: POST /users/alice/inbox (Offer activity)
    InstanceA->>Alice: Notification
    Alice->>InstanceA: Accepte
    InstanceA->>InstanceB: POST /users/bob/inbox (Accept activity)
    InstanceB->>Bob: Viktor adopté!
    Note over InstanceA,InstanceB: HTTP Signatures sur toutes les requêtes
```

## SharedSequence — Règle MVP

**Un lien sans SharedSequence est invalide.**

```
1. Lien accepté → notification aux deux joueurs
2. Initiateur rédige sa partie (Markdown)
3. Accepteur complète la scène
4. Les deux valident → publication sur les deux instances
5. SharedSequence visible dans les deux parties concernées
```
