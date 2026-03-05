# PROJECT_BRIEF.md

## Executive Summary

- **Project Name**: Suddenly
- **Vision**: Un réseau fédéré où les PNJ des uns deviennent les PJ des autres
- **Mission**: Plateforme ActivityPub de partage de comptes-rendus de parties de JDR, permettant aux personnages de traverser les campagnes via des mécaniques de claim/adopt/fork

### Full Description

Suddenly est un réseau social fédéré (ActivityPub) pour joueurs de jeux de rôle. Les joueurs publient des comptes-rendus de parties mentionnant des personnages. Ces personnages (d'abord PNJ) peuvent être réclamés, adoptés ou dérivés par d'autres joueurs pour devenir leurs propres PJ.

## Context

### Core Domain

Plateforme fédérée TTRPG : chaque instance est autonome mais peut interopérer avec les autres via ActivityPub (compatible Mastodon). Les personnages constituent le lien entre les instances et les joueurs.

### Ubiquitous Language

| Term | Definition | Synonymes |
| ---- | ---------- | --------- |
| PJ | Personnage Joueur — appartient à un joueur | PC |
| PNJ | Personnage Non-Joueur — créé dans un compte-rendu, disponible | NPC |
| Partie / Jeu | Fiction en cours recevant des comptes-rendus | Game, Campaign |
| Compte-rendu | Récit narratif d'une session de jeu (Markdown) | Report |
| Citation | Citation mémorable d'un personnage (public/privée/éphémère) | Quote |
| Claim | Rétcon : le PNJ était mon PJ depuis le début | — |
| Adopt | Reprise : le PNJ devient mon nouveau PJ | — |
| Fork | Dérivation : nouveau PJ inspiré du PNJ, lien de lignée | — |
| Lien | Relation établie entre personnages après acceptation d'une demande | CharacterLink |
| Demande de lien | Requête pending claim/adopt/fork | LinkRequest |
| Séquence partagée | Contenu co-créé lors de l'établissement d'un lien | SharedSequence |
| Apparition | Lien entre un personnage et un compte-rendu | CharacterAppearance |
| Distribution | Cast planifié avant l'écriture d'un compte-rendu | ReportCast |
| Instance | Serveur Suddenly fédéré | — |

## Features & Use-cases

- Créer et gérer des jeux (fictions en cours) avec leurs comptes-rendus
- Mentionner des personnages dans les comptes-rendus (création automatique de PNJ)
- Envoyer des demandes de claim/adopt/fork sur les PNJ disponibles
- Accepter/refuser les demandes (rôle du créateur du PNJ)
- Suivre des utilisateurs, jeux et personnages (local et fédéré)
- Publier des citations mémorables de personnages (avec visibilité configurable)
- Fédération via ActivityPub : WebFinger, NodeInfo, inbox/outbox

## User Journey maps

```mermaid
journey
    title Suddenly — Parcours principaux
    section Game Master
        Crée un jeu: 5: GM
        Rédige un compte-rendu: 5: GM
        Mentionne des PNJ: 4: GM
        Reçoit une demande de lien: 3: GM
        Accepte ou refuse: 4: GM
    section Player
        Découvre des PNJ dans les comptes-rendus: 4: Player
        Envoie une demande adopt/claim/fork: 5: Player
        Reçoit l'acceptation: 5: Player
        Publie ses propres comptes-rendus: 5: Player
```

### Game Master

- Auteur principal des comptes-rendus
- Crée des PNJ via les mentions `@character` dans ses récits
- Arbitre les demandes de claim/adopt/fork sur ses PNJ

#### Créer une partie et publier un compte-rendu

Créer un jeu → Rédiger le compte-rendu avec mentions → Définir le cast (distribution) → Publier → Les PNJ sont disponibles pour adoption

### Player

- Joue dans des campagnes, cherche des PNJ à adopter/forker
- Peut avoir plusieurs PJ issus de PNJ de différents GMs

#### Adopter un PNJ

Parcourir les comptes-rendus → Trouver un PNJ → Envoyer demande adopt avec message → Attendre décision du GM → Si accepté : le PNJ devient son PJ
