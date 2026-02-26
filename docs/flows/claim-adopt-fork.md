# Flows — Claim / Adopt / Fork

Les trois types de liens narratifs qui constituent le cœur de Suddenly.

---

## Vue d'ensemble

| Type | Signification | Résultat | PNJ original |
|------|--------------|----------|--------------|
| **Claim** | "Ce PNJ était mon PJ depuis le début" — rétcon | PNJ remplacé par le PJ existant | Remplacé |
| **Adopt** | "Je reprends ce PNJ comme mon PJ" — transfert | PNJ devient le PJ du demandeur | Transféré |
| **Fork** | "Mon PJ est inspiré de ce PNJ" — dérivation | Nouveau PJ lié, PNJ reste intact | Conservé |

---

## Flow Adopt (le plus courant)

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

    Bob->>System: Rédige scène narrative (début)
    Alice->>System: Complète la scène
    System->>System: SharedSequence publiée

    Note over System: Viktor.status = ADOPTED
    Note over System: Viktor.owner = Bob
```

## Flow Claim (rétcon)

```mermaid
sequenceDiagram
    participant Bob
    participant System
    participant Alice

    Note over Bob: Bob a un PJ "Marcus" depuis longtemps
    Bob->>System: Voit PNJ "Viktor" d'Alice
    Bob->>System: Claim Request: "Viktor = Marcus depuis le début"
    Bob->>System: Désigne son PJ Marcus comme "proposed_character"
    System->>Alice: Notification Claim

    Alice->>System: Accepte le rétcon

    System->>System: CharacterLink (Claim) créé
    System->>System: Viktor.status = CLAIMED
    Note over System: Viktor remplacé par Marcus dans les CRs partagés
    System-->>Bob: Demande SharedSequence (scène du "dévoilement")

    Bob->>System: Rédige scène du dévoilement
    Alice->>System: Complète la scène
    System->>System: SharedSequence publiée
```

## Flow Fork (dérivation)

```mermaid
sequenceDiagram
    participant Bob
    participant System
    participant Alice

    Bob->>System: Voit PNJ "Viktor" d'Alice
    Bob->>System: Fork Request + relation ("frère jumeau", "successeur", etc.)
    System->>Alice: Notification Fork

    Alice->>System: Accepte (optionnel pour Fork)

    System->>System: Nouveau Character créé pour Bob
    System->>System: CharacterLink (Fork) créé
    Note over System: Viktor.status reste NPC
    Note over System: Nouveau PJ de Bob lié à Viktor via Fork
    System-->>Bob: Demande SharedSequence (scène de rencontre)

    Bob->>System: Rédige scène de rencontre/révélation
    Alice->>System: Complète la scène
    System->>System: SharedSequence publiée
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

## Statuts Character

```mermaid
stateDiagram-v2
    [*] --> NPC : Créé dans un CR
    NPC --> CLAIMED : Claim accepté (PNJ remplacé)
    NPC --> ADOPTED : Adopt accepté (PNJ transféré)
    NPC --> FORKED : Fork accepté (PNJ conservé)
    CLAIMED --> [*] : PJ source reste, PNJ remplacé
    ADOPTED --> [*] : PNJ devient PJ
    FORKED --> NPC : PNJ original inchangé
```

## SharedSequence — Règle MVP

**Un lien sans SharedSequence est invalide.**

La séquence partagée est la scène narrative co-écrite par les deux joueurs qui justifie le lien. Elle est obligatoire pour tous les types (Claim, Adopt, Fork).

```
Workflow SharedSequence:
1. Lien accepté → notification aux deux joueurs
2. Initiateur rédige sa partie de la scène (Markdown)
3. Accepteur complète la scène
4. Les deux valident → publication sur les deux instances
5. La SharedSequence apparaît dans les deux parties concernées
```
