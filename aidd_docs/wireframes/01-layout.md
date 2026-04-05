# 01 — Layout global

## Header (sticky)

```
+------------------------------------------------------------------+
| (dice) Suddenly    Accueil  Explorer  Mes parties  Mes persos    |
|                                                                  |
|                                          (cloche)  [avatar \/]   |
+------------------------------------------------------------------+
                                              |
                                              v (dropdown Alpine.js)
                                        +------------------+
                                        | Mon profil       |
                                        | Parametres       |
                                        | ──────────────── |
                                        | Deconnexion      |
                                        +------------------+
```

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

Couleurs : success=emerald, warning=amber, error=red, info=blue.

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
                                        | demande d'Adopt sur    |
                                        | Viktor                 |
                                        |              il y a 2s |
                                        +------------------------+
```

Apparait via HTMX polling ou SSE. Disparait apres 5s.

## Loading indicator (HTMX)

```
+==================================================================+  <- barre indigo 2px
| (contenu de la page)                                             |
```

Barre animee en haut de page pendant les requetes HTMX.
