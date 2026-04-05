# Master Plan — Suddenly

**Date** : 2026-04-05
**Statut** : Actif

---

## Etat des lieux

### Ce qui existe (code fonctionnel)

- **Modèles complets** : User, Game, Report, ReportCast, Character, Quote, CharacterAppearance, LinkRequest, CharacterLink, SharedSequence, Follow, FederatedServer, PublicKeyCache
- **Migrations** : toutes créées et commitées (users, games, characters, activitypub)
- **Services** : `LinkService` (Claim/Adopt/Fork avec validation)
- **ActivityPub** : signatures HTTP, inbox avec rate limiting, activities, serializers, wellknown URLs, signals
- **Views** : `CharacterViewSet` (API REST avec DRF)
- **Templates** : `base.html`, composants, `core/home.html`, `users/` (partiel)
- **Infra** : Dockerfile, docker-compose.yml/.dev.yml, Makefile, scripts/init-dev.sh, pyproject.toml

### Ce qui ne fonctionne pas encore

- Les modèles `characters/` n'héritent pas de `BaseModel` (violation convention)
- Pas de slug sur Character (URLs non-humaines)
- Pas d'index FTS PostgreSQL (recherche non-performante)
- Pas de vues/templates HTMX pour characters, quotes, links, feed
- Docker dev setup cassé (chemins et config obsolètes)
- Pas de tests sur les modules critiques
- Migrations jamais appliquées (DB non initialisée)

---

## Tâches restantes — par priorité

### P0 — Fondations (bloquantes)

| # | Tâche | Source | Effort |
|---|-------|--------|--------|
| 1 | **Initialiser la DB** — migrate + createsuperuser + validation | `2026_02_26-premiere-migration.md` (Phases 2-3) | 15 min |
| 2 | **Corriger l'héritage BaseModel** — tous les modèles characters/ doivent hériter de `core.models.BaseModel`, supprimer les champs redondants (id, created_at, updated_at), régénérer les migrations | `task-2026-03-06-characters-models-basemodel-inheritance.md` | 2h |
| 3 | **Fix Docker dev/prod** — aligner Dockerfile avec pyproject.toml, fixer docker-compose.dev.yml, ajouter Make targets | `2026_03_06-docker-dev-prod.md` | 2h |

### P1 — Sécurité et qualité (pré-production)

| # | Tâche | Source | Effort |
|---|-------|--------|--------|
| 4 | **Audit sécurité** — SECRET_KEY, cache clés publiques, validation domaine actor, dédup inbox | `2026_02_26-audit-fixes.md` Phase 1 | 2h |
| 5 | **Outillage statique** — configurer mypy strict + ruff, corriger les erreurs | `2026_02_26-audit-fixes.md` Phase 3 | 1h |
| 6 | **Tests modules critiques** — signatures, inbox handlers, LinkService | `2026_02_26-audit-fixes.md` Phases 4-5 | 4h |

### P2 — Vues et templates (MVP fonctionnel)

| # | Tâche | Source | Effort |
|---|-------|--------|--------|
| 7 | **Templates profil utilisateur** — profile.html + profile_edit.html | `2026_02_26-templates-users-profile.md` | 1h |
| 8 | **Ajouter slug sur Character** — champ + migration + auto-génération | Nouveau | 30 min |
| 9 | **Index FTS PostgreSQL** — migration SQL pour index GIN sur Character(name, description) | Tâche 08 archivée (reste) | 30 min |
| 10 | **Vues HTMX Characters** — liste avec FTS, détail avec historique, suggest inline, search | Tâche 08 archivée (reste) | 3h |
| 11 | **Vues HTMX Quotes** — liste par personnage, formulaire ajout, carte citation | Tâche 09 archivée (reste) | 2h |
| 12 | **Vues HTMX Links** — demande claim/adopt/fork, accepter/refuser, SharedSequence | Tâche 10 archivée (reste) | 3h |
| 13 | **Vues HTMX Follow + Feed** — bouton follow/unfollow, fil d'actualité chronologique | Tâche 11 archivée (reste) | 3h |

### P3 — Fédération complète

| # | Tâche | Source | Effort |
|---|-------|--------|--------|
| 14 | **Envoi activités AP sortantes** — Offer/Accept/Reject sur liens, Follow/Accept | `2026_02_26-audit-fixes.md` Phase 2 | 3h |
| 15 | **Performance N+1** — annotate() sur serializers, db_index manquants | `2026_02_26-audit-fixes.md` Phase 5 | 1h |

### P4 — Design du workflow agentique (amélioration continue)

| # | Tâche | Source | Effort |
|---|-------|--------|--------|
| 16 | **Alternatives pondérées** — enrichir le framework d'audit avec scoring LLM/supervision | `plan_weighted_alternatives.md` | 2h |

---

## User Stories couvertes par priorité

| Priorité | US couvertes | Tâches |
|----------|-------------|--------|
| P0 | — | 1, 2, 3 |
| P1 | — | 4, 5, 6 |
| P2 | US-01 (done), US-02-03, US-04-05, US-06-07, US-08, US-09-11, US-12 | 7-13 |
| P3 | US-22-24 | 14, 15 |
| P4 | — | 16 |

**US non couvertes (post-MVP)** : US-13 (distribution/cast UX), US-15 (file d'attente QUEUED), US-16 (révocation lien), US-17 (fork en chaîne), US-18-19 (éditeur collaboratif SharedSequence), US-20-21 (notifications), US-25-27 (administration/modération).

---

## Dépendances

```
1 (DB init) ──→ 2 (BaseModel) ──→ 8 (slug) ──→ 9 (FTS) ──→ 10 (vues characters)
                                                            ──→ 11 (vues quotes)
                                                            ──→ 12 (vues links)
                                                            ──→ 13 (vues feed)
3 (Docker) ───→ 6 (tests)
4 (sécurité) ─→ 14 (AP sortant)
5 (linters) ──→ 6 (tests)
7 (templates profil) — indépendant
15 (perf) — indépendant
16 (weighted alt) — indépendant
```

---

## Tâches archivées (référence)

| Fichier | Motif |
|---------|-------|
| `07-premiere-migration.md` | Remplacée par `2026_02_26-premiere-migration.md` |
| `08-app-characters.md` | Modèles existent, chemins `apps/` faux |
| `09-app-quotes.md` | Quote dans characters, pas d'app séparée |
| `10-app-links.md` | Modèles + services existent |
| `11-social-feed.md` | Follow existe avec architecture différente |
| `2026_02_26-federation-federated-server.md` | FederatedServer implémenté |
| `2026_03_06-claude-md-omissions.md` | Fixes appliqués |
| `alpine-js-missing-from-claude-md.md` | Doublon, résolu |
