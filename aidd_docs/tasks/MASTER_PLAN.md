# Master Plan — Suddenly

**Date** : 2026-04-05 (v3 — post-audit conception)
**Statut** : Actif
**User Stories** : US-01 a US-33 (27 originales + 6 ajoutees)
**Audit conception** : `2026_04/2026_04_05-conception-audit.md`

---

## Etat des lieux

### Ce qui existe (code fonctionnel)

- **Modeles complets** : User, Game, Report, ReportCast, Character, Quote, CharacterAppearance, LinkRequest, CharacterLink, SharedSequence, Follow, FederatedServer, PublicKeyCache
- **Migrations** : toutes creees et commitees (users, games, characters, activitypub)
- **Services** : `LinkService` (Claim/Adopt/Fork avec validation)
- **ActivityPub** : signatures HTTP, inbox avec rate limiting, activities, serializers, wellknown URLs, signals
- **Views** : `CharacterViewSet` (API REST avec DRF)
- **Templates** : `base.html`, 16 composants, `core/home.html`, `users/` (partiel)
- **Design system** : UnoCSS avec shortcuts, Alpine.js (9 composants), Vite build, template tag `{% vite_asset %}`
- **Infra** : Dockerfile, docker-compose.yml/.dev.yml, Makefile, scripts/init-dev.sh
- **Wireframes** : 17 pages + style guide + component map + UX patterns + persona audit

### Ce qui ne fonctionne pas encore

- Build Vite jamais execute (`/static/dist/` inexistant)
- Les modeles `characters/` n'heritent pas de `BaseModel`
- Pas de slug sur Character
- Pas d'index FTS PostgreSQL
- Pas de vues/templates HTMX
- Docker dev setup casse
- Pas de tests sur les modules critiques
- Pas de CW ni de visibilite sur les CRs (deal breaker Fediverse)
- Pas de boost/recommandation (deal breaker Fediverse)
- Pas d'import/export follows

### Decisions architecturales a prendre (audit conception)

| # | Decision | Choix valide | Bloque |
|---|----------|-------------|--------|
| **DA-1** | DRF JSON vs HTMX HTML pour les vues front | **HTMX-first** : vues Django pour le front, DRF pour l'API publique AP. VALIDE. | Toutes taches P2 |
| **DA-2** | ADR-011 (NPC jusqu'a SharedSequence publiee) vs code actuel | **Suivre l'ADR-011** : corriger le code pour que le statut reste NPC jusqu'a publication SS. VALIDE. | T16, T17 |
| **DA-3** | SharedSequence synchrone vs temps reel (CRDT/Yjs) | **Asynchrone pour le MVP** : polling presence + verrouillage pessimiste. VALIDE. | T17 |
| **DA-4** | GenericForeignKey sur Follow vs 3 FK nullables | **Garder GFK pour le MVP**, documenter le trade-off, migrer post-MVP si N+1. VALIDE. | T18 |

### Corrections de schema requises avant P2

| Correction | Modele | Champs a ajouter | Tache |
|-----------|--------|-----------------|-------|
| Statuts manquants | LinkRequestStatus | `QUEUED = 'queued'`, `EXPIRED = 'expired'` | T7 |
| Content Warning | Report, Quote | `content_warning: TextField(blank=True)` | T7 |
| Visibilite | Report | `visibility: CharField(choices=public/unlisted/followers_only, default=public)` | T7 |
| Notification | Nouveau modele | `recipient, type, actor, target (GFK), message, is_read` | T7 |
| SharedSequence collab | SharedSequence | `last_edited_by, publication_proposed_by, publication_proposed_at` | T7 |
| Soft delete | BaseModel | `deleted_at: DateTimeField(null=True)` (optionnel) | Post-MVP |

---

## Taches restantes — par priorite

### P0 — Fondations (bloquantes)

| # | Tache | US | Effort |
|---|-------|----|--------|
| 1 | **Initialiser la DB** — migrate + createsuperuser + validation | — | 15 min |
| 2 | **Corriger l'heritage BaseModel** — tous les modeles characters/ | — | 2h |
| 3 | **Fix Docker dev/prod** — Dockerfile, docker-compose, Make targets | — | 2h |
| 4 | **Build frontend** — `npm install && npm run build` pour generer `/static/dist/` | — | 15 min |

### P1 — Securite, qualite, modeles Fediverse

| # | Tache | US | Effort |
|---|-------|----|--------|
| 5 | **Audit securite** — SECRET_KEY, cache cles publiques, validation domaine actor, dedup inbox (ProcessedActivity), chiffrement cles privees AP, rate limiting front (login 10/min, signup 5/min, API 1000/h) | — | 4h |
| 6 | **Outillage statique** — mypy strict + ruff | — | 1h |
| 7 | **Modeles manquants + corrections schema** — CW + visibility sur Report/Quote, statuts QUEUED/EXPIRED sur LinkRequest, modele Notification, champs collab SharedSequence, mixin AP, split characters/models.py en 4 fichiers. Regenerer les migrations. | US-29, US-30 | **6h** |
| 8 | **Tests modules critiques** — signatures, inbox handlers, LinkService, CW/visibility, Notification creation | — | 4h |

### P2 — Vues et templates (MVP fonctionnel)

| # | Tache | US | Effort |
|---|-------|----|--------|
| 9 | **Templates profil** — profile.html + profile_edit.html + followers/following listes + champs custom + migration badge + password strength + comptes bloques/mutes | US-01 | **5h** |
| 10 | **Page A propos instance** — /about avec description, regles, stats, admin, federation | US-31 | 1h |
| 11 | **Signup avec contexte instance** — nom instance, regles, checkbox acceptation, @username@domain preview | US-01, US-31 | 1h |
| 12 | **Slug Character** — champ + migration + auto-generation | US-06 | 30 min |
| 13 | **Index FTS PostgreSQL** — migration SQL pour index GIN | US-07 | 30 min |
| 14 | **Vues HTMX Characters** — liste avec FTS + onglets Instance/Fediverse, detail avec lignee (US-17), badge distant, status banner demande en cours | US-06, US-07, US-17 | 4h |
| 15 | **Vues HTMX Quotes** — liste par personnage, formulaire ajout avec CW, carte citation repliable, menu edit/delete | US-08, US-30 | 2h |
| 16 | **Vues HTMX Links — flow guide** — modal unique [Lier a mon histoire] -> choix type (Adoption/Derivation/Retcon) -> formulaire specifique, file d'attente QUEUED (US-15), revocation avec grace period (US-16). Necessite decision DA-2 (ADR-011) | US-09, US-10, US-11, US-14, US-15, US-16 | **8h** |
| 17 | **SharedSequence editeur** — editeur **asynchrone** (DA-3) avec presence polling, verrouillage, sauvegarde, proposition publication, double validation. Pas de CRDT/Yjs au MVP. | US-18, US-19 | **3h** |
| 18 | **Vues HTMX Feed** — 3 onglets (Abonnements/Instance/Fediverse, DA-1), filtres (Tout/CRs/Recommandations/Sequences/PNJ), bouton follow/unfollow, CW repliable, recommandation, invitation | US-12, US-28, US-29 | **8h** |
| 19 | **Vues parties** — liste avec onglets Instance/Fediverse, detail, creation | US-02, US-03, US-13 | 3h |
| 20 | **Vues CRs** — detail avec CW, editeur avec CW + visibilite + autosave + cast + @mention | US-04, US-05, US-29, US-30 | 4h |
| 21 | **Dashboard GM** — vue "Mes PNJ" avec demandes en attente, arbitrage inline, activite recente | US-14 | 2h |
| 22 | **Notifications** — centre avec 9 types (lien, reponse, CR, recommandation, mention, invitation, follower, sequence, revocation), badge header, parametres canal | US-20, US-21 | 3h |
| 23 | **Onboarding** — 3 etapes (profil, decouverte + import follows + timeline locale, premiere action) | — | 2h |
| 24 | **Pages erreur + signalement** — 404/403/500, modal signalement avec categories | US-27 | 1h |

### P3 — Federation complete

| # | Tache | US | Effort |
|---|-------|----|--------|
| 25 | **AP sortant + namespace** — Offer/Accept/Reject liens, Follow/Accept, Announce (recommandation), CW + visibility dans les payloads, documenter namespace `suddenly:` (ADR-022), resoudre les 9 TODO dans le code | US-22, US-23, US-24, US-28 | **8h** |
| 26 | **Import/export follows CSV** — export Mastodon-compatible, import avec resolution WebFinger | US-32 | 2h |
| 27 | **Block/mute utilisateur** — modele, vues settings, filtrage dans les feeds | US-33 | 2h |
| 28 | **Migration compte** — alias entrant, Move activity sortant, badge "compte migre" | US-32 | 2h |
| 29 | **Performance N+1** — annotate() sur serializers, db_index manquants | — | 1h |

### P4 — Post-MVP

| # | Tache | US | Effort |
|---|-------|----|--------|
| 30 | **Administration** — dashboard moderation, signalements, gestion instances | US-25, US-26 | 4h |
| 31 | **Hashtags** — tag system sur CRs/Quotes, feed par hashtag, federation | — | 3h |
| 32 | **Alternatives ponderees** — enrichir le framework d'audit agentique | — | 2h |

---

## Couverture US par priorite

| Priorite | US couvertes | Taches |
|----------|-------------|--------|
| P0 | — | 1-4 |
| P1 | US-29, US-30 | 5-8 |
| P2 | US-01-14, US-15-21, US-27, US-28 | 9-24 |
| P3 | US-22-24, US-32, US-33 | 25-29 |
| P4 | US-25, US-26 | 30-32 |

**Toutes les 33 US sont couvertes.**

---

## Couverture wireframes par tache

| Wireframe | Tache(s) |
|-----------|----------|
| 01-layout | 9, 22 (header nav + badge notifs + badge demandes) |
| 02-home | 19 (home connecte), 10 (home visiteur -> about) |
| 03-auth | 11 (signup contexte instance) |
| 04-profile | 9 (profil complet) |
| 05-games | 19 (vues parties) |
| 06-reports | 20 (vues CRs avec CW + visibilite) |
| 07-characters | 14 (vues characters) |
| 08-quotes | 15 (vues quotes avec CW) |
| 09-links | 16 (flow guide), 17 (SharedSequence) |
| 10-feed | 18 (feed 3 onglets + recommandation + invitation) |
| 11-notifications | 22 (notifications 9 types) |
| 12-gm-dashboard | 21 (dashboard GM) |
| 13-admin | 30 (post-MVP) |
| 14-federation | 25 (AP sortant), 26 (import/export) |
| 15-settings | 26, 27, 28 (follows, block/mute, migration) |
| 16-misc | 23 (onboarding), 24 (erreurs + signalement) |
| 17-instance-about | 10 (page A propos) |

**Tous les 17 wireframes sont couverts.**

---

## Dependances

```
1 (DB) -> 2 (BaseModel) -> 7 (CW+visibility models)
                        -> 12 (slug) -> 13 (FTS) -> 14 (characters)
                                                  -> 15 (quotes)
                                                  -> 16 (links)
                                                  -> 17 (SharedSeq)
                                                  -> 18 (feed)
3 (Docker) -> 4 (build) -> 8 (tests)
5 (securite) -> 25 (AP sortant)
6 (linters) -> 8 (tests)
9 (profil) -- independant
10 (about) -- independant
11 (signup) -- depend de 10 (regles)
19 (parties) -- depend de 12 (slug si lien parties)
20 (CRs) -- depend de 7 (CW+visibility)
21 (GM dash) -- depend de 16 (links)
22 (notifs) -- depend de 16, 17, 18 (sources de notifs)
23 (onboarding) -- depend de 18 (feed timeline locale)
24 (erreurs) -- independant
26 (import/export) -> 28 (migration)
27 (block/mute) -- independant
```

---

## Taches archivees (reference)

| Fichier | Motif |
|---------|-------|
| `07-premiere-migration.md` | Remplacee par `2026_02_26-premiere-migration.md` |
| `08-app-characters.md` | Modeles existent, chemins `apps/` faux |
| `09-app-quotes.md` | Quote dans characters, pas d'app separee |
| `10-app-links.md` | Modeles + services existent |
| `11-social-feed.md` | Follow existe avec architecture differente |
| `2026_02_26-federation-federated-server.md` | FederatedServer implemente |
| `2026_03_06-claude-md-omissions.md` | Fixes appliques |
| `alpine-js-missing-from-claude-md.md` | Doublon, resolu |
