# Wireframes — Suddenly MVP

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
| `06-reports.md` | Liste CRs, detail CR, editeur CR + cast | US-04, US-05, US-13 |
| `07-characters.md` | Liste persos, fiche perso, recherche FTS | US-06, US-07 |
| `08-quotes.md` | Citations sur fiche perso, ajout citation | US-08 |
| `09-links.md` | Demande claim/adopt/fork, arbitrage, SharedSequence | US-09 a US-11, US-18-19 |
| `10-feed.md` | Fil d'actualite, follow/unfollow | US-12 |
| `11-notifications.md` | Centre de notifications | US-20, US-21 |

## Conventions

- `[Bouton]` = bouton cliquable
- `{champ}` = champ de formulaire
- `(icone)` = icone Lucide
- `| ... |` = tableau/grille
- `--- HTMX --->` = requete HTMX (partial swap)
- `@composant` = reference a un composant existant dans `templates/components/`
- Les wireframes sont en largeur desktop (1280px max). Le responsive suit les breakpoints UnoCSS standard.
