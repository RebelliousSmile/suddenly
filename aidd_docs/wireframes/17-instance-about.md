# 17 — Page A propos de l'instance

## Page publique (`/about/`)

Accessible depuis le footer, la home visiteur et le header.

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  A propos de {{ SITE_NAME }}                                     |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Description                                                     |
|                                                                  |
|  {{ SITE_DESCRIPTION }}                                          |
|  (texte libre, configure par l'admin dans le panneau admin)      |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Statistiques                                                    |
|                                                                  |
|  +------------+ +------------+ +------------+ +------------+    |
|  | (users)    | | (book-open)| | (users)    | | (globe)    |    |
|  | 142        | | 1 247      | | 891        | | 14         |    |
|  | joueurs    | | CRs publies| | personnages| | instances  |    |
|  +------------+ +------------+ +------------+ +------------+    |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Regles de l'instance                                            |
|                                                                  |
|  1. Respectez les autres joueurs et leurs creations              |
|  2. Pas de contenu haineux, discriminatoire ou harcelant         |
|  3. Utilisez les Avertissements de Contenu pour les themes       |
|     sensibles (violence, contenu mature)                          |
|  4. Pas de spam ni de publicite non sollicitee                   |
|  5. Le contenu genere par IA doit etre clairement identifie     |
|                                                                  |
|  (texte libre, configure par l'admin)                            |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Administration                                                  |
|                                                                  |
|  +------+  @admin — Administrateur                               |
|  |avatar|  admin@suddenly.social                                 |
|  +------+  (envelope) Contacter l'admin                          |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Federation                                                      |
|                                                                  |
|  Logiciel : Suddenly 0.1.0                                       |
|  Protocole : ActivityPub                                         |
|  Compatible avec : Mastodon, BookWyrm, Lemmy, Pleroma            |
|                                                                  |
|  Instances federees : 14                                         |
|  Instances bloquees : 1                                          |
|                                                                  |
|  [Voir les instances connues ->]                                 |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Apercu de l'activite locale                                     |
|                                                                  |
|  @feed_item — dernier CR public                                  |
|  @feed_item — avant-dernier CR public                            |
|  @feed_item — ...                                                |
|                                                                  |
|  [Voir la timeline locale ->]                                    |
|                                                                  |
+------------------------------------------------------------------+
|                         FOOTER                                   |
+------------------------------------------------------------------+
```
