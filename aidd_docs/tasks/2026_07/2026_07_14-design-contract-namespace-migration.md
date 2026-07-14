# Instruction : migration du code vers les namespaces du contrat de design

## Feature

- **Résumé** : aligner le code frontend (143 templates + `uno.config.js` + `base.css`) sur le contrat de design figé v1.0.0 (`design/tokens.json`, `design/components.json`). Aujourd'hui le code consomme des utilitaires plats (`text-muted`, `bg-crimson/10`, `z-dropdown`) qui ne correspondent à aucun groupe du contrat ; tant que cette divergence existe, `design-system.md` ne peut pas passer en `status: figé` (blocage `adjust/02-freeze § 2bis`).
- **Stack** : UnoCSS (`presetUno` + `presetIcons`), Vite, Django templates
- **Branche** : `refactor/design-namespace-migration`
- **Contrat de référence** : `design/tokens.json` v1.0.0 · `design/components.json` v1.0.0 (`mode: utility-first`)
- **Confiance** : 7/10 — le renommage est mécanique, mais quatre pièges non-couleur (ci-dessous) peuvent casser en silence
- **Temps estimé** : 1 à 1,5 jour

## Ce que la migration débloque

`components.json` déclare `mode: "utility-first"`. Le vocabulaire fermé porte donc sur l'**usage des tokens** : le segment de tête de toute classe de couleur doit être un groupe top-level de `tokens.json § color.*` — `brand`, `neutral`, `sepia`, `semantic`, `domain`. C'est ce qui rend `enforce`/`lint-core.mjs` capable de vérifier quoi que ce soit. Sans la migration, le linter tourne, ne reconnaît rien, et ressort vert sans avoir rien vérifié.

## Fichiers existants

- @frontend/uno.config.js — thème + 60 shortcuts
- @frontend/src/base.css — variables `--c-*` (canaux RGB) et thème sombre
- @frontend/src/main.js — point d'entrée (importe `base.css`)
- @templates/**/*.html — 143 fichiers portant des classes du design system
- @design/adapters/tokens.css — **nouveau**, à importer
- @design/adapters/uno-tokens.mjs — **nouveau**, à consommer comme thème

### Documentation design préexistante à réconcilier

Quatre documents décrivent le design system **avant** le contrat et vont le contredire :

- `docs/design-system.md`
- `aidd_docs/memory/internal/DESIGN.md`
- `aidd_docs/wireframes/STYLE_GUIDE.md`
- `aidd_docs/wireframes/COMPONENT_MAP.md`

Ils doivent être mis à jour ou marqués obsolètes en fin de migration — sinon ils resteront la référence lue par le prochain développeur (et par l'agent), et la migration sera annulée par inadvertance.

---

## Les quatre pièges (à lire avant de coder)

Le renommage des couleurs est la partie facile. Ce qui casse en silence :

### 1. L'ordre d'empilement s'inverse

| Clé | `uno.config.js` actuel | `tokens.json` | Effet |
|---|---|---|---|
| `z-dropdown` | 10 | 60 | — |
| `z-sticky` | 20 | 40 | **dropdown passe devant sticky** |
| `z-modal` | 40 | 100 | — |

Aujourd'hui `dropdown(10) < sticky(20)`. Dans le contrat, `sticky(40) < dropdown(60)`. L'ordre relatif **s'inverse** : un menu déroulant qui passait sous un en-tête collant passera désormais devant (ce qui est d'ailleurs le comportement correct, mais c'est un changement de rendu à vérifier, pas à subir).

### 2. `spacing` ne doit PAS être remappé

L'échelle native d'UnoCSS (unité 0.25rem, demi-pas inclus) produit déjà le pas de 2px figé : `p-1.5` = 6px, `p-2.5` = 10px, `p-3.5` = 14px. Remapper la clé `spacing` sur les tokens redéfinirait `p-4` de 16px à **4px** dans les 143 fichiers. `uno-tokens.mjs` omet volontairement `spacing` — ne pas « corriger » cet oubli apparent.

En revanche, `spacing.safe` (`env(safe-area-inset-bottom)`) doit être **conservé** : il n'est pas dans les tokens et il porte la barre d'action mobile.

### 3. Les clés de thème non-couleur disparaissent

Le thème actuel définit des clés que `uno-tokens.mjs` ne reprend pas. Les classes correspondantes cesseront de résoudre :

| Classe employée | Aujourd'hui | Cible |
|---|---|---|
| `rounded-card` (31×) | `borderRadius.card` = 0.75rem | `rounded-lg` |
| `rounded-badge` | `borderRadius.badge` = 9999px | `rounded-full` |
| `rounded-button` | `borderRadius.button` = 0.5rem | `rounded-md` |
| `duration-normal` | 200ms | `duration-base` |
| `duration-fast` | **100ms** | `duration-fast` (**150ms** — valeur différente) |
| `duration-slow` | 300ms | `duration-slow` (**400ms**) |
| `shadow-btn` | halo crimson | absent du contrat → à conserver en extension, ou à tokeniser |
| `shadow-dropdown` | ombre portée | idem |
| `easing-in` / `-out` / `-in-out` | 3 courbes | contrat : `standard`, `entrance` |

Décision requise : soit étendre le thème généré d'un bloc de compatibilité, soit migrer les classes. **Recommandation** : migrer les classes (le contrat doit rester la seule source) et tokeniser `shadow-btn` / `shadow-dropdown` s'ils sont jugés nécessaires — ce qui demandera un re-figeage mineur de `tokens.json`.

### 4. Les faux amis du renommage

Ces classes contiennent les mots `primary`, `card`, `muted`… mais **ne sont pas des couleurs**. Un `sed` naïf les détruirait :

`btn-primary` (207×) · `btn-secondary` (160×) · `badge-primary` (75×) · `link-muted` (101×) · `rounded-card` (31×) · `shadow-card` (17×)

Ce sont des **shortcuts UnoCSS**, définis dans `uno.config.js`. Leur nom ne change pas ; c'est leur **définition interne** qui doit être migrée. Le motif de remplacement doit donc être ancré sur les préfixes réellement porteurs de couleur (`bg|text|border|ring|outline|fill|stroke|from|to|via|divide|accent|decoration`) et sur eux seuls — jamais `btn|badge|link|rounded|shadow`.

---

## Table de correspondance des couleurs

| Namespace actuel | Occurrences | Cible |
|---|---|---|
| `muted` | 1 913 | `semantic-muted` |
| `primary` | 1 037 | `semantic-ink` |
| `border` | 687 | `semantic-border` |
| `crimson` | 670 | `brand-primary` |
| `crimson-hover` | — | `brand-primary-hover` |
| `secondary` | 568 | `semantic-ink-secondary` |
| `surface` | 381 | `semantic-surface` |
| `card` | 198 | `semantic-card` |
| `card-dark` | 73 | `semantic-card-sunken` |
| `error` | 191 | `semantic-danger` |
| `info` | 174 | `semantic-info` |
| `success` | 158 | `semantic-success` |
| `warning` | 118 | `semantic-warning` |
| `violet` | 139 | `brand-accent` |
| `neon` | 23 | `brand-signal` (surfaces) · `domain-available-text` (texte) |
| `background` | 8 | `semantic-background` |
| `input` | 2 | `semantic-surface` |
| `brand` | 14 | **déjà conforme** — ne pas toucher |

Les variantes (`hover:`, `focus:`, `dark:`, `group-hover:`, `lg:`) et les modificateurs d'opacité (`/10`, `/30`…) sont préservés tels quels : seul le segment de namespace change.

**Cas `neon` — à trier à la main (23 occurrences seulement).** La règle `usage.rules[signal-never-text]` interdit au néon de porter un glyphe (contraste 1,6:1). `text-neon` → `text-domain-available-text` ; `bg-neon/10`, `border-neon/30`, `ring-neon` → `bg-brand-signal/10`, etc. Ne pas automatiser ce cas.

### Variables CSS inline

~143 usages de `var(--c-*)` dans des attributs `style=` des templates :

`var(--c-border)` → `var(--color-semantic-border)` · `var(--c-surface)` → `var(--color-semantic-surface)` · `var(--c-muted)` → `var(--color-semantic-muted)` · `var(--c-primary)` → `var(--color-semantic-ink)` · `var(--c-secondary)` → `var(--color-semantic-ink-secondary)` · `var(--c-card)` → `var(--color-semantic-card)` · `var(--c-card-dark)` → `var(--color-semantic-card-sunken)` · `var(--c-bg)` → `var(--color-semantic-background)` · `var(--c-brand)` → `var(--color-brand-identity)` · `var(--c-neon)` → `var(--color-brand-signal)` · `var(--c-violet)` → `var(--color-brand-accent)` · `var(--c-warning)` → `var(--color-semantic-warning)`

---

## Phases

### Phase 0 — Filet de sécurité (à ne pas sauter)

> Une migration de 6 260 occurrences sans référence visuelle est un pari, pas un refactor.

1. Créer la branche `refactor/design-namespace-migration`.
2. Capturer une **baseline visuelle** de l'application avant tout changement : les pages principales (accueil, liste de parties, partie, personnage, compte-rendu, profil, recherche, formulaire de lien), en clair **et** en sombre, aux viewports 375px et 1280px. Utiliser Playwright (déjà présent dans l'outillage de test).
3. Vérifier que `pnpm build` (dans `frontend/`) passe **avant** la migration, pour ne pas hériter d'un échec préexistant.

### Phase 1 — Brancher le contrat

> Aucun renommage encore : on rend seulement les tokens disponibles.

1. Importer `design/adapters/tokens.css` dans `frontend/src/main.js`, **avant** `base.css`.
2. Dans `base.css`, remplacer les blocs `:root` / `[data-theme]` par les seules règles qui ne sont pas des tokens : `box-sizing`, `body`, styles d'`input`, mini-reset `button`, `[x-cloak]`. Toutes les déclarations `--c-*` et `--shadow-*` disparaissent — elles vivent désormais dans `tokens.css`.
3. Conserver le dégradé de fond du mode sombre (`--body-bg`, radial-gradient) : ce n'est pas un token, c'est une décoration de page. Le réécrire avec `var(--color-sepia-900)`.
4. Vérifier que `pnpm build` passe. À ce stade, le rendu doit être **strictement inchangé** (les anciennes vars existent encore via `base.css` si on procède par recouvrement — sinon, faire les phases 1 et 2 d'un bloc).

### Phase 2 — Migrer `uno.config.js`

1. Importer le thème généré : `import { theme } from '../design/adapters/uno-tokens.mjs'`.
2. Fusionner en conservant explicitement ce que le contrat ne couvre pas :
   - `spacing: { safe: 'env(safe-area-inset-bottom)' }` (ne pas ajouter d'autre clé `spacing`)
   - `boxShadow.btn` et `boxShadow.dropdown`, en attendant leur tokenisation éventuelle
3. Réécrire les ~60 **shortcuts** avec les nouveaux namespaces. C'est le meilleur rapport effort/couverture : `btn-primary`, `card`, `badge-*`, `input-base`, `form-input`, `dropdown-menu`, `link-muted`, `avatar` encapsulent à eux seuls une grande partie des usages de couleur du projet.
4. Dans les shortcuts, en profiter pour appliquer les règles figées du contrat : `rounded-[12px]` → `rounded-md` (le contrat dit **8px** pour un bouton, pas 12), ajouter le focus visible (`focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-semantic-focus`) — la maquette n'en avait aucun.

### Phase 3 — Migrer les templates

1. Écrire un script de remplacement **ancré** (Node ou PowerShell), pas un `sed` global. Motif :
   `/(^|[\s"'])((?:[a-z-]+:)*!?)(bg|text|border|ring|outline|fill|stroke|from|to|via|divide|accent|decoration)-(crimson|violet|neon|surface|card|card-dark|primary|secondary|muted|input|success|warning|error|info|background)(\/\d+)?\b/`
   Remplacement : préserver le groupe de variantes et le modificateur d'opacité ; ne substituer que le namespace.
2. Ordonner les remplacements du plus long au plus court (`card-dark` **avant** `card`, `crimson-hover` **avant** `crimson`) — sinon `bg-card-dark` devient `bg-semantic-card-dark`, qui ne résout pas.
3. Traiter `neon` **manuellement** (23 occurrences, cf. règle `signal-never-text`).
4. Remplacer les `var(--c-*)` inline (table ci-dessus).
5. Migrer les classes non-couleur du piège n°3 (`rounded-card`, `duration-normal`…).
6. Vérifier qu'aucune occurrence des anciens namespaces ne subsiste :
   `grep -rE "\b(bg|text|border|ring)-(crimson|violet|neon|surface|card|primary|secondary|muted|input|success|warning|error|info)\b" templates/` → doit être vide.

### Phase 4 — Vérification

1. `pnpm build` dans `frontend/` — zéro erreur, CSS régénéré.
2. **Comparaison visuelle** contre la baseline de la phase 0, en clair et en sombre. Toute différence doit être expliquée ; les seules attendues sont : le rayon des boutons (12px → 8px), l'empilement dropdown/sticky, et l'apparition des anneaux de focus.
3. Lancer `lint-core.mjs` (via `/design:enforce`) sur `templates/` : zéro violation `raw-hex`, zéro namespace inconnu.
4. Passer `design/design-system.md` en `status: figé` et retirer la section « Blocage du figeage » de la Provenance. **C'est l'objectif de toute l'opération.**
5. Mettre à jour ou marquer obsolètes les quatre documents de design préexistants.

---

## Ce que cette migration ne fait PAS

- Elle n'intègre pas la maquette v3 (les 17 composants BEM du manifeste — `rap`, `badge--npc`, `card__body` — n'apparaissent encore dans aucun template ; c'est une divergence manifeste → code, non bloquante).
- Elle ne charge pas Fraunces (question ouverte du contrat).
- Elle ne bascule pas les `@media` en `@container` (question ouverte).
- Elle ne corrige pas les contrastes non résolus au figeage (`semantic.muted` à 3,2:1, crimson en texte à 4,2:1).

Ces quatre points restent ouverts après la migration et devront être traités séparément.
