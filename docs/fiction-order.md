# Ordre de fiction des scènes

Une partie (`Game`) accumule des scènes (`Report`) au fil du temps. L'ordre dans
lequel elles sont **publiées** n'est pas l'ordre dans lequel l'histoire se **lit**.
Ce document explique le mécanisme qui matérialise l'ordre de fiction, pourquoi il
n'est pas `Meta.ordering`, et comment il traverse la fédération.

> Contributeur pressé : ne triez **jamais** l'ordre de fiction par `published_at`
> ni via un manager. L'ordre de fiction n'existe que par le service
> `fiction_thread(game)`.

## Deux axes orthogonaux

Une scène porte deux informations indépendantes :

| Axe | Champ source de vérité | Rôle |
| --- | --- | --- |
| **Lecture** | `previous_report` (FK auto-référentiel) | la scène qui précède dans le fil de lecture |
| **Chronologie** | `temporal_kind` + `temporal_anchor` + `temporal_label` | où la scène se situe dans la chronologie interne (flashback / flashforward) |

Les deux sont orthogonaux : une scène **flashback** reste **dans** le fil de lecture
(elle a un `previous_report`), elle est simplement étiquetée « antérieure » par
rapport à son ancre. Le lecteur la rencontre à sa place dans la chaîne ; le badge
lui dit qu'elle se déroule « avant ».

```
S1  ──▶  S2 (flashback, ancre = S1)  ──▶  S3
        « il y a dix ans »
```

`S2` se lit entre `S1` et `S3`, mais raconte un événement antérieur à `S1`.

## Pourquoi pas `Meta.ordering` ?

`previous_report` définit une **forêt**, pas un ordre total :

- une scène peut avoir **plusieurs suites** (`next_reports`) — ce sont des
  **bifurcations**, gratuites (aucune contrainte supplémentaire) ;
- plusieurs scènes racines (sans prédécesseur) peuvent coexister.

Un `Meta.ordering` est un tri linéaire sur des colonnes ; il ne peut pas exprimer
un arbre. `Report.Meta.ordering` reste donc **inchangé** (`session_date`,
`-published_at`, `-created_at`) pour l'admin et les listes plates. L'ordre de
fiction se calcule uniquement par un **parcours en profondeur mainline-first**
dans `suddenly/games/services.py` :

- `fiction_thread(game)` charge la forêt en une passe
  (`select_related("author")` + `prefetch_related("next_reports")`), construit
  l'adjacence en mémoire à partir de `previous_report_id`, puis fait le DFS. Le
  coût requêtes est **borné**, indépendant de la profondeur de l'arbre ;
- les enfants d'un nœud sont triés par `(branch_order, session_date, created_at)` :
  la **mainline** d'abord, les branches ensuite ;
- `set_previous(report, new_previous)` réécrit **exactement une arête** après
  validation des invariants ; en cas d'échec, rien n'est écrit.

### Invariants (validés dans le service, jamais dans le modèle)

- pas d'auto-référence (`previous_report != self`, `temporal_anchor != self`) ;
- pas de cycle dans la chaîne `previous_report` (remontée bornée) ;
- même partie (`previous_report.game == self.game`, idem ancre) ;
- `temporal_kind == normal` ⟺ ni ancre ni label ; une ancre/un label exige un
  `temporal_kind` non normal ;
- XOR local/remote (voir ci-dessous), doublé d'une `CheckConstraint` en base.

## Contrat de fédération

Le lien voyage en **IRI mou** : **aucun FK dur ne traverse la fédération**. Une
instance ne connaît pas la clé primaire d'une scène distante ; elle n'en connaît
que l'IRI (`ap_id`).

### Émission — `serialize_report()`

Sous le namespace `suddenly:` (déclaré au `@context`) :

- `suddenly:previousReport` = l'`ap_id` (distant) ou l'URL locale de la scène
  précédente, **sinon** l'IRI mou déjà stocké (`previous_report_iri`) ;
- `suddenly:temporalKind` / `suddenly:temporalAnchor` / `suddenly:temporalLabel`
  quand la scène n'est pas `normal`.

Les clés sont **omises** pour une scène non chaînée et chronologiquement normale :
une scène ordinaire reste un `Article` AP ordinaire, qu'un pair ignorant le
vocabulaire affiche sans rien casser.

### Réception — `_handle_create_report()`

Un `Create(Article)` distant est ingéré (idempotent par `ap_id` : un double POST
crée **une seule** scène), l'auteur distant résolu via `attributedTo`, la partie
distante via `context`. Puis la **résolution IRI→FK** :

- si l'IRI (`suddenly:previousReport` / `suddenly:temporalAnchor`) correspond à une
  scène déjà connue par `ap_id`, on **relie le FK** et on **vide l'IRI**
  correspondant — le FK *est* le lien, l'IRI n'était que le transport (respect du
  XOR : la `CheckConstraint` interdit d'avoir les deux) ;
- sinon on **écrit l'IRI seul** ; le FK reste nul.

Le bloc est **tolérant** : absent = no-op, malformé = ignoré, forme compacte
(`previousReport`) comme expansée (`suddenly:previousReport`) acceptées.

## Poids UI

- Ouverture d'une scène → partial `_fiction_previously.html` : « ← Précédemment :
  {titre} » + badge flashback/flashforward le cas échéant. Rien si aucun
  prédécesseur.
- Clôture → partial `_fiction_next.html` : « Suite → » listant la mainline puis les
  branches. Rien s'il n'y a aucune suite.
- La donnée reste sur `Report` ; les partials ne stockent **aucun id**, ils rendent
  le lien à partir des données préfetchées par la vue.

## Limites assumées

- **Résolution différée non rétroactive** : une scène ancre qui arrive *après* une
  scène qui la référence ne reconnecte pas rétroactivement le FK — l'IRI mou reste
  seul (et reste fédérable). Une reconnexion rétroactive est un travail ultérieur.
- **UI des branches minimale** : les bifurcations rendent la mainline d'abord ;
  l'ergonomie fine des branches est laissée ouverte.
- **Inférence de visibilité** en réception : `to`/`cc` → `visibility`, avec un
  défaut `public` tolérant.
