# Mapping composants — wireframes

Chaque element de wireframe est mappe a un composant Django template
avec ses props et classes UnoCSS exactes.

Legende :
- `@composant(prop=val)` = `{% include "components/composant.html" with prop=val %}`
- `[shortcut]` = classe UnoCSS definie dans `uno.config.js`
- `(alpine:composant)` = `x-data="composant"` defini dans `main.js`

---

## 01-layout.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Header sticky | `<header class="bg-white border-b border-gray-200 sticky top-0 z-50">` |
| Nav container | `<nav class="container-app flex items-center justify-between h-16">` |
| Logo | `<a class="font-bold text-xl text-gray-900">` + `i-lucide-dice-5` |
| Nav links | `<a class="text-sm font-medium text-gray-600 hover:text-primary-600">` |
| Nav link "Dashboard" | Conditionnel `{% if user.owned_games.exists %}` |
| User dropdown | `(alpine:dropdown)` + `shadow-dropdown rounded-card` |
| Mobile menu | `(alpine:dropdown)` + `sm:hidden` |
| Flash messages | Classes `message-success`, `message-error`, `message-warning`, `message-info` |
| Toast notifs | `(alpine:notifications)` + `fixed bottom-4 right-4 z-50` |
| Loading bar | `htmx-indicator` + `bg-primary-500 h-0.5 fixed top-0 w-full` |
| Footer | `<footer class="bg-white border-t border-gray-200 mt-auto">` |

---

## 02-home.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Hero visiteur | `<section class="text-center py-16 px-4">` |
| Hero titre | `<h1 class="text-4xl font-bold text-gray-900 mb-4">` serif Lora |
| Hero CTA primaire | `[btn-primary btn-lg]` |
| Hero CTA secondaire | `[btn-secondary btn-lg]` |
| Feature grid | `<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">` |
| Feature card | `<div class="card card-body text-center">` + icone Lucide |
| Activite recente | `@report_card` x3 dans `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` |
| Federation info | `<div class="card card-body text-center">` + `i-lucide-globe` |
| Home connecte — parties | `@game_card(compact=True)` dans `<div class="space-y-3">` |
| Home connecte — PNJ | `@npc_highlight` dans `grid grid-cols-2 md:grid-cols-3 gap-3` |

---

## 03-auth.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Container auth | `<div class="max-w-md mx-auto mt-12">` + `[card card-body]` |
| Titre | `<h1 class="text-2xl font-bold text-center mb-6">` |
| Champs | `@form_fields` macros : `input`, `checkbox` |
| Bouton submit | `[btn-primary]` full width `w-full` |
| Liens secondaires | `<a class="link text-sm">` |
| Force mot de passe | `@password_strength(field_id="id_password1")` |
| Erreurs non-champ | `<div class="message message-error mb-4">` |

---

## 04-profile.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Avatar profil | `[avatar-xl]` ou `[avatar-xl avatar-placeholder]` |
| Nom + username | `text-2xl font-bold` + `text-sm text-gray-500` |
| Bio | `<p class="text-gray-600 whitespace-pre-line">` |
| Lien AP | `<a class="link-muted text-sm">` + `i-lucide-link` |
| Bouton Suivre | `@follow_button(target=profile_user, target_type="user")` |
| Bouton Modifier | `[btn-secondary btn-sm]` conditionnel `{% if user == profile_user %}` |
| Section parties | `@game_card(compact=True)` dans `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` |
| Section personnages | `@character_card` dans `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` |
| Section CRs | `@report_card` dans `<div class="space-y-4">` |
| Etats vides | `@empty_state(icon=..., title=..., cta_label=..., cta_url=...)` |
| Edit — formulaire | `@form_fields` macros : `input`, `textarea`, `file_upload`, `checkbox` |
| Edit — submit | `[btn-primary]` + `<a class="link-muted">Annuler</a>` |

---

## 05-games.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Titre + CTA | `flex items-center justify-between` + `[btn-primary]` |
| Recherche | `[form-input]` + `i-lucide-search` |
| Filtres | `<select class="form-input">` systeme + tri |
| Grille parties | `@game_card` dans `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` |
| Pagination | `hx-trigger="revealed"` sur sentinelle |
| Etat vide | `@empty_state(icon="book-open")` |
| Detail — header | `avatar-xl` du owner + `text-2xl font-bold` |
| Detail — Suivre | `@follow_button(target=game, target_type="game")` |
| Detail — CRs | `@report_card` dans `<div class="space-y-4">` |
| Detail — Persos | `@character_card` mini dans `grid grid-cols-2 md:grid-cols-4 gap-3` |
| Creation — form | `@form_fields` + `[btn-primary]` |

---

## 06-reports.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Breadcrumb | `<nav class="text-sm text-gray-500 mb-4">` + `link-muted` |
| Titre CR | `<h1 class="text-2xl font-bold">` |
| Auteur + date | `[avatar-md]` + `text-sm text-gray-500` |
| Cast badges | `[badge-available]` / `[badge-pc]` / `[badge-claimed]` etc. |
| Contenu prose | `<div class="prose-report">` (preset typography UnoCSS) |
| Citations dans CR | `@quote_card` dans `<div class="space-y-3">` |
| Ajouter citation | `[btn-ghost btn-sm]` + `hx-get` -> `_quote_form.html` |
| Actions footer | `[btn-ghost btn-sm]` + icones heart/message/share |
| Editeur — cast | `@report_editor` (composant existant avec Alpine mentionInput) |
| Editeur — sauvegarde auto | `@status_banner(type="info", icon="cloud")` |
| Editeur — publier | `[btn-primary]` |
| Editeur — brouillon | `[btn-secondary]` |
| Editeur — supprimer | `[btn-ghost text-red-600]` -> `@modal` confirmation |

---

## 07-characters.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Recherche FTS | `[form-input]` + `i-lucide-search` + `hx-get hx-trigger="keyup changed delay:300ms"` |
| Filtres statut/systeme | `<select class="form-input">` |
| Grille persos | `@character_card(show_actions=True)` dans `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4` |
| Fiche — avatar | `[avatar-xl]` |
| Fiche — statut | `[badge-available]` / `[badge-pc]` / etc. |
| Fiche — Suivre | `@follow_button(target=character, target_type="character")` |
| Fiche — aide C/A/F | `(alpine:dropdown)` accordeon "Quelle est la difference ?" (voir `00-ux-patterns`) |
| Fiche — boutons action | `[btn-primary]` Adopter + `[btn-secondary]` Reclamer + `[btn-ghost]` Fork |
| Fiche — modal action | `@modal` avec formulaire (voir `09-links`) |
| Banniere demande | `@status_banner(type="info")` — "Vous avez une demande en cours" |
| Apparitions table | `<table class="w-full text-sm">` |
| Citations section | `@quote_card` + `[btn-ghost btn-sm]` ajouter |
| Lignee | `<ul class="text-sm space-y-1 ml-4">` avec indentation |
| Variante distant | `@status_banner(type="info", icon="globe")` — "Instance distante" |
| Etat vide apparitions | `@empty_state(icon="file-text")` |

---

## 08-quotes.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Section titre | `flex items-center justify-between` + `text-heading` |
| Bouton ajouter | `[btn-secondary btn-sm]` + `hx-get` -> form partial |
| Liste citations | `@quote_card` dans `<div id="quote-list" class="space-y-3">` |
| Formulaire ajout | `@form_fields` (textarea content, textarea context, select visibility, input language) |
| Form submit | `[btn-primary btn-sm]` + `hx-post hx-target="#quote-list" hx-swap="afterbegin"` |
| Form annuler | `[btn-ghost btn-sm]` + `hx-get` (vide le container) |
| Menu modifier/suppr | `(alpine:dropdown)` sur chaque `@quote_card` si `quote.author == user` |

---

## 09-links.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Modal adopt/claim/fork | `@modal` + `@form_fields(textarea)` |
| Avertissement QUEUED | `@status_banner(type="warning", icon="alert-triangle")` dans la modal |
| Page demandes — filtres | `(alpine:tabs)` [Recues \| Envoyees] |
| Carte demande | `@link_request_card(request=req, perspective="received"\|"sent")` |
| Modal acceptation | `@modal` + textarea reponse + `[btn-primary]` confirmer |
| Modal revocation pre-publi | `@modal` + `@status_banner(type="error")` + textarea raison |
| Modal revocation post-publi | `@modal` + `@status_banner(type="warning")` + textarea raison |
| Modal renonciation | `@modal` + textarea message + `[btn-danger]` confirmer |
| Grace period toast | `(alpine:notifications)` avec `[btn-ghost btn-sm]` annuler |
| SharedSequence header | `@presence_indicator(participants=...)` |
| SharedSequence editeur | `<textarea class="form-input font-mono resize-y min-h-[400px]">` |
| SharedSequence actions | `[btn-secondary]` sauvegarder + `[btn-primary]` proposer publication |
| Bandeau publication | `@status_banner(type="info")` + `[btn-primary]` valider + `[btn-ghost]` modifications |
| Cross-instance badge | `<span class="i-lucide-globe text-gray-400">` + nom instance |

---

## 10-feed.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| PNJ disponibles | `@npc_highlight` dans `grid grid-cols-2 md:grid-cols-3 gap-3` |
| Sequences section | `[card card-body]` fond `bg-violet-50` |
| Filtres type | `(alpine:tabs)` [Tout \| CRs \| Sequences \| PNJ] |
| Items du fil | `@feed_item(report=report)` dans `<div id="feed-list" class="space-y-4">` |
| Pagination infinie | `hx-get="?page=N" hx-trigger="revealed" hx-swap="afterend"` |
| Etat vide | `@empty_state(icon="rss", cta_label="Explorer les parties")` |
| Bouton follow | `@follow_button(target=..., target_type=...)` |
| Page explorer — onglets | `(alpine:tabs)` [Joueurs \| Parties \| Personnages] |
| Explorer — resultats | `@character_card` / `@game_card` / profil ligne |

---

## 11-notifications.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Header + tout lire | `flex justify-between` + `[btn-ghost btn-sm]` |
| Items | `@notification_item(notification=notif)` dans `<div class="divide-y divide-gray-100">` |
| Badge header | `<span class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-xs">` |
| Pagination | `hx-trigger="revealed"` |
| Parametres — tableau | `<table>` avec `<input type="checkbox">` par canal/type |

---

## 12-gm-dashboard.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Stats cards | `[card card-body]` dans `grid grid-cols-1 sm:grid-cols-2 gap-4` + icones Lucide |
| PNJ avec demandes | `[card]` avec `@link_request_card` inline |
| Bouton traiter | `[btn-primary btn-sm]` lien vers detail |
| PNJ sans demande | `@character_card` dans `grid grid-cols-2 md:grid-cols-4 gap-3` |
| Persos lies | `[card card-body]` avec badges statut + lien sequence |
| Activite recente | timeline `<div class="space-y-3 border-l-2 border-gray-200 pl-4">` |
| Etat vide | `@empty_state(icon="users", cta_label="Écrire un CR")` |

---

## 13-admin.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Dashboard stats | `[card card-body]` dans `grid grid-cols-1 sm:grid-cols-2 gap-4` |
| Signalement carte | `[card card-body]` avec `[badge-accent]` categorie |
| Actions moderation | `[btn-primary btn-sm]` / `[btn-danger btn-sm]` / `[btn-ghost btn-sm]` |
| Modal suppression | `@modal` + `@form_fields(textarea)` + `[btn-danger]` |
| Instance ligne | `[card]` flex avec badges `[badge-available]` / `[badge-accent]` / `badge text-red-600 bg-red-100` |
| Modal blocage | `@modal` + `@status_banner(type="error")` + `[btn-danger]` |

---

## 14-federation.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Recherche globale | `[form-input]` + `[btn-primary]` |
| Onglets portee | `(alpine:tabs)` [Local \| Federe \| Tout] |
| Resultats locaux | `@character_card` / `@game_card(compact=True)` / profil ligne |
| Resultats federes | `hx-get hx-trigger="load"` + `<div class="animate-pulse">` skeleton |
| Badge distant | `<span class="i-lucide-globe text-xs text-gray-400">` + nom instance |
| Profil distant | Layout `04-profile` + `@status_banner(type="info", icon="globe")` |

---

## 15-settings.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Sidebar onglets | `(alpine:tabs)` vertical + `<nav class="w-full md:w-56 space-y-1">` |
| Onglet actif | `bg-primary-50 text-primary-700 font-medium` |
| Formulaires | `@form_fields` macros |
| Zone dangereuse | `<div class="border border-red-200 rounded-card p-4 bg-red-50">` |
| Bouton desactiver | `[btn-ghost]` text-red-600 |
| Bouton supprimer | `[btn-danger]` |
| Sessions actives | `[card]` avec `i-lucide-monitor` / `i-lucide-smartphone` |
| Cle publique | `<pre class="text-xs bg-gray-50 p-3 rounded-card font-mono overflow-x-auto">` |

---

## 16-misc.md

| Element wireframe | Composant / classes |
|-------------------|-------------------|
| Onboarding container | `<div class="max-w-2xl mx-auto">` + `[card card-body]` |
| Stepper | `flex items-center gap-2 text-sm text-gray-500` + active `text-primary-600 font-medium` |
| Bouton retour | `[btn-ghost btn-sm]` |
| Bouton passer | `<a class="link-muted text-sm">` |
| Choix premiere action | `[card card-hover card-body]` dans `grid grid-cols-1 sm:grid-cols-2 gap-4` |
| Modal signalement | `@modal` + radios categorie + `@form_fields(textarea)` + `[btn-danger]` |
| Confirmation signalement | `@modal` + `@status_banner(type="success")` + `[btn-primary]` |
| Page 404 | `@empty_state(icon="search-x", title="Page non trouvée", cta_label="Retour à l'accueil")` |
| Page 403 | `@empty_state(icon="shield-x", title="Accès refusé")` |
| Page 500 | `@empty_state(icon="alert-triangle", title="Erreur serveur")` |
| Modal suppression | `@modal` + `@status_banner(type="error", icon="alert")` + `[btn-danger]` |
