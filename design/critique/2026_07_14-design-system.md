# Critique — design system (sortie de `define`)

- **Date** : 2026-07-14
- **Cible** : `design/tokens.json` + `design/design-system.md` (v0.1.0, brouillon), dérivés de `templates/wireframes/maquette-v3.html`
- **Mode** : entonnoir
- **Score de distinction** : **62/100**

Le score est haut là où le produit est le produit (le moteur narratif, le sépia, l'italique
signifiante) et bas partout ailleurs : le chrome applicatif est du framework de série.

---

## Mesures

Comptes réels sur `maquette-v3.html` (1616 lignes), pas des impressions.

| Mesure | Compte | Lecture |
|---|---|---|
| Tailles de police distinctes | **20** (hors clamps) | dont 4 demi-pixels : 11,5 / 12,5 / 13,5 / 16,5 |
| Valeurs d'espacement distinctes | **25** | dont 3, 5, 7, 9, 26, 34 px |
| Rayons distincts | **8** (hors vars) | 4 / 6 / 8 / 10 / 12 / 999 (+22, 30 = châssis de l'outil) |
| Couleurs hex hors token | **2** | `#0a8f4d` (voir ci-dessous), `#12121f` (chrome outil) |
| Icônes SVG inline | 32 | Lucide, cohérent |
| **Emoji comme icône** | **0** | ✅ rien à signaler |
| **Règles `:focus` / `:focus-visible`** | **0** | ❌ |
| **`prefers-reduced-motion`** | **0** | ❌ |
| **États `disabled` / `loading`** | **0** | ❌ |
| Attributs `aria-*` | 10 | pour 32 icônes et ~16 pages |

**Le fait le plus parlant du lot : `#0a8f4d`.** C'est un vert sombre, hors palette, posé sur un
seul sélecteur — `.scene__marker--enter`. C'est-à-dire : au moment où l'auteur de la maquette a
eu besoin de lire du vert **en texte**, il a silencieusement abandonné le néon `#00e676` pour un
vert lisible. La maquette contourne déjà son propre token. Ce n'est plus une hypothèse de ma
part sur le contraste : c'est une preuve interne.

---

## Critique par lentille

### Générique vs distinctif — `générique`

Ce qui est réellement distinctif tient en trois choses, et elles sont bonnes :

1. **Le moteur `rap`** — un composant, quatre registres narratifs par modificateur. C'est le
   produit, et aucun framework ne fournit ça.
2. **Le sépia** — un mode sombre qui est un choix (papier brûlé, halos crimson en guise
   d'ombres) et pas une inversion de luminance.
3. **L'italique Fraunces porteuse de sens** — la police comme signal de registre narratif.

Tout le reste pourrait être n'importe quel SaaS de 2024 : Inter, radius 8/12, ombre molle
`0 2px 16px rgba(0,0,0,.07)`, cartes blanches sur fond cassé, Lucide en 16px, badge-pastille.
**La personnalité s'arrête au bord du contenu.** Un réseau de fiction partagée dont le chrome
ressemble à un dashboard analytics rate une occasion : le chrome pourrait lui aussi *raconter*
(marges de manuscrit, filets, numérotation de scène, ferrage éditorial) au lieu de se contenter
de contenir.

Choix pris par confort, non assumés : le radius 8px (aucune intention), l'ombre molle (elle
n'existe que parce que "une carte a une ombre"), Inter (défaut mondial).

### Cohérence interne — `incohérent`

**L'échelle d'espacement que j'ai tokenisée est en partie une fiction.** J'ai posé un pas de
4 px (`space.1` = 4px, `.2` = 8px, `.3` = 12px…). Or les valeurs les plus fréquentes de la
maquette sont **6px (34×), 10px (22×), 14px (26×), 18px, 22px, 26px, 34px** — un pas de 2 px de
facto. Mon échelle 4px ne couvre pas la majorité des espacements réels : l'appliquer
telle quelle ferait bouger presque toute la mise en page. Trois issues possibles (cf. pistes) —
mais l'état actuel est un token set qui ment sur sa source. C'est le défaut le plus concret de
la sortie de `define`.

**Vingt tailles de police pour seize pages**, dont quatre demi-pixels (11,5 / 12,5 / 13,5 /
16,5). Il n'y a pas d'échelle modulaire là-dedans : il y a une suite de micro-ajustements
optiques. 13px, 13,5px et 14px coexistent, sans qu'aucun rôle ne les distingue.

**Le message des rayons se contredit** : 4, 6, 8, 10 et 12px cohabitent sans logique de rôle
(pourquoi l'`icon-btn` est-il à 10px et le bouton à 8px ?).

**La bordure lavande `#d4cfe8`** sur une palette entièrement chaude est le seul élément froid
du système. Soit c'est une intention (et elle n'est écrite nulle part), soit c'est un résidu.

### Accessibilité — `risque-a11y` (bloquant)

Trois manques structurels, pas des détails d'implémentation :

- **Aucun style de focus n'existe dans la maquette.** Zéro règle `:focus-visible`. Un produit de
  lecture-écriture au clavier sans focus visible n'est pas navigable. Ce n'est pas « à faire à
  l'intégration » : la couleur et la forme du focus sont des décisions de direction, et le
  crimson sur fond chaud n'est pas un anneau de focus évident (contraste 4,2:1).
- **Aucun `prefers-reduced-motion`.** La direction pose des animations (`400ms` avec courbe
  d'entrée, transitions d'ouverture de tiroir) sans jamais dire ce qui se passe quand
  l'utilisateur les refuse.
- **Aucun état `disabled` ni `loading`.** Sur un produit où l'on soumet des demandes de claim /
  adoption / fork — donc des actions asynchrones, réseau, fédérées, potentiellement lentes et
  refusables — l'absence d'état d'attente et d'état désactivé se paiera en incohérences
  inventées par le développeur.

S'ajoutent les contrastes déjà consignés dans la charte (néon 1,6:1 ; crimson texte 4,2 ; blanc
sur crimson 4,4 ; muted 3,2). Rappel : **la maquette elle-même triche déjà** (`#0a8f4d`).

Enfin, **la couleur est le seul vecteur d'état** dans tout le système d'anneaux d'avatar et de
badges : PJ / PNJ / disponible / distant se distinguent uniquement par une teinte. Un
utilisateur daltonien (deutéranopie : ambre PNJ ≈ vert disponible) ne peut pas lire le statut
central du produit. Le badge porte bien un libellé, mais **l'anneau d'avatar, non**.

### Tendances & fraîcheur

Peu de dette de mode — c'est un point positif. Pas de glassmorphism, pas de gradient 2014, pas
de neumorphism. Deux réserves :

- L'**ombre molle diffuse** (`0 2px 16px`) est le tic de 2020-2023 ; elle est déjà en train de
  dater au profit du filet net (bordure 1px + zéro ombre). Coût de retrait : nul.
- Le **halo crimson en mode sombre** est plus risqué : c'est joli, c'est daté-mais-réversible, et
  ça devient vite sale sur écran OLED bas de gamme. À garder — mais en connaissance de cause.

L'intemporel du lot, c'est le sépia et la serif. Ne pas y toucher.

### Divergence d'inspiration

Le territoire actuel est « SaaS chaleureux ». Trois voisinages crédibles, tous compatibles avec
le crimson et le sépia :

- **Éditorial / manuscrit** — la page comme feuillet : filets nets, pas d'ombre, numérotation de
  scène en marge, Fraunces poussée jusque dans les titres de section du chrome. Référence de
  registre : les liseuses de fiction sérielle (AO3 en propre, Wattpad en travaillé).
- **Grimoire / table de jeu** — assumer le JdR : chapeaux de section, capitales à empattement,
  encadrés de règle, bordures doubles. Risque : le kitsch fantasy, à tenir par la retenue.
- **Terminal narratif** — pousser un seul axe à fond : monospace pour les métadonnées, densité
  élevée, couleur rare. Référence de registre : les interfaces de MUD modernisées.

---

## Pistes d'évolution

### Axe accessibilité (le plus urgent)

- **Néon dégradé en signal, pas en texte** — principe : une couleur qui échoue à 4,5:1 ne porte
  jamais de glyphe. Le néon reste sur les pastilles, anneaux et fonds (seuil 3:1) ; tout texte
  « disponible » passe sur `#0a8f4d` — c'est-à-dire **la valeur que la maquette utilise déjà en
  douce**. Effet : le défaut a11y le plus grave disparaît sans perdre l'identité visuelle.
  Coût contrat : **re-figeage** (dédouble `color.domain.available` en `…-signal` / `…-text`).
- **Statut par forme, pas seulement par teinte** — principe : l'anneau d'avatar encode le statut
  par un motif (plein / pointillé / double / absent) *en plus* de la couleur. Effet : le cœur du
  produit devient lisible en daltonisme et en `forced-colors`. Coût : **re-figeage** (ajoute
  `border.style.*`).
- **Focus comme décision de direction** — principe : un anneau de 2px `outline-offset: 2px` en
  `color.brand.identity` (indigo, 4,5:1) plutôt qu'en crimson (4,2:1), pour ne pas confondre
  focus et action. Effet : navigation clavier possible. Coût : **re-figeage** (nouveau groupe
  `focus.*`).

### Axe cohérence

- **Assumer le pas de 2px** — principe : l'échelle réelle de la maquette est un pas de 2, pas de
  4. Tokeniser 2/4/6/8/10/12/14/16/20/24/32/40/56 et cesser de prétendre à une grille de 4.
  Effet : le token set cesse de mentir ; aucune régression visuelle. Coût : **re-figeage** de
  `space.*` (mais rien n'est branché, donc gratuit aujourd'hui).
- **Ou : rationaliser vers 4px et l'assumer comme une refonte** — principe : la grille de 4 est
  un standard, mais l'adopter *déplace* la maquette (6→8, 10→12, 14→16). Effet : système plus
  net, fidélité visuelle perdue. Coût : **re-figeage** + reprise de la maquette. À ne choisir que
  si « la maquette fait foi » est révisable.
- **Échelle de type par rôle, pas par pixel** — principe : supprimer les demi-pixels et les
  triplets 13/13,5/14 en nommant les rôles (meta, ui, body, dialogue, titre) et en n'autorisant
  qu'une taille par rôle. Effet : passe de 20 tailles à ~9. Coût : **re-figeage**.

### Axe distinction

- **Sortir le chrome du générique** — principe : appliquer au chrome la logique éditoriale déjà
  présente dans le contenu (filet net à la place de l'ombre molle, Fraunces sur les titres de
  section, marge de manuscrit). Effet : le produit cesse de ressembler à un dashboard.
  Coût : **rentre dans le contrat** pour l'ombre (`shadow.card` → bordure), **re-figeage** pour
  la typo du chrome.
- **Un seul axe poussé à fond : la typo** — principe : Fraunces variable, exploitée sur son axe
  optique (`opsz`) et son `SOFT`/`WONK`, de la légende au hero. Effet : identité forte, coût de
  chargement à mesurer. Coût : **re-figeage** + self-hosting.

### Axe états (occasion manquée)

- **Table d'états pour les 3 composants critiques** — `btn--primary`, le formulaire de demande
  de lien (claim/adopt/fork), la carte de personnage cliquable. Neuf états à désigner
  (default / hover / focus / active / disabled / loading / error / success / empty). Effet :
  évite que chaque développeur invente le sien. Coût : **rentre dans le contrat** (c'est de la
  conception, pas du token) — mais doit être fait **avant** `adjust`.

---

## Verdict

**Le levier maximal, c'est le néon.** La maquette a déjà écrit la solution en cachette
(`#0a8f4d`) : dédoubler `color.domain.available` en un token de signal et un token de texte
règle d'un coup le seul défaut d'accessibilité vraiment cassé, sur l'information la plus
importante du produit — sans toucher à l'identité visuelle.

Juste derrière : **l'absence totale de focus, de `reduced-motion` et d'états `disabled`/`loading`
n'est pas un oubli d'intégration, c'est un trou de direction.** Sur un produit fédéré où les
actions sont asynchrones et refusables, ça se paiera.
