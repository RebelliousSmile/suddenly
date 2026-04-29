# 18 — CR complet : marqueurs de personnages et variantes

Complète `06-reports.md` avec le détail des statuts de personnages dans la distribution
et toutes les variantes d'affichage d'un CR.

---

## Légende des statuts de personnages

| Badge | Couleur | Statut | Description |
|-------|---------|--------|-------------|
| `[NPC]` | Vert | `npc` | PNJ du GM auteur — pas de lien |
| `[PC]` | Bleu | `pc` | PJ de l'auteur — pas de lien |
| `[⟵ claim]` | Violet | `claimed` | PNJ rétroactivement réclamé comme PC (retcon) |
| `[⟵ adopt]` | Émeraude | `adopted` | PNJ adopté comme PC par un autre joueur |
| `[⟵ fork]` | Ambre | `forked` | Nouveau PC dérivé/inspiré du PNJ |

## Légende des rôles de cast

| Icône | Rôle | `CastRole` |
|-------|------|------------|
| `★` | Principal | `main` |
| `·` | Secondaire | `supporting` |
| `○` | Mentionné | `mentioned` |

---

## CR complet — vue lecteur connecté (published, public)

```
+------------------------------------------------------------------+
|  HEADER — nav + badge notifs                                     |
+------------------------------------------------------------------+
|                                                                  |
|  City of Mist  ›  Session 14                         [Suivre v] |
|                                                                  |
|  L'Écho des Miroirs                                              |
|                                                                  |
|  +--------+  @alice  ·  Session du 12 avr. 2026                 |
|  | avatar |  publiée le 15 avr. 2026                            |
|  +--------+  (globe) Public                                      |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Distribution                                                    |
|                                                                  |
|  ★ Principaux                                                    |
|  +-------------------------------+  +-------------------------------+
|  | (av) Viktor          [NPC]   |  | (av) Lyra            [PC]   |
|  |      @alice · City of Mist  |  |      @alice                  |
|  |      Principal               |  |      Principal               |
|  +-------------------------------+  +-------------------------------+
|                                                                  |
|  · Secondaires                                                   |
|  +-------------------------------+  +-------------------------------+
|  | (av) Ombra      [⟵ claim]   |  | (av) Kael       [⟵ adopt]  |
|  |      @bob (retcon de @alice) |  |      @carol (adopté de      |
|  |      Secondaire              |  |       @alice) · Secondaire  |
|  +-------------------------------+  +-------------------------------+
|                                                                  |
|  ○ Mentionnés                                                    |
|  +-------------------------------+                                |
|  | (av) Sable       [⟵ fork]   |                                |
|  |      @dan (dérivé de Viktor) |                                |
|  |      Mentionné               |                                |
|  +-------------------------------+                                |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  La nuit tombait sur le Quartier des Reflets quand **Viktor**   |
|  poussa la porte du bar. L'Oracle l'attendait, ses yeux         |
|  brillant d'une lueur froide...                                  |
|                                                                  |
|  **Lyra** arriva par la porte de derrière, son manteau          |
|  ruisselant de pluie. Elle posa un dossier sur la table.        |
|  « Je ne suis pas venue pour négocier. »                        |
|                                                                  |
|  Dans l'ombre, **Ombra** observait la scène sans intervenir.    |
|  Son silence était éloquent.                                     |
|                                                                  |
|  (mention de **Sable** — absent mais évoqué dans le dialogue)   |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Citations de cette session                                      |
|                                                                  |
|  +---------------------------------------------------------+     |
|  | « Les mythes ne meurent pas, ils changent de visage. » |     |
|  |   — Viktor  ·  (lock) public  [Signaler] [♡ 3]         |     |
|  +---------------------------------------------------------+     |
|  | « Je ne suis pas venue pour négocier. »                 |     |
|  |   — Lyra  ·  (lock) public   [Signaler] [♡ 7]          |     |
|  +---------------------------------------------------------+     |
|                                                                  |
|  [+ Ajouter une citation]                                        |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  [♡ 12]  [↺ Recommander]  [⋯ Plus]                              |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Panneau détail d'un personnage lié (clic sur badge)

Clic sur `[⟵ adopt]` de Kael ouvre un panneau latéral ou tooltip :

```
+------------------------------------------+
| (av) Kael — @carol@soudainement.fr       |
|                                          |
| (adopt) Adopté depuis                    |
| (av) Kael (PNJ originel) — @alice       |
|      City of Mist · Session 8           |
|                                          |
| Demande acceptée le 20 mars 2026         |
|                                          |
| [Voir la fiche de Kael (@carol)]         |
| [Voir le PNJ originel]                   |
+------------------------------------------+
```

Clic sur `[⟵ fork]` de Sable :

```
+------------------------------------------+
| (av) Sable — @dan@suddenly.social        |
|                                          |
| (fork) Dérivé de                         |
| (av) Viktor (PNJ) — @alice              |
|      City of Mist                        |
|                                          |
| Fork accepté le 2 avril 2026             |
|                                          |
| [Voir la fiche de Sable]                 |
| [Voir Viktor (originel)]                 |
+------------------------------------------+
```

Clic sur `[⟵ claim]` d'Ombra :

```
+------------------------------------------+
| (av) Ombra — @bob@soudainement.fr        |
|                                          |
| (claim) Rétrocon — ce personnage était   |
| déjà le PC de @bob depuis le début.     |
|                                          |
| (av) Ombra (PNJ originel) — @alice      |
|      City of Mist · Session 1-7         |
|                                          |
| Claim accepté le 10 mars 2026            |
|                                          |
| [Voir la fiche d'Ombra (@bob)]           |
| [Voir l'historique des apparitions]      |
+------------------------------------------+
```

---

## Variante — CR avec Content Warning (vue feed)

Le CR est masqué dans le feed ; clic `[Afficher]` le déplie inline (Alpine.js) :

```
+------------------------------------------------------------+
| +------+  @alice · City of Mist              il y a 2h    |
| |avatar|  Session 14 : L'Écho des Miroirs                 |
| +------+                                                   |
|                                                            |
|  (alert-triangle) Violence, thèmes sombres                 |
|  [Afficher le contenu]                                     |
|                                                            |
+------------------------------------------------------------+
```

Vue détail avec CW — bandeau au-dessus du contenu :

```
+------------------------------------------------------------------+
|  [Distribution]  ← identique à la vue standard                  |
+------------------------------------------------------------------+
|                                                                  |
|  (alert-triangle) Avertissement : Violence, thèmes sombres       |
|  [Masquer le contenu]                                            |
|                                                                  |
|  La nuit tombait sur le Quartier des Reflets...                  |
|  (contenu visible car l'utilisateur a cliqué Afficher)          |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Variante — CR brouillon (vue auteur)

```
+------------------------------------------------------------------+
|  ⚠ Brouillon — non publié, non fédéré                           |
+------------------------------------------------------------------+
|                                                                  |
|  City of Mist  ›  Session 14 (brouillon)           [Modifier]   |
|                                                                  |
|  L'Écho des Miroirs                                              |
|                                                                  |
|  +--------+  @alice  ·  créé le 14 avr. 2026                   |
|  | avatar |  (clock) Brouillon                                  |
|  +--------+                                                      |
|                                                                  |
+------------------------------------------------------------------+
|  [Distribution]  ← identique                                     |
+------------------------------------------------------------------+
|  [contenu]                                                       |
+------------------------------------------------------------------+
|                                                                  |
|  [Publier]  [Modifier]  [Supprimer]                              |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Variante — CR non-listé (unlisted)

```
+------------------------------------------------------------------+
|                                                                  |
|  City of Mist  ›  Session 14                                     |
|                                                                  |
|  L'Écho des Miroirs                                              |
|                                                                  |
|  +--------+  @alice  ·  Session du 12 avr. 2026                 |
|  | avatar |  (unlock) Non-listé — accessible par lien direct    |
|  +--------+  (non visible dans les fils d'actualité)            |
|                                                                  |
+------------------------------------------------------------------+
|  [Distribution + contenu identiques]                             |
+------------------------------------------------------------------+
```

Pas de bouton `[↺ Recommander]` dans la barre d'actions.

---

## Variante — CR abonnés seulement (followers-only)

```
+------------------------------------------------------------------+
|                                                                  |
|  L'Écho des Miroirs                                              |
|                                                                  |
|  +--------+  @alice  ·  Session du 12 avr. 2026                 |
|  | avatar |  (lock) Abonnés seulement                           |
|  +--------+                                                      |
|                                                                  |
+------------------------------------------------------------------+
```

**Vue visiteur non-abonné** — le contenu est caché, seul le résumé/titre est visible :

```
+------------------------------------------------------------------+
|                                                                  |
|  L'Écho des Miroirs                                              |
|  (lock) Ce contenu est réservé aux abonnés de @alice.           |
|                                                                  |
|  [Suivre @alice]                                                 |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Variante — CR distant/fédéré (autre instance)

```
+------------------------------------------------------------------+
|                                                                  |
|  City of Mist  ›  Session 14  · (globe) suddenly.social         |
|                                                                  |
|  L'Écho des Miroirs                                              |
|                                                                  |
|  +--------+  @alice@suddenly.social  ·  15 avr. 2026            |
|  | avatar |  (globe) Public · Instance distante                  |
|  +--------+                                                      |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Distribution                                                    |
|                                                                  |
|  ★ +----------------------------+  +----------------------------+|
|    | (av) Viktor       [NPC]   |  | (av) Ombra    [⟵ claim]  ||
|    |      @alice@suddenly.social|  |      @bob@suddenly.social  ||
|    |      (globe) distant       |  |      (globe) distant        ||
|    +----------------------------+  +----------------------------+|
|                                                                  |
|  (info) Les personnages liés (claim/adopt/fork) sont affichés   |
|  tels que fournis par l'instance distante. Les demandes de lien |
|  cross-instance sont disponibles via [Lier à mon histoire].     |
|                                                                  |
+------------------------------------------------------------------+
|  [contenu + citations identiques]                                |
+------------------------------------------------------------------+
|                                                                  |
|  [♡ 12]  [↺ Recommander]  [⋯ Plus]                              |
|  [Lier à mon histoire]  ← disponible pour NPC/claimed distants  |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Variante — vue auteur (CR publié)

```
+------------------------------------------------------------------+
|                                                                  |
|  L'Écho des Miroirs                                    [Modifier]|
|                                                                  |
|  +--------+  @alice  ·  Session du 12 avr. 2026                 |
|  | avatar |  (globe) Public  ·  (check) Fédéré                  |
|  +--------+                                                      |
|                                                                  |
+------------------------------------------------------------------+
|  [Distribution]  ← idem, sans le bouton [Lier à mon histoire]   |
+------------------------------------------------------------------+
|  [contenu]                                                       |
+------------------------------------------------------------------+
|                                                                  |
|  [♡ 12]  [↺ 3 recommandations]  [Modifier]  [Supprimer]         |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Matrice visibilité × actions disponibles

| Visibilité | [↺ Recommander] | [Lier] | Fédéré | Dans le feed |
|-----------|----------------|--------|--------|--------------|
| Public | ✓ | ✓ (NPC distants) | ✓ | ✓ |
| Non-listé | — | ✓ | ✓ | — |
| Abonnés | — | — | ✓ (followers) | ✓ (followers) |
| Brouillon | — | — | — | — |
