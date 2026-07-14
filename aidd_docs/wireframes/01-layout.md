# 01 — Layout global

## Header (sticky)

```
+------------------------------------------------------------------+
| (dice) Suddenly    Accueil  Explorer  Mes parties  Mes persos    |
|                                                                  |
|                               Dashboard*  (link)[2]  (bell)[3]  |
|                                            ^^^^^^^^  [avatar v]  |
+------------------------------------------------------------------+
                                 demandes     notifs
                                 actives       |
                                               v (dropdown Alpine.js)
                                         +------------------+
                                         | Mon profil       |
                                         | Mes demandes     |
                                         | Parametres       |
                                         | ──────────────── |
                                         | Deconnexion      |
                                         +------------------+
```

- **Dashboard** : visible si l'utilisateur a cree au moins une partie (GM)
- **(link)[2]** : compteur de demandes actives (envoyees en attente + recues a traiter).
  Clic -> `/requests/`. Badge visible seulement si > 0.
- **(bell)[3]** : compteur de notifications non lues. Clic -> `/notifications/`.

### Header visiteur (non connecte)

```
+------------------------------------------------------------------+
| (dice) Suddenly    Accueil  Explorer                             |
|                                                                  |
|                                    [Connexion]  [S'inscrire]     |
+------------------------------------------------------------------+
```

### Header mobile (< 768px)

```
+----------------------------------+
| (dice) Suddenly      (menu-ham)  |
+----------------------------------+
          |
          v (toggle Alpine.js)
+----------------------------------+
| Accueil                          |
| Explorer                         |
| Mes parties                      |
| Mes persos                       |
| ──────────────────────────────── |
| Mon profil                       |
| Deconnexion                      |
+----------------------------------+
```

## Flash messages

```
+------------------------------------------------------------------+
| (check-circle) Compte-rendu publie avec succes.            [x]  |
+------------------------------------------------------------------+

| (alert-triangle) Votre session expire bientot.              [x]  |
+------------------------------------------------------------------+

| (x-circle) Erreur lors de la sauvegarde.                    [x]  |
+------------------------------------------------------------------+
```

Couleurs : tokens `color.semantic.*` — `success`, `warning`, `danger` (et non `error`), `info`.
Un bandeau ne repose jamais sur la seule couleur : il porte toujours son icone et son libelle.

## Footer

```
+------------------------------------------------------------------+
|                                                                  |
|  (dice) Suddenly                                                 |
|  Reseau federe pour joueurs de JDR                               |
|                                                                  |
|  A propos  ·  Documentation  ·  GitHub                           |
|                                                                  |
+------------------------------------------------------------------+
```

## Toast notifications (coin bas-droite)

```
                                        +------------------------+
                                        | (bell) Nouvelle        |
                                        | demande d'Adoption sur |
                                        | Viktor                 |
                                        |              il y a 2s |
                                        +------------------------+
```

Apparait via HTMX polling ou SSE. Disparait apres 5s.

## Loading indicator (HTMX)

```
+==================================================================+  <- barre crimson 2px
| (contenu de la page)                                             |
```

Barre animee en haut de page pendant les requetes HTMX — token `color.brand.primary`
(la couleur d'action). Sous `prefers-reduced-motion`, l'animation est desactivee.
