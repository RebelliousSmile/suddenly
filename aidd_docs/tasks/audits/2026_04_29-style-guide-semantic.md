# Code Review — Style Guide : sémantique et cohérence

Audit de `templates/wireframes/style-guide.html` et `frontend/uno.config.js` après la définition de la sémantique couleurs du 2026-04-29.

- Statut: in-progress
- Confidence: high

## Périmètre

- `templates/wireframes/style-guide.html`
- `frontend/uno.config.js` (shortcuts badges)

---

## Scoring

- [🔴] **badge-available = badge-adopted** : `uno.config.js:146,148` Les deux shortcuts sont identiques (`bg-success/10 text-success border border-success/30`). Un personnage "disponible" et un personnage "adopté" ne doivent PAS avoir le même visuel — c'est l'opposé sémantique. (Différencier : available=success, adopted=success-foncé ou couleur distincte)
- [🔴] **btn-danger hardcodé 2×** : `style-guide.html:499,538` La classe `btn-danger` est définie dans les shortcuts mais jamais utilisée. À la place : `bg-red-600 text-white px-4 py-2 rounded-lg...` — duplication du shortcut. (Remplacer par `class="btn-danger"`)
- [🔴] **Date input n'utilise pas form-input** : `style-guide.html:820` `block w-full rounded-[12px] border border-solid border-border px-3 py-2.5 focus:border-crimson sm:text-sm bg-input text-primary outline-none cursor-pointer` est exactement `form-input` + `cursor-pointer`. (Remplacer par `class="form-input cursor-pointer"`)
- [🟡] **badge-info = badge-claimed** : `uno.config.js:147,150` Les deux shortcuts sont identiques après la refonte. badge-claimed = statut de personnage, badge-info = message générique. L'identité est acceptable mais doit être documentée pour éviter les doublons futurs.
- [🟡] **Descriptions palette incohérentes avec section 0** : `style-guide.html:264,279` Violet dit "Accent secondaire, fork, badges" au lieu de "Dérivation / fork". Neon dit "Accent formulaires, fond teinté" au lieu de "Création / formulaire actif". (Aligner le texte des 2 cartes avec les définitions de la section 0)
- [🟡] **git-merge affiché en text-warning** : `style-guide.html:959` L'icône `i-lucide-git-merge` est montrée en warning/amber dans la galerie icônes, alors que Claim est maintenant info/bleu dans la section 0. (Changer en `text-info`)
- [🟡] **text-crimson sur icônes d'avatar décoratifs** : `style-guide.html:625,633,641,649,717` Les icônes `i-lucide-user` dans les placeholders d'avatar utilisent `text-crimson`. Crimson = interaction uniquement. Un avatar placeholder est décoratif. (Remplacer par `text-muted`)
- [🟡] **bg-background utilisé inside un composant** : `style-guide.html:82` La section 0 dit "bg-background — Racine, jamais dans un composant", mais la carte de démonstration utilise précisément `bg-background` sur un div avec `border` et `padding`. Auto-contradiction. (Ajouter une note "usage illustratif uniquement" ou utiliser un fond neutre)
- [🟡] **Domaine d'instance incohérent** : `style-guide.html:1128` L'instance badge affiche `suddenly.games`, alors que le projet définit `suddenly.social` et `soudainement.fr`. (Remplacer par `suddenly.social`)
- [🟢] **badge-pending et badge-rejected absents de la section 4** : `style-guide.html:593` Les shortcuts et la safelist contiennent `badge-pending` et `badge-rejected`, mais la section 4 ne les montre pas. (Ajouter aux badges génériques)
- [🟢] **sparkles en text-warning sans justification** : `style-guide.html:967` L'icône sparkles est montrée en warning/amber. Warning = "en attente / attention". Sparkles n'ont pas ce sens. (Utiliser `text-primary` ou définir un rôle)
- [🟢] **Avatar placeholders : fond hardcodé** : `style-guide.html:624,632,640,648,715` `style="background:#e0e7ff"` est une valeur Tailwind indigo-100 hardcodée qui ne répond pas au thème dark/light. (Remplacer par un token CSS ex. `bg-surface` ou une variable)
- [🟢] **Blockquote typographie sans couleur** : `style-guide.html:444` Le blockquote de la section 2 n'a pas de classe de couleur, contrairement au comportement documenté en section 0 (text-secondary). Sans la classe prose-report, il hérite du parent en text-primary, ce qui est incohérent. (Ajouter `text-secondary`)

---

## ✅ Code Quality Checklist

### Potentiellement inutile

- [🟡] **badge-info = badge-claimed** : identiques, l'un pourrait être un alias de l'autre

### Conformité standards

- [🟢] Naming conventions ok — toutes les classes suivent les conventions kebab-case
- [🟡] Descriptions section 1 ne reflètent pas la sémantique définie en section 0

### Architecture

- [🔴] Shortcuts dupliqués (badge-available=badge-adopted, badge-info=badge-claimed)
- [🔴] Composants HTML ne réutilisent pas les shortcuts disponibles (btn-danger, form-input)

### Santé du code

- [🟢] Taille de fichier correcte (~1140 lignes pour un design system complet)
- [🟡] Valeurs hardcodées non tokenisées (`background:#e0e7ff`, `bg-red-600`)
- [🟢] Pas de JS inliné problématique — Alpine.js correctement encapsulé

### Frontend

#### États UI

- [🟡] Aucun état `disabled` montré pour les form-input (section 7)
- [🟢] États hover/focus bien illustrés pour les boutons
- [🟡] badge-pending (en attente) absent des exemples visuels

#### UI/UX

- [🟡] Contradiction interne : bg-background décrit comme "jamais dans un composant" mais utilisé dans un composant illustratif
- [🟢] Design responsive ok — grids adaptatifs sm/lg sur toutes les sections
- [🟢] Icônes accessibles via classes, pas via SVG inline

---

## Corrections prioritaires

| Priorité | Fichier | Correction |
|----------|---------|-----------|
| P0 | `uno.config.js:148` | Différencier badge-adopted de badge-available |
| P0 | `style-guide.html:499,538` | Utiliser `btn-danger` shortcut |
| P0 | `style-guide.html:820` | Utiliser `form-input cursor-pointer` |
| P1 | `style-guide.html:264,279` | Aligner descriptions palette avec section 0 |
| P1 | `style-guide.html:959` | git-merge → text-info |
| P1 | `style-guide.html:625,633,641,649,717` | text-crimson → text-muted sur avatars décoratifs |
| P1 | `style-guide.html:1128` | `suddenly.games` → `suddenly.social` |
| P2 | `style-guide.html:82` | Note "illustratif" sur bg-background |
| P2 | `style-guide.html:444` | Ajouter text-secondary sur blockquote typo |
| P2 | `style-guide.html:624+` | Remplacer `background:#e0e7ff` par token CSS |
| P3 | `style-guide.html:593` | Ajouter badge-pending et badge-rejected |
| P3 | `style-guide.html:967` | sparkles → text-primary |

## Final Review

- **Score**: 6.5/10 — sémantique bien définie en section 0, mais plusieurs sections existantes n'ont pas été mises à jour pour la refléter
- **Feedback**: La section 0 est solide et constitue une vraie référence. Les problèmes sont principalement des incohérences entre la documentation (section 0) et les exemples (sections 1-9), plus deux shortcuts identiques dans uno.config.js qui créent une confusion sémantique réelle (available=adopted).
- **Follow-up**: Appliquer les corrections P0 immédiatement, P1 dans la même session, P2-P3 en nettoyage.
- **Additional Notes**: La distinction `badge-available` vs `badge-adopted` est le problème le plus impactant car il se répercute dans tous les templates qui affichent des statuts de personnage.
