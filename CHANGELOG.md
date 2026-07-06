# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **Parties** — Catalogue GameSystem avec dropdown HTMX et recherche inline (mode catalogue + personnalisé)
- **Parties** — Synchronisation Foundry VTT via tâche planifiée
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
