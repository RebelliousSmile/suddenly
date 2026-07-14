# 13 — Administration d'instance (post-MVP)

> Ces wireframes couvrent les US-25, 26, 27 (persona Admin d'instance).
> Classees post-MVP dans le master plan mais documentees ici pour completude.

## Dashboard admin (`/admin-panel/`) — US-25

Distinct du Django admin (`/admin/`). Interface dediee a la moderation.

```
+------------------------------------------------------------------+
|                         HEADER (badge "Admin")                   |
+------------------------------------------------------------------+
|                                                                  |
|  Administration                                                  |
|                                                                  |
|  +---------------------------+  +---------------------------+    |
|  | (flag) Signalements       |  | (globe) Instances         |    |
|  |                           |  |                           |    |
|  |  5 en attente             |  |  12 federees              |    |
|  |  2 cette semaine          |  |  1 bloquee                |    |
|  |                           |  |  3 limitees               |    |
|  |  [Voir signalements ->]   |  |  [Gerer instances ->]     |    |
|  +---------------------------+  +---------------------------+    |
|                                                                  |
|  +---------------------------+  +---------------------------+    |
|  | (users) Utilisateurs      |  | (activity) Activite       |    |
|  |                           |  |                           |    |
|  |  142 inscrits             |  |  1.2k activites/jour     |    |
|  |  3 suspendus              |  |  98% locales             |    |
|  |                           |  |                           |    |
|  |  [Gerer utilisateurs ->]  |  |  [Journal d'activite ->] |    |
|  +---------------------------+  +---------------------------+    |
|                                                                  |
+------------------------------------------------------------------+
```

## Signalements (`/admin-panel/reports/`) — US-27

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Signalements                                                    |
|                                                                  |
|  Filtre: [En attente v]                                          |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (flag) #42 — Contenu inapproprie            il y a 3h      |  |
|  |                                                             |  |
|  |  Signale par : @alice                                      |  |
|  |  Cible : CR "Session 8" par @troll123                      |  |
|  |  Instance : locale                                          |  |
|  |                                                             |  |
|  |  Commentaire : "Description graphique non sollicitee"      |  |
|  |                                                             |  |
|  |  [Voir le contenu]  [Supprimer le contenu]                 |  |
|  |  [Avertir l'auteur]  [Suspendre le compte]                 |  |
|  |  [Classer sans suite]                                      |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (flag) #41 — Spam                           il y a 1j      |  |
|  |                                                             |  |
|  |  Signale par : @bob                                        |  |
|  |  Cible : Profil @spammer (instance : evil.social)          |  |
|  |  Instance : distante                                        |  |
|  |                                                             |  |
|  |  [Voir le profil]  [Bloquer l'instance evil.social]        |  |
|  |  [Transferer a l'instance distante]                        |  |
|  |  [Classer sans suite]                                      |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
```

## Action de moderation — modal suppression (US-25)

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Supprimer le contenu                                    |
|                                                          |
|  CR "Session 8" par @troll123                            |
|                                                          |
|  (alert) Le contenu sera masque (soft delete).           |
|  L'auteur sera notifie avec votre message.               |
|                                                          |
|  Raison de la suppression                                |
|  {______________________________________________________}|
|  {______________________________________________________}|
|                                                          |
|  [ ] Suspendre egalement le compte de @troll123          |
|                                                          |
|            [Confirmer la suppression]   Annuler           |
|                                                          |
+----------------------------------------------------------+
```

## Gestion des instances (`/admin-panel/instances/`) — US-26

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Instances federees                                              |
|                                                                  |
|  {Rechercher une instance...}                                    |
|                                                                  |
|  Filtre: [Toutes v]                                              |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  +------------------------------------------------------------+  |
|  | mastodon.social        Mastodon 4.2.1     (vert) Federee   |  |
|  | 12.4M utilisateurs     Derniere verif: il y a 2h           |  |
|  |                                  [Limiter]  [Bloquer]      |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | suddenly.games         Suddenly 0.1.0     (vert) Federee   |  |
|  | 84 utilisateurs        Derniere verif: il y a 1h           |  |
|  |                                  [Limiter]  [Bloquer]      |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | spam.zone              Pleroma 2.x        (rouge) Bloquee  |  |
|  | ? utilisateurs         Bloquee le 15 mars 2026             |  |
|  |                                  [Debloquer]               |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | edgy.social          Mastodon 4.1.0     (warning) Limitee  |  |
|  | 2.1k utilisateurs      Limitee le 10 mars 2026             |  |
|  |                                  [Debloquer]  [Bloquer]    |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
```

### Etats d'instance

| Etat | Badge | Effet |
|------|-------|-------|
| **Federee** | (vert) | Interactions normales |
| **Limitee** | (warning) | Contenu absent des fils publics, visible si suivi explicite |
| **Bloquee** | (rouge) | Toutes activites rejetees, contenu masque |

## Modal blocage instance

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Bloquer spam.zone                                       |
|                                                          |
|  (alert) Cette action :                                  |
|  - Rejettera toutes les activites entrantes              |
|  - Masquera le contenu existant de cette instance        |
|  - Empechera vos utilisateurs d'interagir avec elle      |
|                                                          |
|  Raison (journal interne)                                |
|  {______________________________________________________}|
|                                                          |
|            [Confirmer le blocage]   Annuler               |
|                                                          |
+----------------------------------------------------------+
```
