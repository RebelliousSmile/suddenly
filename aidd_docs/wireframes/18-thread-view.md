# 18 — Fil federe : lecture de compte-rendu (US-31)

## Concept

Le fil federe permet de lire un compte-rendu compose de multiples Rapports
(Description, Action, Discussion, Narration) en mode flux chronologique
ou en mode groupe par rapport parent. Inspire des fils de conversation email.

---

## Page de lecture (`/games/<pk>/reports/<pk>/thread/`)

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  City of Mist > Session 12 > Fil                                |
|  (breadcrumb link-muted text-sm)                                 |
|                                                                  |
|  +-----------------------------------------------------+        |
|  | (list) Flux | (layers) Groupe |                      |        |
|  +-----------------------------------------------------+        |
|  (alpine:tabs, par defaut "Flux")                                |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Mode Flux (chronologique)

Tous les Rapports dans l'ordre d'arrivee, differencies visuellement par type.

```
+------------------------------------------------------------------+
|  id="thread-items"                                               |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (book-open) DESCRIPTION              il y a 2h  (globe)?   |  |
|  |                                                             |  |
|  | card bg-indigo-50 border-l-4 border-indigo-400              |  |
|  |                                                             |  |
|  | La nuit tombait sur le Quartier des Reflets. Les neons      |  |
|  | clignotaient dans la bruine, projetant des ombres           |  |
|  | dansantes sur les murs de brique humide...                  |  |
|  |                                                             |  |
|  | par @alice · City of Mist                                   |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (message-circle) DISCUSSION           il y a 1h45          |  |
|  |                                                             |  |
|  | card bg-emerald-50 border-l-4 border-emerald-400            |  |
|  |                                                             |  |
|  | +------+  Viktor :                                         |  |
|  | |avatar|  "Tu es en retard. L'Oracle n'attend pas."        |  |
|  | +------+                                                    |  |
|  |                                                             |  |
|  | par @alice · personnage: Viktor                             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (zap) ACTION                          il y a 1h30          |  |
|  |                                                             |  |
|  | card bg-amber-50 border-l-4 border-amber-400               |  |
|  |                                                             |  |
|  | Lyra pousse la porte du bar. Son manteau ruisselle          |  |
|  | de pluie. Elle pose un dossier sur la table sans            |  |
|  | un mot.                                                     |  |
|  |                                                             |  |
|  | par @bob · personnage: Lyra                                 |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (feather) NARRATION                   il y a 1h             |  |
|  |                                                             |  |
|  | card bg-violet-50 border-l-4 border-violet-400             |  |
|  |                                                             |  |
|  | Le silence s'installe. Dehors, le bruit d'une              |  |
|  | sirene s'eloigne. Les trois personnages se regardent,       |  |
|  | conscients que rien ne sera plus comme avant.               |  |
|  |                                                             |  |
|  | par @alice · narration                                      |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  (hx-trigger="revealed" -> page suivante)                        |
|                                                                  |
+------------------------------------------------------------------+
```

### Codes couleur par type de Rapport

| Type | Fond | Bordure gauche | Icone |
|------|------|---------------|-------|
| Description | `bg-indigo-50` | `border-indigo-400` | `i-lucide-book-open` |
| Discussion | `bg-emerald-50` | `border-emerald-400` | `i-lucide-message-circle` |
| Action | `bg-amber-50` | `border-amber-400` | `i-lucide-zap` |
| Narration | `bg-violet-50` | `border-violet-400` | `i-lucide-feather` |

---

## Mode Groupe (par rapport parent)

Les Rapports sont regroupes par "scene" (rapport parent). Navigation
horizontale par swipe entre les groupes.

```
+------------------------------------------------------------------+
|                                                                  |
|  Scene 1 de 4            [<]  [1] [2] [3] [4]  [>]             |
|  "L'arrivee au bar"                                              |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | card swipeable (Alpine.js x-data="threadGroup")             |  |
|  |                                                             |  |
|  | +--------------------------------------------------------+ |  |
|  | | (book-open) DESCRIPTION                                 | |  |
|  | | La nuit tombait sur le Quartier des Reflets...           | |  |
|  | +--------------------------------------------------------+ |  |
|  |                                                             |  |
|  | +--------------------------------------------------------+ |  |
|  | | (message-circle) DISCUSSION                             | |  |
|  | | Viktor : "Tu es en retard."                             | |  |
|  | +--------------------------------------------------------+ |  |
|  |                                                             |  |
|  | +--------------------------------------------------------+ |  |
|  | | (zap) ACTION                                            | |  |
|  | | Lyra pousse la porte du bar...                          | |  |
|  | +--------------------------------------------------------+ |  |
|  |                                                             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  <- Swipe gauche : Scene precedente                              |
|  -> Swipe droite : Scene suivante                                |
|  (Alpine.js: @touchstart, @touchend, calcul delta)               |
|                                                                  |
+------------------------------------------------------------------+
```

### Navigation entre groupes

```
  Indicateur de position (dots ou numerotation) :

  [<]  ● ○ ○ ○  [>]
       ^
       Scene active

  Clavier : fleches gauche/droite
  Touch : swipe horizontal
  Clic : boutons [<] [>] ou dots
```

---

## Header de rapport individuel (partiel reutilisable)

```
+------------------------------------------------------------+
| (icone-type) TYPE                     timestamp  (globe)?  |
|                                                             |
|  Contenu du rapport...                                      |
|                                                             |
|  par @auteur · contexte (personnage ou partie)              |
|                                                             |
|  ── actions ──────────────────────────────────────────────  |
|  (heart)  (sparkles) Recommander  (flag) ...               |
+------------------------------------------------------------+
```

Le badge `(globe)` apparait si le rapport vient d'une instance distante.

---

## Composant Alpine.js : threadGroup

```javascript
Alpine.data('threadGroup', () => ({
  currentScene: 0,
  totalScenes: 0,
  touchStartX: 0,

  init() {
    this.totalScenes = this.$el.querySelectorAll('[data-scene]').length
  },

  next() {
    if (this.currentScene < this.totalScenes - 1) this.currentScene++
  },

  prev() {
    if (this.currentScene > 0) this.currentScene--
  },

  onTouchStart(e) { this.touchStartX = e.touches[0].clientX },
  onTouchEnd(e) {
    const delta = e.changedTouches[0].clientX - this.touchStartX
    if (delta > 50) this.prev()
    else if (delta < -50) this.next()
  },
}))
```

---

## HTMX patterns

```
Mode Flux :
  hx-get="/games/{pk}/reports/{pk}/thread/?mode=flux&page=2"
  hx-trigger="revealed"
  hx-swap="afterend"
  hx-target="#thread-items"

Mode Groupe :
  Pas de HTMX — tout charge en une fois (scenes pre-rendues)
  Navigation cote client (Alpine.js show/hide)

Toggle mode :
  hx-get="/games/{pk}/reports/{pk}/thread/?mode=group"
  hx-target="#thread-content"
  hx-push-url="true"
```

---

## Mapping composants UnoCSS

| Element | Classes |
|---------|---------|
| Rapport Description | `card bg-indigo-50 border-l-4 border-indigo-400 card-body` |
| Rapport Discussion | `card bg-emerald-50 border-l-4 border-emerald-400 card-body` |
| Rapport Action | `card bg-amber-50 border-l-4 border-amber-400 card-body` |
| Rapport Narration | `card bg-violet-50 border-l-4 border-violet-400 card-body` |
| Scene container | `card card-body overflow-hidden` |
| Dots navigation | `flex items-center gap-2 justify-center` |
| Dot active | `w-2 h-2 rounded-full bg-primary-500` |
| Dot inactive | `w-2 h-2 rounded-full bg-gray-300` |
| Badge distant | `instance-badge` (text-xs text-gray-500 + i-lucide-globe) |
| Breadcrumb | `text-sm text-gray-500` + `link-muted` |
| Mode tabs | `(alpine:tabs)` avec border-b |

---

## Responsive

```
Mobile (< 640px) :
  - Mode flux : cards pleine largeur, scroll vertical
  - Mode groupe : swipe natif, dots en bas

Desktop (> 1024px) :
  - Mode flux : max-w-3xl centre
  - Mode groupe : fleches [<] [>] visibles, dots centres
```

---

## Dependances

- Modele `Report` existant (champ `type` a ajouter ou inferer du contenu)
- Relation parent-enfant entre Reports (champ `parent` a ajouter si absent)
- Composant Alpine.js `threadGroup` (nouveau)
- Pas de dependance externe (pas de librairie swipe)
