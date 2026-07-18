# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.0] - 2026-07-18

### Added
- **Connexion** — « Se connecter avec le Fediverse » : authentification OAuth2
  avec un compte Mastodon (et tout serveur compatible : Pleroma, Akkoma,
  GoToSocial, Pixelfed). Les applications OAuth sont enregistrées à la volée par
  instance — aucune configuration d'identifiants côté admin. Boutons ajoutés sur
  les pages de connexion et d'inscription ; création de compte local à la
  première connexion (jamais rattachée par e-mail, pour éviter tout détournement
  de compte). Réglable via `FEDIVERSE_LOGIN_ENABLED`.
- **Composer & éditeur de scène** — composer de post persistant en sidebar sur
  l'éditeur de scène (mise en page « accueil » : composer à gauche, fil à
  droite), avec bottom-sheets de sélection (personnage / partie) sur mobile et la
  dernière scène affichée sous le composer. Le bouton « Éditer » rouvre le
  composer en mode édition. Placeholder épuré, gating et états vides propres du
  feed.
- **Lecteur de scène** — lecteur de scène dédié avec gating d'édition
  auteur | MJ.
- **Parties** — ordre de fiction explicite pour les scènes ; signalement des
  personnages ayant quitté une scène dans le casting.
- **Personnages** — bouton « Nouveau personnage » sur le profil, affiché dès
  qu'au moins une partie existe ; la section personnages est masquée tant
  qu'aucune partie n'existe, pour éviter un cul-de-sac de création (un personnage
  requiert une partie d'origine qu'on possède).

### Changed
- **Lecture de scène** — suppression de la vue fil groupée/flux ; la lecture est
  fusionnée dans `report_detail`.
- **Éditeur de scène** — actions de post allégées et suppression compatible
  fédération.

### Fixed
- **Langue** — le sélecteur de langue change réellement la langue de l'interface.
- **Parties** — les commentaires Django `{# #}` sont mono-ligne uniquement : du
  texte littéral fuitait dans l'UI.
- **Récupération de mot de passe** — le flux « Mot de passe oublié ? » est
  vérifié de bout en bout. En production, un avertissement est désormais journalisé
  au démarrage lorsque `EMAIL_HOST` n'est pas configuré : sans SMTP, les e-mails
  (dont le lien de réinitialisation) étaient silencieusement ignorés.

## [0.6.0] - 2026-07-15

### Added
- **Flux** — Composer de post en sidebar persistante sur les trois flux
  (Amis / Instance / Fédiverse), avec point d'entrée mobile compact vers le
  composer plein écran. Pool de protagonistes (PJ propres + PNJ maîtrisés) et
  cartes de scène montrant les derniers posts d'une scène.
- **Personnages** — Suggestions de personnages à lier (réclamer / adopter /
  dériver) sur la page de création ; publication de séquence partagée avec
  notifications aux deux parties.
- **Parties** — Puces de tags cliquables, autocomplétion du système de jeu et
  aperçu d'image dans le formulaire.

### Changed
- **Affichage** — Vocabulaire UI unifié : un `Report` s'affiche « scène », un
  `Rapport` « post » (FR + EN).

### Security
- **Fédération** — Durcissement des bords réseau (audit high-findings) :
  résolution WebFinger/acteur via `fetch_ap_json` avec épinglage anti-rebind
  DNS et invalidation de la clé d'acteur à la rotation ; diffusion AP `Create`
  sur `transaction.on_commit` ; ingestion atomique ; correction de la fuite de
  langue thread-local du middleware ; `totalItems` de l'outbox calculé sur la
  collection complète ; `@require_POST` sur les suppressions de traits/actions.

## [0.5.0] - 2026-07-15

### Added
- **Personnages** — Nouvelle vue de création (identité, traits, actions, image
  de couverture), jusqu'ici absente du flux — seule l'édition existait.
- **Personnages** — Liste refondue en cartes produit avec bascule grille/liste.
- **Personnages** — Champs `cover_alt` / `cover_tone` sur `Character`.
- **Personnages** — `Action.character` devient une clé étrangère requise ;
  `Action.__str__` se replie sur le personnage quand `trait_set` est absent.

### Fixed
- **Personnages** — `action_create` renseignait implicitement `action.character` ;
  l'affectation est désormais explicite.
- **Parties** — Protection de `cover.url` contre une valeur absente au
  re-rendu de `game_form`.

### Changed
- **CI** — La suite pytest complète est retirée du hook pre-push (gain de
  vitesse sur chaque push ; la suite complète reste exécutée en CI).

## [0.4.0] - 2026-07-15

### Added
- **Parties** — Refonte du formulaire de création/édition sur le design system.
  Tags alignés sur le modèle de contenu fédéré Mastodon : normalisation
  insensible à la casse (accents préservés) et dédoublonnage. Champ « système de
  jeu » enrichi de suggestions basées sur les 10 libellés les plus utilisés de
  l'instance, plus un validateur anti-doublon (métrique de similarité partagée
  client/serveur) exigeant confirmation sur une saisie très proche mais différente
  (ex. « L'appel de cthulhu » vs « Appel de Cthulhu »).

### Fixed
- **Parties** — La création de partie ignorait entièrement les tags saisis.
- **Docker** — Copie de `design/` dans l'étape frontend-builder avant le build
  (requis par `uno.config.js`).

## [0.3.0] - 2026-07-15

### Added
- **Design system** — Contrat de design 3 couches (tokens / composants / charte) v1.1 → v1.3 :
  migration complète du frontend, trois jeux d'icônes avec rôles et noms accessibles, responsive
  par container queries (invariant `container-not-viewport`).
- **Navigation** — Menu déroulant de compte avec avatar, liens de langue, « Histoires complètes »,
  mur de citations, commande de seed de démo.
- **UI (phase-6)** — Include DRY du menu de compte (`_user_menu_items`), entrée « Stats &
  achievements », partials interventions / rapports, accessibilité (aria-label/aria-hidden,
  cibles tactiles 44 px), gestion des safe-areas mobiles (`pt-safe-t`).
- **Personnages** — Méta-modèle narratif interne : lots de traits (`TraitSet`), traits nommés
  à valeur affichée et nullable (`Trait`), actions en texte (`Action`). Transpose une fiche
  narrative (PbtA, FATE, Mist) sans catalogue. Rien n'est jamais évalué : Suddenly affiche.
- **Personnages** — Éditeur inline traits/actions (HTMX + Alpine) réservé au mainteneur de la
  fiche, avec sélecteur de valeur −5/+5, valeur libre ou sans valeur (borne UI, pas de validation).
- **Personnages** — Section « Traits » et bloc « Fiche technique : lien externe » (`sheet_url`)
  sur la fiche publique ; inlines admin pour `TraitSet` (traits + actions).

### Changed
- **Frontend** — Migration vers les tokens du design system v1.3 (`semantic-*` / `brand-*`) et
  grilles container-query explicites.
- **Navigation** — Consolidation sur le mur `core:quotes` (retrait du doublon `games:quotes_wall`
  et des templates `citations`).

### Removed
- **Parties** — Sous-système FoundryVTT retiré : modèle `GameSystem`, FK `Game.game_system_ref`,
  tâche de synchronisation `sync_foundry_systems`, commande de gestion associée, picker catalogue
  et recherche inline. `Game.game_system` reste un champ texte libre (aucun catalogue).
- **Explorer** — Facette « systèmes distincts » (`get_distinct_game_systems`) et son invalidation
  de cache retirées.

### Fixed
- **i18n / a11y** — Traduction des noms accessibles, correction de deux libellés fautifs.
- **Personnages** — Déduplication de la liste de tags du filtre (piège `distinct` + `ordering`).
- **Histoires** — Alignement de la fiche histoire sur la maquette v3 (retrait de la couverture,
  résumé N rapports, libellés de rapport discrets).
- **Templates** — Conversion des commentaires multi-lignes `{# #}` en `{% comment %}` (Django les
  rendait en texte).

## [0.2.0] - 2026-07-06

### Added
- **ActivityPub** — Fédération sortante complète : Follow/Undo(Follow) signés en tâches Celery, `handle_create`/`update`/`delete` pour les Character, remote follow toggle, Accept/Offer signés
- **ActivityPub** — Stockage media S3/Cloudflare R2 pour les avatars (#94), fallback filesystem si non configuré
- **Personnages** — US-13 à US-17 : distribution du casting de rapport avec @mention scopé, file d'attente de demandes de lien sur les PNJ populaires, révocation de lien accepté, chaînage de forks sur PJ dérivés, arbitrage inline HTMX
- **Personnages** — Bouton "Commencer" + page de composition, migration des tags `JSONField` → `ManyToManyField`
- **Parties** — Rapport : modèle d'entrée atomique typée avec marqueurs narratifs, chaînage en graphe (RapportLink, réponse et parent distant, #64-#66), vue de lecture en fil (thread, US-31 #67)
- **Parties** — Champs `session_date`/`started_at` pour les parties historiques (US-03), filtres de tags, endpoint d'ingestion pour l'export choix-narratifs
- **Explore** — Page de découverte publique `/explore/` avec filtres de feed communautaire
- **Docs** — Application Django docs (5 sections, rendu Markdown)
- **GMH** — Panel admin renommé `/gmh/`, vue des réglages d'instance
- **Core** — Modèle singleton `InstanceSettings`, propagation langue/contexte/email
- **UI** — Éditeur Markdown EasyMDE avec autocomplete @mention, badge de notification non lue sur l'avatar
- **Utilisateurs** — Rôle `is_admin` avec migration de données et commande `set_admin`, templates allauth stylés pour la réinitialisation de mot de passe
- **Wireframes** — Prototypes HTML (component-map, style-guide, audit fédivers, overview), toggle clair/sombre
- **Autres** — Système de prompt de don, refonte de la marque (couleur crimson/violet/néon unifiée)

### Fixed
- Avatar/background ne s'affichaient pas en prod — absence de service `/media/` et pas de volume persistant sur Railway (#98)
- `ALLOWED_HOSTS` : wildcard `*.up.railway.app` et `healthcheck.railway.app` manquants (#96)
- CSS : `box-sizing: border-box` manquant — racine de tous les débordements d'input
- i18n : conflits `.po` après merge, entrées fuzzy et manquantes en français
- Divers correctifs UI : tags input (Entrée soumettait le formulaire), couleurs de badge codées en dur, contraste `--c-muted` (WCAG AA)

### Changed
- Fonts auto-hébergées, storage statique en mode manifest (perf)
- Requêtes explorer mises en cache avec invalidation par signal (perf)
- Palette de couleurs redéfinie autour des types de rapport
- Déploiement : script Alwaysdata, Railway via Dockerfile builder

## [0.1.0] - 2026-04-28

### Added
- **Personnages** — Grille de cartes portrait 2:3, filtrage par tags, préférence de fond par défaut
- **Personnages** — Upload d'avatar, bouton édition sur la page détail
- **Parties** — Upload d'illustration de couverture, affichage sur la page détail
- **Parties** — Champ « système de jeu » en texte libre
- **UI** — Composant `form_switch` (toggle réutilisable pour les champs booléens)
- **UI** — Composant `form_image_upload` (dropzone réutilisable avec prévisualisation et suppression)
- **UI** — Icônes thématiques via `game-icons` pour les états vides
- **UI** — Mode dark/light : variables CSS, theme toggle (lune/soleil), migration des tokens
- **Design** — Palette "dark cosmos" avec accent crimson, design system complet
- **i18n** — Traductions françaises complètes (371 messages), middleware de langue, sélecteur de langue dans le nav
- **i18n** — Préférence `interface_language` dans le profil utilisateur
- **Préférences** — Page dédiée (séparée du profil) : langue, contenu, fond personnage
- **Utilisateurs** — Import/export JSON des parties et personnages
- **Utilisateurs** — Actions groupées sur les listes (édition, suppression, bulk-delete)
- **ActivityPub** — Requêtes sortantes signées, suivi d'instances, recherche fédérée, WebFinger
- **Onboarding** — Flux 3 étapes après inscription
- **Feed** — 3 onglets (Abonnements / Instance / Fediverse)
- **GM Dashboard** — Mes PNJ + demandes en attente
- **Notifications** — Centre de notifications
- **Citations (Quotes)** — Vues HTMX (ajout + carte partielle)
- **Comptes-rendus** — Vues HTMX (détail + création avec CW/visibilité)
- **Séquences partagées** — Éditeur asynchrone (DA-3)
- **Liens** — Guide de flux Claim/Adopt/Fork
- **Hashtags** — Modèle Tag + M2M avec Report
- **Administration** — Dashboard admin, gestion instances/utilisateurs
- **Infrastructure** — Pre-commit hooks (ruff, mypy), CI GitHub Actions, pipeline qualité

### Fixed
- i18n : `SITE_DESCRIPTION` hardcodé en français — traduit via `gettext_lazy`
- i18n : fichiers `.mo` compilés et versionnés (plus de dépendance à `gettext` en déploiement)
- Docker : templates et sources non copiés avant `npm run build` → UnoCSS générait un CSS vide
- Settings : absence de `EMAIL_BACKEND` causait une erreur 500 lors de l'inscription sans SMTP configuré
- ActivityPub : décompression du tuple `verify_signature` avant test booléen
- Utilisateurs : alerte d'import masquée si l'utilisateur a déjà des parties

### Changed
- Préférences de langue déplacées du profil vers une page Préférences dédiée
- Redis et Celery rendus optionnels (fallback cache DB + tâches synchrones)
- Threshold de couverture abaissé à 50% pendant le développement actif
