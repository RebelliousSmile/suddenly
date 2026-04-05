# Charte graphique — Suddenly

**Date** : 2026-04-05
**Outil** : UnoCSS 0.58 + HTMX 1.9 + Alpine.js 3.14
**Build** : Vite 5.4 -> `/static/dist/`

---

## 1. Palette de couleurs

### Couleurs principales

```
PRIMARY (Indigo) — Creativite, fiction, identite
+------+------+------+------+------+------+------+------+------+------+------+
|  50  | 100  | 200  | 300  | 400  | 500  | 600  | 700  | 800  | 900  | 950  |
|eef2ff|e0e7ff|c7d2fe|a5b4fc|818cf8|6366f1|4f46e5|4338ca|3730a3|312e81|1e1b4b|
+------+------+------+------+------+------+------+------+------+------+------+
                                           ^^^^^^ reference

SECONDARY (Emerald) — Liens, connexions, succes
+------+------+------+------+------+------+------+------+------+------+------+
|  50  | 100  | 200  | 300  | 400  | 500  | 600  | 700  | 800  | 900  | 950  |
|ecfdf5|d1fae5|a7f3d0|6ee7b7|34d399|10b981|059669|047857|065f46|064e3b|022c22|
+------+------+------+------+------+------+------+------+------+------+------+
                                           ^^^^^^ reference

ACCENT (Amber) — Attention, actions, PNJ disponibles
+------+------+------+------+------+------+------+------+------+------+------+
|  50  | 100  | 200  | 300  | 400  | 500  | 600  | 700  | 800  | 900  | 950  |
|fffbeb|fef3c7|fde68a|fcd34d|fbbf24|f59e0b|d97706|b45309|92400e|78350f|451a03|
+------+------+------+------+------+------+------+------+------+------+------+
                                           ^^^^^^ reference
```

### Couleurs de statut personnage

```
+------------------+----------+----------------------+
| Statut           | Couleur  | Usage                |
+------------------+----------+----------------------+
| PNJ disponible   | #10b981  | badge-available      |
|                  | green    | (vert)               |
+------------------+----------+----------------------+
| Reclame (Claim)  | #f59e0b  | badge-claimed        |
|                  | amber    | (ambre)              |
+------------------+----------+----------------------+
| Adopte (Adopt)   | #6366f1  | badge-adopted        |
|                  | indigo   | (indigo)             |
+------------------+----------+----------------------+
| Derive (Fork)    | #8b5cf6  | badge-forked         |
|                  | violet   | (violet)             |
+------------------+----------+----------------------+
| PJ actif         | #3b82f6  | badge-pc             |
|                  | blue     | (bleu)               |
+------------------+----------+----------------------+
```

### Couleurs systeme

```
+------------------+----------+----------------------+
| Role             | Valeur   | Variable CSS         |
+------------------+----------+----------------------+
| Background       | #fafafa  | --color-bg           |
| Surface (cards)  | #ffffff  | --color-surface      |
| Texte principal  | #1f2937  | --color-text         |
| Texte secondaire | #6b7280  | --color-text-muted   |
| Bordures         | #e5e7eb  | --color-border       |
| Primary          | #6366f1  | --color-primary      |
| Primary dark     | #4f46e5  | --color-primary-dark |
| Secondary        | #10b981  | --color-secondary    |
+------------------+----------+----------------------+
```

### Couleurs de feedback

```
+------------------+----------+----------+
| Type             | Fond     | Texte    |
+------------------+----------+----------+
| Success          | #d1fae5  | #065f46  |
| Error            | #fee2e2  | #991b1b  |
| Warning          | #fef3c7  | #92400e  |
| Info             | #dbeafe  | #1e40af  |
+------------------+----------+----------+
```

---

## 2. Typographie

### Familles

```
SANS-SERIF (corps, UI)
  Inter, system-ui, -apple-system, sans-serif
  Usage : tout le texte d'interface

SERIF (citations, accents narratifs)
  Lora, Georgia, serif
  Usage : blockquotes dans quote_card, contenu narratif

MONOSPACE (editeur, code)
  JetBrains Mono, Fira Code, monospace
  Usage : textarea de l'editeur de CR
```

### Echelle

```
text-xs    0.75rem / 1rem      metadonnees, timestamps
text-sm    0.875rem / 1.25rem  labels, texte secondaire
text-base  1rem / 1.5rem       corps de texte
text-lg    1.125rem / 1.75rem  citations (serif italic)
text-xl    1.25rem / 1.75rem   titres de section
text-2xl   1.5rem / 2rem       titres de page
text-4xl   2.25rem / 2.5rem    hero, element decoratif
```

### Graisses

```
font-normal   400   corps de texte
font-medium   500   boutons, labels
font-semibold 600   titres de section (text-heading)
font-bold     700   logo, hero
```

---

## 3. Espacement et layout

### Container

```
container-app = max-w-7xl mx-auto px-4 sm:px-6 lg:px-8

  mobile (<640px)  : px-4  (16px)
  tablet (640-1024): px-6  (24px)
  desktop (>1024)  : px-8  (32px)
  max-width        : 80rem (1280px)
```

### Grille responsive

```
Cards (3 colonnes) :
  grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4

Cards (4 colonnes, compact) :
  grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3

Sidebar + content :
  flex flex-col md:flex-row gap-6
  sidebar: w-full md:w-64
  content: flex-1
```

### Tokens d'espacement

```
gap-1   0.25rem   entre badges inline
gap-2   0.5rem    entre elements d'une ligne
gap-3   0.75rem   entre cards compactes
gap-4   1rem      entre cards standard, sections
gap-6   1.5rem    entre sections majeures
gap-8   2rem      entre blocs de page
```

---

## 4. Coins et ombres

### Border radius

```
rounded-button  0.5rem (8px)   boutons, inputs
rounded-card    0.75rem (12px) cards, modals
rounded-badge   9999px         badges (pill)
rounded-full    50%            avatars
```

### Ombres

```
shadow-card      0 1px 3px rgba(0,0,0,0.1)     repos
shadow-card-hover 0 4px 6px rgba(0,0,0,0.1)    hover
shadow-dropdown  0 10px 15px rgba(0,0,0,0.1)    menus flottants
```

---

## 5. Composants

### Boutons

```
[btn-primary]     Indigo 600, texte blanc, hover 700
                  Action principale : publier, envoyer, creer

[btn-secondary]   Fond blanc, bordure grise, texte gris 700
                  Action secondaire : sauvegarder brouillon, annuler

[btn-ghost]       Pas de fond, texte gris 600, hover gris 100
                  Action tertiaire : retour, fermer

[btn-danger]      Rouge 600, texte blanc, hover 700
                  Action destructive : supprimer, revoquer

Tailles :
  btn-sm   px-3 py-1.5 text-sm    actions inline, cards
  (defaut) px-4 py-2              formulaires, modals
  btn-lg   px-6 py-3 text-lg      hero CTA
```

### Cards

```
+------------------------------------------------------------+  card
| card-header (optionnel)                                    |  px-4 py-3, border-b
+------------------------------------------------------------+
|                                                            |
| card-body                                                  |  p-4 sm:p-6
|                                                            |
+------------------------------------------------------------+
| card-footer (optionnel)                                    |  px-4 py-3, bg-gray-50
+------------------------------------------------------------+

  card       : bg-white, border gray-200, rounded-card, shadow-card
  card-hover : + shadow-card-hover au hover, transition
```

### Badges

```
  [badge-available]  vert      PNJ disponible    (o) Dispo
  [badge-claimed]    ambre     Reclame           (*) Reclame
  [badge-adopted]    indigo    Adopte            (v) Adopte
  [badge-forked]     violet    Derive            (/) Derive
  [badge-pc]         bleu      PJ actif          (*) PJ

  [badge-primary]    indigo    usage generique
  [badge-secondary]  emerald   liens/succes
  [badge-accent]     ambre     attention
  [badge-gray]       gris      brouillon, prive
```

### Avatars

```
  avatar-sm   32x32    dans les listes, metadata
  avatar-md   40x40    en-tetes de cards (report, feed)
  avatar-lg   48x48    fiche personnage card
  avatar-xl   64x64    fiche personnage detail, profil
  avatar-placeholder   fond primary-100, texte primary-600
                       initiales centrees
```

### Formulaires

```
  form-label   text-sm font-medium text-gray-700 mb-1
  form-input   w-full rounded-button border-gray-300 shadow-sm
               focus: ring-primary-500 border-primary-500
  form-help    text-sm text-gray-500
  form-error   text-sm text-red-600, input border-red-300
```

### Modal

```
  Backdrop    : bg-gray-500/75, transition opacity
  Container   : bg-white, rounded-card, shadow-dropdown
  Animation   : ease-out 300ms, scale 95->100, opacity 0->100
  Fermeture   : bouton [x], touche Escape, clic hors modal
  Structure   : header (titre + close) | body | footer (actions)
```

---

## 6. Iconographie

### Bibliotheque : Lucide (via @iconify-json/lucide)

Format UnoCSS : `i-lucide-{nom}`

### Icones principales

```
Navigation :
  i-lucide-home         accueil
  i-lucide-compass      explorer
  i-lucide-book-open    parties / CRs
  i-lucide-users        personnages
  i-lucide-bell         notifications
  i-lucide-menu         hamburger mobile
  i-lucide-search       recherche
  i-lucide-user         profil

Actions personnage :
  i-lucide-git-merge    claim (retcon)
  i-lucide-heart        adopt
  i-lucide-git-branch   fork (derivation)
  i-lucide-sparkles     PNJ disponible
  i-lucide-star         PJ actif

Actions generiques :
  i-lucide-plus         ajouter
  i-lucide-edit         modifier
  i-lucide-trash        supprimer
  i-lucide-check        confirmer / succes
  i-lucide-x            fermer / annuler
  i-lucide-link         lien
  i-lucide-share        partager
  i-lucide-flag         signaler
  i-lucide-copy         copier

Etats :
  i-lucide-clock        ephemere, en attente
  i-lucide-lock         prive
  i-lucide-globe        federe / distant
  i-lucide-alert-triangle  avertissement
  i-lucide-info         information
  i-lucide-check-circle succes
  i-lucide-x-circle     erreur
  i-lucide-shield-x     acces refuse
  i-lucide-search-x     pas de resultat

Social :
  i-lucide-message-circle  commentaire
  i-lucide-message-square  commentaire (alt)
  i-lucide-rss             fil d'actualite
  i-lucide-user-plus       nouveau follower

Externe :
  i-simple-icons-mastodon  logo Mastodon
  i-lucide-external-link   lien externe
  i-lucide-upload          upload fichier
  i-lucide-download        telecharger
```

---

## 7. Interactions

### HTMX patterns

```
Recherche live :
  hx-get="/htmx/search/"
  hx-trigger="keyup changed delay:300ms"
  hx-target="#results"

Pagination infinie :
  hx-get="?page=2"
  hx-trigger="revealed"
  hx-swap="afterend"

Formulaire inline :
  hx-post="/endpoint/"
  hx-target="#container"
  hx-swap="innerHTML"

Bouton toggle (follow) :
  hx-post="/follow/"
  hx-target="this"
  hx-swap="outerHTML"
```

### Alpine.js patterns

```
Dropdown :       x-data="dropdown"    toggle/close
Modal :          x-data="modal"       show/hide + body scroll
Toast :          x-data="notifications"  add/remove avec duree
Mention :        x-data="mentionInput"   recherche async + clavier
Tabs :           x-data="tabs"        activeTab/isActive/select
Character status: x-data="characterStatus"  label + class mapping
```

### Transitions

```
Tous les boutons :  transition-colors (couleur)
Cards hover :       transition-shadow (ombre)
Modal enter :       ease-out 300ms, opacity + scale
Modal leave :       ease-in 200ms, opacity
Dropdown :          ease-out 100ms (enter), ease-in 75ms (leave)
```

---

## 8. Responsive

### Breakpoints (UnoCSS standard)

```
sm   640px    tablets portrait
md   768px    tablets landscape
lg   1024px   desktop
xl   1280px   wide desktop
```

### Regles de responsive

```
Mobile first : tout le CSS est mobile par defaut.

Header :
  mobile  -> hamburger menu (Alpine toggle)
  desktop -> navigation horizontale + dropdown user

Grilles :
  mobile  -> 1 colonne
  sm      -> 2 colonnes
  lg      -> 3-4 colonnes

Settings :
  mobile  -> onglets empiles verticalement
  md      -> sidebar + content

Fiche personnage :
  mobile  -> sections empilees
  lg      -> sidebar (avatar + meta) + content (sections)

Editeur CR :
  mobile  -> cast + textarea empiles
  md      -> mention suggestions en dropdown
```

---

## 9. Inventaire des composants

### Existants (templates/components/)

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Character card | `character_card.html` | Carte personnage avec statut, actions hover |
| Report card | `report_card.html` | Carte CR avec auteur, preview, mentions |
| Game card | `game_card.html` | Carte partie avec stats, mode compact |
| Quote card | `quote_card.html` | Citation avec blockquote serif, attribution |
| Modal | `modal.html` | Dialog Alpine.js teleporte, slots header/body/footer |
| Report editor | `report_editor.html` | Editeur CR avec @mention, cast, draft/publish |
| Form fields | `form_fields.html` | Macros input/textarea/select/checkbox/file |

### A creer

| Composant | Description | Wireframes concernes |
|-----------|-------------|---------------------|
| `follow_button.html` | Toggle follow/unfollow HTMX, 2 etats | 04, 05, 07, 10 |
| `link_request_card.html` | Carte demande avec statut, actions, message | 09, 11, 12 |
| `notification_item.html` | Ligne notif avec icone, texte, timestamp, lu/non-lu | 11 |
| `feed_item.html` | Carte CR enrichie pour le fil (PNJ highlights) | 10 |
| `npc_highlight.html` | Mini-carte PNJ avec lien fiche (ambre) | 10, 12 |
| `empty_state.html` | Etat vide generique : icone + message + CTA | Tous |
| `status_banner.html` | Bandeau info sur fiche (demande en cours, QUEUED) | 07, 09 |
| `presence_indicator.html` | Indicateur online/offline pour SharedSequence | 09 |
| `password_strength.html` | Barre de force mot de passe temps reel | 03, 15 |
