# 06 — Comptes-rendus (Reports)

## Detail CR (`/games/{slug}/reports/{id}/`) — US-04

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  City of Mist > Session 12                                      |
|                                                                  |
|  L'Oracle brise                                                  |
|                                                                  |
|  +--------+ Alice  ·  publie le 15 mars 2026                    |
|  | avatar |                                                      |
|  +--------+                                                      |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Distribution                                                    |
|                                                                  |
|  [Viktor (PNJ)] [Lyra (PJ)] [Ombra (PNJ)] [Kael (reclame)]    |
|   (vert)         (bleu)      (vert)         (ambre)             |
|   Principal      Principal   Secondaire     Mentionne           |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  (contenu Markdown rendu en prose)                               |
|                                                                  |
|  La nuit tombait sur le Quartier des Reflets quand               |
|  **Viktor** poussa la porte du bar. L'Oracle l'attendait,       |
|  assis dans l'ombre, ses yeux brillant d'une lueur...            |
|                                                                  |
|  Lyra arriva par la porte de derriere, son manteau              |
|  ruisselant de pluie. Elle posa un dossier sur la table...      |
|                                                                  |
|  (...)                                                           |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Citations de cette session                                      |
|                                                                  |
|  @quote_card — "Les mythes ne meurent pas..." — Viktor          |
|  @quote_card — "Je ne suis pas venue pour negocier" — Lyra      |
|                                                                  |
|  [+ Ajouter une citation]  --- HTMX ---> _quote_form.html       |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  (heart) 4   (message-square) 2   (share) Partager              |
|                                                                  |
+------------------------------------------------------------------+
```

## Editeur CR (`/games/{slug}/reports/new/`) — US-04, US-05, US-13

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Nouveau compte-rendu — City of Mist                             |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Distribution (cast)                                    US-13    |
|                                                                  |
|  +----------------------------------------------------+         |
|  | {Ajouter un personnage...}                          |         |
|  +----------------------------------------------------+         |
|        |                                                         |
|        v  (Alpine.js dropdown, fetch API)                        |
|  +----------------------------------------------------+         |
|  | (avatar) Viktor — PNJ, City of Mist                 |         |
|  | (avatar) Lyra — PJ de @bob                          |         |
|  | (plus) Creer "Kael" comme nouveau PNJ               |         |
|  +----------------------------------------------------+         |
|                                                                  |
|  Personnages selectionnes :                                      |
|  [Viktor x] Role: [Principal v]                                  |
|  [Lyra   x] Role: [Principal v]                                  |
|  [Kael   x] Role: [Mentionne v]                                 |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Titre                                                           |
|  {_L'Oracle brise_____________________________________________}  |
|                                                                  |
|  Contenu (Markdown)                                              |
|  +------------------------------------------------------------+  |
|  | La nuit tombait sur le Quartier des Reflets quand           |  |
|  | @Viktor poussa la porte du bar.                             |  |
|  |                                                             |  |
|  | @Ly|                                                        |  |
|  |   +---------------------------+                             |  |
|  |   | (avatar) Lyra — PJ       |  <- mention autocomplete    |  |
|  |   | (avatar) Lyriel — PNJ    |     (Alpine.js)              |  |
|  |   +---------------------------+                             |  |
|  |                                                             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |  Avertissement de contenu (optionnel)                       |  |
|  |  {_Violence, themes sombres_______________________________} |  |
|  |  (info) Si rempli, le CR sera masque derriere un bouton     |  |
|  |  "Afficher le contenu" dans les fils d'actualite.           |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  Visibilite                                                      |
|  (o) (globe) Public — visible par tous, federe, dans les fils   |
|  ( ) (unlock) Non-liste — visible par lien, pas dans les fils   |
|  ( ) (lock) Abonnes — visible seulement par vos followers       |
|                                                                  |
|  [Publier]  [Sauvegarder brouillon]  [Supprimer]*               |
|                                                                  |
+------------------------------------------------------------------+
```

*`[Supprimer]` visible uniquement en mode edition.

### CR avec Content Warning dans le feed

Quand un CR a un avertissement de contenu, il est affiche replie :

```
+------------------------------------------------------------+
| +------+  @alice dans City of Mist          il y a 2h      |
| |avatar|                                                    |
| +------+  Session 12 : L'Oracle brise                      |
|                                                             |
|  (alert-triangle) Violence, themes sombres                  |
|  [Afficher le contenu]                                      |
|                                                             |
+------------------------------------------------------------+
```

Clic [Afficher le contenu] deplie le CR (Alpine.js toggle).

### Comportement HTMX

- Le champ de recherche de cast fait un `hx-get` vers `/htmx/characters/suggest/?q=...&game_id=...`
- La mention `@` dans le textarea declenche Alpine.js (pas HTMX) pour l'autocompletion
- `[Publier]` soumet le formulaire avec `status=published`
- `[Sauvegarder brouillon]` soumet avec `status=draft`

### Regles de visibilite

| Visibilite | Timeline Instance | Timeline Fediverse | Profil public | Federation AP |
|-----------|------------------|-------------------|--------------|--------------|
| Public | Oui | Oui | Oui | Create(Article) |
| Non-liste | Non | Non | Oui (direct link) | Create(Article) unlisted |
| Abonnes | Non | Non | Non | Create(Article) followers-only |
