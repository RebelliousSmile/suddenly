# Wireframes — Suddenly

**Date** : 2026-04-05
**Design system** : UnoCSS + HTMX + Alpine.js
**Palette** : Primary (Indigo), Secondary (Emerald), Accent (Amber)

## Index des wireframes

| Fichier | Pages couvertes | User Stories |
|---------|----------------|--------------|
| `01-layout.md` | Header, footer, navigation, flash messages | — |
| `02-home.md` | Page d'accueil (visiteur + connecte) | — |
| `03-auth.md` | Login, signup, logout | US-01 |
| `04-profile.md` | Profil public, edition profil | US-01 |
| `05-games.md` | Liste parties, detail partie, creation partie | US-02, US-03 |
| `06-reports.md` | Detail CR, editeur CR + cast + @mentions | US-04, US-05, US-13 |
| `18-report-character-links.md` | CR complet : marqueurs NPC/PC/claim/adopt/fork, toutes variantes (CW, draft, unlisted, followers, distant, auteur) | US-04, US-05, US-09 a US-11 |
| `07-characters.md` | Liste FTS, fiche perso, variantes (PJ, fork, distant, revoque) | US-06, US-07, US-17, US-22 |
| `08-quotes.md` | Citations sur fiche perso, ajout HTMX | US-08 |
| `09-links.md` | Modals claim/adopt/fork, file d'attente, revocation, cross-instance, SharedSequence | US-09 a US-11, US-15, US-16, US-18-19, US-23 |
| `10-feed.md` | Fil d'actualite, bouton follow, page explorer | US-12 |
| `11-notifications.md` | Centre de notifications, badge, parametres canal | US-20, US-21 |
| `12-gm-dashboard.md` | Dashboard GM, vue "Mes PNJ", arbitrage inline | US-14 |
| `13-admin.md` | Dashboard admin, signalements, gestion instances | US-25, US-26 |
| `14-federation.md` | Recherche federee, profil distant, rendu Mastodon, NodeInfo/WebFinger | US-22, US-24 |
| `15-settings.md` | Compte, securite, langues, federation, donnees, migration | US-02 (deletion) |
| `16-misc.md` | Onboarding 3 etapes, modal signalement, pages erreur (404/403/500) | US-27 |

## Couverture par persona

| Persona | Wireframes | Couverture |
|---------|-----------|------------|
| **Joueur solo** | 01-11, 14-16 | Complet — inscription, profil, parties, CRs, persos, citations, liens, feed, notifs, recherche federee, settings, onboarding |
| **Game Master** | 06, 09, 12 | Complet — editeur cast, arbitrage demandes (page + inline), dashboard GM, vue PNJ avec file d'attente |
| **Admin d'instance** | 13 | Complet — moderation, signalements, gestion instances (bloquer/limiter/federer) |
| **Habituee du Fediverse** | Audit : `PERSONA_FEDIVERSE_AUDIT.md` | 10 manques identifies, 2 critiques (boost, visibilite CRs) |

## Couverture des User Stories (33 US)

Issues GitHub : rebellioussmile/suddenly#30 a #62

| US | Titre | Wireframe | Tache MP | Issue |
|----|-------|-----------|----------|
| US-01 | Creer mon compte | 03, 04 | T9, T11 | #30 |
| US-02 | Creer ma campagne | 05 | T19 | #31 |
| US-03 | Reconstituer campagne passee | 05 | T19 | #32 |
| US-04 | Ecrire et publier un CR | 06 | T20 | #33 |
| US-05 | Mentionner des personnages | 06 | T20 | #34 |
| US-06 | Voir la fiche d'un personnage | 07 | T14 | #35 |
| US-07 | Rechercher des personnages | 07 | T13, T14 | #36 |
| US-08 | Ajouter une citation | 08 | T15 | #37 |
| US-09 | Etre notifie d'une demande | 09, 11 | T16, T22 | #38 |
| US-10 | Envoyer une demande (flow guide) | 09 | T16 | #39 |
| US-11 | Accepter ou refuser | 09 | T16 | #40 |
| US-12 | Suivre une partie ou un joueur | 10 | T18 | #41 |
| US-13 | Planifier la distribution | 06 | T20 | #42 |
| US-14 | Arbitrer les demandes | 09, 12 | T16, T21 | #43 |
| US-15 | File d'attente QUEUED | 09 | T16 | #44 |
| US-16 | Revoquer un lien | 07, 09 | T16 | #45 |
| US-17 | Derivation en chaine | 07 | T14 | #46 |
| US-18 | Co-ecrire SharedSequence | 09 | T17 | #47 |
| US-19 | Valider et publier Sequence | 09 | T17 | #48 |
| US-20 | Notifications in-app | 11 | T22 | #49 |
| US-21 | Preferences de notification | 11 | T22 | #50 |
| US-22 | Suivre cross-instance | 14 | T25 | #51 |
| US-23 | Demande cross-instance | 09, 14 | T25 | #52 |
| US-24 | Voir depuis Mastodon | 14 | T25 | #53 |
| US-25 | Moderer le contenu | 13 | T30 | #54 |
| US-26 | Bloquer/limiter instance | 13 | T30 | #55 |
| US-27 | Signaler un contenu | 16 | T24 | #56 |
| **US-28** | **Recommander + inviter** | **10** | **T18** | **#57** |
| **US-29** | **Visibilite CR** | **06** | **T7, T20** | **#58** |
| **US-30** | **Content Warning (CW)** | **06, 08** | **T7, T15, T20** | **#59** |
| **US-31** | **Page A propos instance** | **17** | **T10** | **#60** |
| **US-32** | **Import/export + migration** | **15** | **T26, T28** | **#61** |
| **US-33** | **Block/mute utilisateur** | **15** | **T27** | **#62** |

## Conventions

- `[Bouton]` = bouton cliquable
- `{champ}` = champ de formulaire
- `(icone)` = icone Lucide
- `| ... |` = tableau/grille
- `--- HTMX --->` = requete HTMX (partial swap)
- `@composant` = reference a un composant existant dans `templates/components/`
- Les wireframes sont en largeur desktop (1280px max). Le responsive suit les breakpoints UnoCSS standard.
