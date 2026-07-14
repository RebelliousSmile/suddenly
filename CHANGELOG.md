# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Personnages** — Méta-modèle narratif interne : lots de traits (`TraitSet`), traits nommés
  à valeur affichée et nullable (`Trait`), actions en texte (`Action`). Transpose une fiche
  narrative (PbtA, FATE, Mist) sans catalogue. Rien n'est jamais évalué : Suddenly affiche.
- **Personnages** — Éditeur inline traits/actions (HTMX + Alpine) réservé au mainteneur de la
  fiche, avec sélecteur de valeur −5/+5, valeur libre ou sans valeur (borne UI, pas de validation).
- **Personnages** — Section « Traits » et bloc « Fiche technique : lien externe » (`sheet_url`)
  sur la fiche publique ; inlines admin pour `TraitSet` (traits + actions).

### Removed
- **Parties** — Sous-système FoundryVTT retiré : modèle `GameSystem`, FK `Game.game_system_ref`,
  tâche de synchronisation `sync_foundry_systems`, commande de gestion associée, picker catalogue
  et recherche inline. `Game.game_system` reste un champ texte libre (aucun catalogue).
- **Explorer** — Facette « systèmes distincts » (`get_distinct_game_systems`) et son invalidation
  de cache retirées.

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
