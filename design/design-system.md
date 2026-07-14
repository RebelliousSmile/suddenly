---
version: 1.3.0
status: figé
source: app/templates/wireframes/maquette-v3.html (16 pages, extraction CSS)
derived_by: design:define → destructure → adjust
---

# Design system — Suddenly

> **Contrat figé.** Les trois couches font autorité : `tokens.json` (valeurs),
> `components.json` (vocabulaire fermé), ce document (charte). Le code consommateur a été
> migré et concorde — la réconciliation code ↔ manifeste (`adjust/02-freeze § 2bis`) est
> close. Toute évolution passe par un nouveau cycle `destructure` → `adjust`.

**Arbitrage fondateur : la maquette fait foi.** Là où le code divergeait, c'est le code qui a
convergé.

---

## 1. Fondations

### Ancre de palette — crimson sur neutres chauds

`#e03558` (crimson) est la couleur d'action unique. Elle ne décore pas : elle signale ce sur
quoi on peut cliquer, et le contenu cité. Elle est posée sur des neutres **chauds** (`#faf9f6`
fond, `#f0ede8` surface, blanc pour les cartes) — jamais sur du gris froid.

Le mode sombre n'est pas une inversion : c'est un **sépia**. Fond `#0b0705`, cartes `#25150e`,
bordures `#3d2215` — une chaleur de papier brûlé, avec des ombres qui deviennent des halos
crimson. Les couleurs sémantiques y sont remontées en clair pour rester lisibles.

**Les couleurs portent du sens métier.** Elles ne sont pas interchangeables :

| Rôle narratif | Couleur | Token |
|---|---|---|
| Personnage joueur (PJ), mention | indigo `#6366f1` | `color.domain.pc` |
| Personnage non-joueur (PNJ) | ambre `#b45309` | `color.domain.npc` |
| PNJ disponible — pastille, anneau, fond | néon `#00e676` | `color.domain.available` |
| PNJ disponible — **texte** | vert `#0a8f4d` | `color.domain.available-text` |
| Contenu fédéré / instance distante | violet `#7c3aed` | `color.domain.remote` |
| Fork, oracle | violet `#7c3aed` | `color.domain.forked`, `.oracle` |
| Claim en attente | bleu `#0369a1` | `color.domain.claimed` |
| Adoption acceptée | vert `#15803d` | `color.domain.adopted` |
| Citation | crimson | `color.domain.quoted` |

**Le néon ne porte jamais de glyphe** (contraste 1,6:1 sur fond clair). Cette règle est figée
et vérifiable : `usage.rules[signal-never-text]`. En mode sombre, la distinction disparaît —
sur le sépia, le néon vif est lisible, et `available-text` y est aliasé sur `available`.

Ces tokens sont des alias : changer `color.semantic.warning` déplace aussi la couleur des PNJ.
C'est délibéré, mais c'est un couplage à connaître avant de toucher aux sémantiques.

### Typographie — Fraunces pour la fiction, Inter pour l'application

- **Inter** — tout le chrome : navigation, boutons, badges, métadonnées, formulaires.
  Self-hostée en 400 / 500 / 600 / 700.
- **Fraunces** (serif à contraste élevé) — le corps de fiction : titres de récit, hero,
  descriptions, dialogues. **L'italique de Fraunces porte du sens** : elle marque la description
  narrative et distingue la voix du récit de la voix de l'interface.
  Self-hostée en **fonte variable** (`fraunces-var.woff2` + `fraunces-var-italic.woff2`,
  sous-ensemble latin, graisses 400–700, axe optique `opsz`) : un seul fichier par style couvre
  toute l'échelle, et le dessin s'adapte à la taille de rendu.

Les deux utilitaires `font-serif` et `font-display` pointent sur Fraunces — les usages
historiques de `font-serif` désignaient déjà exactement les endroits de fiction.

Règle figée (`usage.rules[display-font-is-fiction]`) : **jamais Fraunces pour du chrome, jamais
Inter pour de la narration.** La police est un signal de registre, pas une variation esthétique.

L'échelle mélange des pas fixes (12 → 28 px) et quatre pas **fluides** (`lede`, `h-sec`,
`h-page`, `hero`) en `clamp(… cqi …)`, indissociables du contexte de conteneur (cf. § 3).

### Icônes — trois jeux, trois rôles disjoints

Le contrat prévoyait « un jeu unique ». C'était faux et inapplicable : on ne redessine pas le
logo Mastodon en Lucide. La règle est donc une règle de **rôles**, pas de jeu unique
(`usage.rules[icon-set-roles]`) :

| Rôle | Jeu | Emploi | Interdit |
|---|---|---|---|
| `icon.sets.ui` | **Lucide** (152 icônes, 1520 usages) | **Toutes** les icônes d'interface, sans exception. Outline, `stroke-width: 2`, tailles 12/16/24 px | — |
| `icon.sets.brand` | **simple-icons** (2 icônes) | Uniquement les logos de plateformes et protocoles tiers : Mastodon, ActivityPub | Jamais une icône d'UI |
| `icon.sets.illustration` | **game-icons** (11 icônes, 31 usages) | Uniquement l'illustration décorative : états vides, évocation du registre JdR | Jamais un contrôle, jamais un statut |

**Une icône `brand` ou `illustration` ne porte jamais une action** — ni bouton, ni lien, ni badge
d'état. Ces deux jeux illustrent ; ils ne pilotent pas.

Lucide reste bien le jeu **unique de l'interface** : l'intention initiale est préservée, elle est
seulement énoncée correctement.

**Aucun emoji** comme icône, puce, pastille d'état ou glyphe de bouton (`usage.rules[no-emoji-as-icon]`).

**Nom accessible** (`usage.rules[icon-accessible-name]`) : une icône décorative porte
`aria-hidden="true"` ; une icône signifiante — celle qui remplace un mot — porte un `aria-label`.
Un bouton icon-only est toujours labellisé.

### Espace — pas de 2 px

L'échelle d'espacement est un **pas de 2 px** (`space.2` … `space.56`, les clés sont les
valeurs en pixels). C'est ce que la maquette fait réellement : ses valeurs dominantes sont 6,
10, 14, 18 et 22 px — une grille de 4 aurait déplacé presque tous les espacements.

**Conséquence côté UnoCSS : la clé `spacing` n'est pas surchargée.** L'échelle native d'Uno
(unité 0.25rem, avec demi-pas) produit exactement ce pas de 2 : `p-1.5` = 6px, `p-2.5` = 10px,
`p-3.5` = 14px. La remapper redéfinirait silencieusement `p-4` de 16px à 4px dans tous les
templates existants.

### Rayons, ombres, mouvement

Rayons par rôle : `md` (8px) pour les boutons et contrôles, `lg` (12px) pour cartes et menus,
`full` pour pastilles et avatars, `xs` (4px) pour les mentions inline.

Mouvement bref : 150 ms au survol, 200 ms sur changement d'état, 400 ms avec la courbe
`entrance` pour une apparition. **`prefers-reduced-motion` ramène toutes les durées à 0** — la
règle est portée par l'adapter, pas laissée à chaque composant.

---

## 2. Inventaire des composants

Les 17 composants ci-dessous ont une entrée dans `design/components.json` (couche 2), qui est
la source fermée et vérifiable. Cette section en donne l'intention ; elle ne la contredit
jamais.

**Chrome applicatif** — `app-header` (en-tête collant, z-50 : marque, navigation, contrôles),
`nav-drawer` (tiroir mobile sous 768px, `role="dialog"` + `aria-modal`), `icon-btn` (cible 44px,
`aria-label` obligatoire), `dropdown` (menu utilisateur, `aria-expanded`), `actionbar` (barre
d'action basse mobile, respect de `env(safe-area-inset-bottom)`).

**Identité** — `avatar` en trois tailles (34 / 44 / 64 px). L'anneau encode le statut du
personnage par la couleur **et par le style de trait** (`border.style.*`) : la couleur seule ne
suffit pas (ambre PNJ et néon disponible sont confondus en deutéranopie).

**Actions et signalement** — `btn` (`primary` / `secondary` / `ghost` / `danger`, plus `sm`,
`block`, `loading`, `disabled`), `badge` (les états du domaine, `role="status"` + `aria-label`),
`tabs`, `stat-card`.

**Conteneurs** — `card` (rayon 12px, ombre douce, ombre renforcée au survol ; `card__body` et
`card__footer` se réorganisent sous 640px ; variante `empty`).

**Le moteur de rendu narratif — le cœur du système.** `rap` rend les quatre types de rapports
par modificateur : `--narration` (récit neutre), `--description` (italique Fraunces), `--action`
(bordure gauche), `--discussion` (dialogue, taille augmentée en lecture). Deux modificateurs
transverses : `--reply` (réponse indentée) et `--quoted` (bordure crimson). Sous-parties :
`rap__replyto` (rappel du parent), `rap__qmark` (marqueur de citation). C'est le composant à
comprendre avant tous les autres.

**Édition** — `editor` (zone, barre d'outils, états `invalid` / `disabled` / `loading`,
`aria-invalid`), `form-field` (label, contrôle, indice, erreur), `mention` (+ `--npc`),
`scene-marker` (`--enter`, `--oracle`).

**Fiction et découverte** — `quote-card` (bordure gauche de 3px), `def` (infobulle de fiche
personnage au survol du nom, `aria-describedby`).

### États obligatoires

Tout composant interactif désigne ses états avant d'être implémenté : `default` / `hover` /
`focus` / `active` / `disabled` / `loading` / `error` / `empty`. Les trois composants critiques
— `btn`, `form-field`, `card` cliquable — les portent explicitement dans le manifeste. Sur un
produit où les actions (claim, adopt, fork) sont asynchrones, fédérées et refusables, l'état
d'attente n'est pas optionnel.

---

## 3. Layout et responsive — conteneurs, pas fenêtre

**La mise en page réagit à la largeur de son conteneur (`@container app`), pas à celle de la
fenêtre.** Le conteneur `app` est déclaré sur `<body>` (`container-type: inline-size`), et les
variantes s'écrivent `@sm:` / `@md:` / `@lg:` — jamais `sm:` / `md:` / `lg:`.

Tout composant réutilisable est donc posé **dans** un conteneur nommé. Un composant testé
isolément à 375px et le même composant dans une colonne de 375px rendent pareil.

### Deux pièges, tous deux vérifiés en production

**1. Les seuils sont des conditions, pas des largeurs.** Dans `theme.containers`, la valeur doit
être `'(min-width: 640px)'` et **jamais** `'640px'`. UnoCSS interpole la valeur telle quelle :
avec `'640px'` il produit `@container 640px{…}`, une at-rule **invalide** que le navigateur
ignore en silence. Le build reste vert, aucun avertissement — et tout le responsive s'effondre à
une seule colonne. C'est arrivé lors de la migration ; seule une mesure du DOM l'a révélé.

**2. Un conteneur mesure la largeur disponible, scrollbar déduite.** À un viewport de 768px, le
`<body>` ne fait que ~752px sur un navigateur à barre de défilement classique. `@md:` (768px) ne
se déclenche donc pas, là où `@media` se déclenchait. **Conséquence assumée** : sur desktop, une
fenêtre large de 768 à 784px affiche la mise en page mobile plutôt que tablette. Aucun effet sur
mobile et tablette réels, où les barres de défilement sont en superposition. C'est le
comportement correct d'une container query — pas un défaut à compenser par un décalage de 16px,
qui serait une valeur magique dépendante de la plateforme.

Le variant container query d'UnoCSS (0.62) est marqué **expérimental** : il n'est pas couvert par
le semver. Une montée de version doit être vérifiée par la mesure, pas par le build.

Largeurs maximales : 80rem (coque), 64rem (vues intermédiaires), 48rem (lecture), 42rem (texte
suivi).

Cibles tactiles : `size.tap` = 44px sur tout contrôle interactif. C'est un minimum, pas une
indication (`usage.rules[tap-target-min]`).

---

## 4. Accessibilité

**Focus.** Le groupe `focus.*` est figé : trait de 2px, `outline-offset` 2px, couleur
`color.semantic.focus` = indigo `#6366f1` (4,5:1). L'indigo plutôt que le crimson, pour ne pas
confondre « ceci a le focus » et « ceci est l'action primaire » — et parce que le crimson
n'atteint que 4,2:1. La maquette ne contenait **aucune** règle de focus : c'était un trou de
direction, pas un oubli d'intégration.

**Mouvement.** `prefers-reduced-motion: reduce` ramène `duration.fast|base|slow` à
`duration.instant`. Porté par `adapters/tokens.css`.

**Statut jamais par la couleur seule.** Un statut de personnage porte un token `color.domain.*`
**et** un libellé ou une icône ; l'anneau d'avatar ajoute un style de trait distinct
(`usage.rules[state-colour-icon]`).

**Contrastes.** Résolu au figeage : le néon (1,6:1) est dédoublé — `available` pour les
surfaces (seuil 3:1), `available-text` (`#0a8f4d`, 4,9:1) pour tout glyphe.

Restent sous le seuil AA, **non résolus au figeage** (cf. § 5) : crimson en texte (4,2:1), blanc
sur crimson (4,4:1), `semantic.muted` (3,2:1).

---

## 5. Open questions

**[non résolu au figeage — à traiter]** — `semantic.muted` (`#8c8c8c`) donne 3,2:1 sur le fond
clair, employé à des tailles de 12–13px. Un passage à `#6e6e6e` le porterait à 4,9:1 sans
changement perceptible de valeur. Non arbitré : la maquette fait foi, et personne n'a tranché.

**[non résolu au figeage — à traiter]** — crimson en texte (4,2:1) et blanc sur crimson (4,4:1)
échouent AA de peu. Passent en texte large / élément d'UI (seuil 3:1). Assombrir le crimson
d'action toucherait l'ancre de la palette : décision de marque, pas décision technique.

**Bordure lavande.** `#d4cfe8` sur une palette entièrement chaude est le seul élément froid du
système. Intentionnel, ou résidu d'une palette antérieure ?

**Chrome générique.** `destructure` a noté la direction 62/100 : distinctive là où c'est le
produit (moteur `rap`, sépia, italique signifiante), générique partout ailleurs. Sortir le
chrome du « SaaS de série » (filet net au lieu de l'ombre molle, Fraunces sur les titres de
section) est une piste ouverte, non arbitrée.

---

## 6. Provenance

### v1.2.0 — 2026-07-14 — trois jeux d'icônes, trois rôles

`icon.library: lucide` (jeu unique) était **inapplicable** : le code charge trois collections, et
il a raison de le faire. Un logo Mastodon ne se redessine pas en Lucide ; une illustration d'état
vide n'est pas une icône d'interface. La règle du jeu unique est remplacée par une règle de rôles
disjoints — `icon.sets.{ui,brand,illustration}` — qui préserve l'intention (Lucide est le jeu
**unique de l'UI**) sans interdire ce qui n'en est pas.

- `usage.rules[icon-set-roles]` : rôles disjoints ; une icône `brand` ou `illustration` ne porte
  jamais une action.
- `usage.rules[icon-accessible-name]` : décorative → `aria-hidden` ; signifiante → `aria-label`.

**Défauts d'accessibilité corrigés au passage** (mesurés au DOM, pas supposés) :

- **15 boutons icon-only sans nom accessible** — un lecteur d'écran y annonçait « bouton », sans
  plus : fermeture de modale, like, partage, réponse, édition, suppression, retrait de marqueur…
  Chacun a reçu un `aria-label` traduit, propre à son intention, et son icône est passée en
  `aria-hidden`.
- **Le bouton hamburger** n'avait aucun nom : le menu mobile était inatteignable à l'aveugle.
- **9 illustrations `game-icons`** passées en `aria-hidden` (décoratives par définition du rôle).
- **3 logos de plateformes** (Mastodon, ActivityPub, BookWyrm) dotés de `role="img"` +
  `aria-label` : ils remplacent un nom, ils doivent donc en porter un. BookWyrm n'existant pas
  dans simple-icons, il est rendu par un glyphe `game-icons` en substitut de logo — seule
  entorse tolérée, et documentée à l'endroit de l'usage.

Reste ouvert : ~1500 icônes Lucide décoratives sans `aria-hidden`. Impact réel faible (un `<span>`
vide n'est pas annoncé), mais c'est une dette de propreté à traiter en lot.

### v1.1.0 — 2026-07-14 — Fraunces adoptée

`font.family.display` était figée sur Fraunces mais la fonte n'était pas chargée : le projet
servait **Crimson Text**. Divergence tranchée en faveur de la maquette.

- **Fraunces self-hostée** en fonte variable, sous-ensemble latin : `fraunces-var.woff2` (67 Ko)
  et `fraunces-var-italic.woff2` (82 Ko). L'italique est un fichier distinct parce qu'elle porte
  du sens dans ce système — ce n'est pas une emphase typographique, c'est la description narrative.
- **Crimson Text retirée** — `crimson-text-400.woff2` et `-400-italic.woff2` supprimés (66 Ko),
  plus aucun usage. `_fonts.html`, `uno.config.js` et les feuilles de la documentation basculés.
- `font-serif` et `font-display` pointent tous deux sur Fraunces : les 34 usages historiques de
  `font-serif` désignaient déjà les zones de fiction — aucun renommage nécessaire.
- **Coût net : +83 Ko** de fonte. En contrepartie, une fonte variable remplace deux fichiers
  statiques et couvre les graisses 400 à 700 avec l'axe optique.
- **Vérifié au navigateur** : les deux faces passent en `loaded`, `document.fonts.check()`
  répond vrai en 400 / 700 / italique, et l'axe variable produit bien des métriques distinctes
  (148,9 px en 400 contre 159,84 px en 700).

Reste ouvert : l'exploitation des axes `SOFT` et `WONK` de Fraunces, non utilisés à ce stade.

### v1.0.0 — 2026-07-14 — arbitrage résolu, migration du code, figeage

Source : `templates/wireframes/maquette-v3.html`, extraction CSS (16 pages).
Critique : `design/critique/2026_07_14-design-system.md` (score 62/100).

**Décisions d'arbitrage — gate humain (3)**

1. **Néon dédoublé.** `color.domain.available` (`#00e676`) reste sur les pastilles, anneaux et
   fonds ; `color.domain.available-text` (`#0a8f4d`) porte tout glyphe. `#0a8f4d` n'est pas une
   invention : c'est la valeur que la maquette utilisait déjà en douce sur
   `.scene__marker--enter`, seule couleur hors palette du fichier — la maquette contournait son
   propre token.
2. **Espacement au pas de 2 px.** L'échelle de 4 px du brouillon était une fiction : les valeurs
   dominantes de la maquette sont 6 (34×), 10 (22×), 14 (26×) px. Le token set est désormais
   fidèle à sa source.
3. **Le code s'aligne sur les tokens** (et non l'inverse). Les utilitaires seront renommés vers
   les namespaces sémantiques du contrat — on nomme le rôle, pas la teinte : `brand-primary`
   survit à un changement de rouge, `crimson` non.

**Deltas `destructure` appliqués sans gate (aucune valeur en compétition)**

- Groupe `focus.*` créé (2px / offset 2px / indigo). La maquette n'avait aucun style de focus.
- `border.style.*` créé — le statut d'un personnage ne peut plus reposer sur la seule teinte.
- `motion.duration.instant` + bloc `prefers-reduced-motion` dans l'adapter.
- États `loading` / `disabled` / `invalid` / `empty` déclarés sur `btn`, `form-field`, `editor`,
  `card`.

**Déduplications** — `color.domain.{remote,forked,oracle}` sont trois alias explicites de
`color.brand.accent` : trois rôles narratifs distincts, une valeur. Conservés comme alias, pas
fusionnés — leur divergence future est prévisible.

**Renommages de couche 1** — `semantic.text` → `semantic.ink`, `semantic.text-secondary` →
`semantic.ink-secondary`, `semantic.text-muted` → `semantic.muted`. Motif : éviter l'utilitaire
`text-semantic-text-muted`, illisible.

### Réconciliation code → manifeste (étape 2bis) — CLOSE

`mode: "utility-first"`. Le vocabulaire fermé porte sur l'**usage des tokens** : le segment de
tête de toute classe de couleur doit être un groupe top-level de `tokens.json § color.*`
(`brand`, `neutral`, `sepia`, `semantic`, `domain`, `ui`).

**6 303 occurrences migrées** dans 147 fichiers (143 templates + `uno.config.js` + `base.css` +
`easymde-theme.css` + `main.js`) — plan : `aidd_docs/tasks/2026_07/2026_07_14-design-contract-namespace-migration.md`.

| Ancien namespace | Occurrences | Cible |
|---|---|---|
| `muted` | 1 911 | `semantic-muted` |
| `primary` | 1 022 | `semantic-ink` |
| `border` | 676 | `semantic-border` |
| `crimson` | 643 | `brand-primary` |
| `secondary` | 562 | `semantic-ink-secondary` |
| `surface` / `input` | 376 | `semantic-surface` |
| `error` | 178 | `semantic-danger` |
| `info` / `success` / `warning` | 429 | `semantic-*` |
| `card` / `card-dark` | 169 | `semantic-card` / `-card-sunken` |
| `violet` | 92 | `brand-accent` |
| `neon` | 17 | `brand-signal` (surfaces) · `domain-available-text` (glyphes) |
| `brand` | 5 | `domain-pc` |
| `amber-*` (toggle de thème) | 8 | `ui-sun` / `ui-sun-soft` |

**Vérification.** Mesure `getComputedStyle` sur tous les éléments de la page d'accueil, en clair
et en sombre, avant/après : **aucune différence de couleur, de fonte, de taille de police,
d'espacement ni de graisse.** Les seuls écarts sont les deux changements voulus (rayons et
z-index, ci-dessous). Suite de tests : 552 passés, 0 échec.

**Changements de rendu assumés**

1. **Rayons alignés sur le contrat** — cartes 16px → 12px (`radius.lg`), boutons 12px → 8px
   (`radius.md`). C'est l'application de « la maquette fait foi ».
2. **Ordre d'empilement corrigé** — avant : `dropdown(10) < sticky(20) < toast(50)`. Après :
   `sticky(40) < dropdown(60) < toast(120)`. Le menu déroulant passe désormais **devant**
   l'en-tête collant, ce qui est le comportement attendu et ne l'était pas.
3. **Focus visible** — le shortcut `focus-ring` (2px, offset 2px, indigo) est appliqué aux
   boutons, champs et interrupteurs. La maquette n'avait aucune règle de focus.
4. **Types de rapport** — `thread_rapport_card.html` ne colore plus les rapports par un fond
   pastel (`bg-indigo-50` pour « description »…). Ces teintes sont réservées à la sémantique de
   domaine — l'indigo signifie « personnage joueur ». La différenciation passe désormais par la
   typographie et la bordure, comme le moteur `rap`.

**Pièges neutralisés.** Trois échelles ne sont **pas** injectées dans le thème UnoCSS —
`spacing`, `fontSize`, `lineHeight`, `letterSpacing`, `borderRadius`, `maxWidth` — parce que
leurs clés collisionnent avec l'échelle native d'Uno pour des valeurs différentes : les injecter
redéfinissait silencieusement `p-4` (16px → 4px), `text-sm` (14px → 13px) et `leading-tight`
dans tout le projet. Les valeurs du contrat restent accessibles par variable CSS. Voir
`design/adapters/uno-tokens.mjs`.

**Divergences manifeste → code (non bloquantes).** Les 17 composants BEM du manifeste
(`rap`, `badge--npc`, `card__body`…) n'apparaissent dans aucun template : la maquette v3 n'est
pas intégrée. Déclarés en avance de leur premier usage, ce qui est légitime.

**Hors périmètre du lint.** `templates/wireframes/*.html` sont des maquettes statiques (675
classes Tailwind natives), pas des templates applicatifs. À exclure du glob de `enforce`.
