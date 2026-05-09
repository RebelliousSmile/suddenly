# Audit data-layer — Django ORM — full-app

**Date** : 2026-05-09
**Stack** : Django 5.x ORM + PostgreSQL + DRF + django-htmx + Celery (Redis fallback DatabaseCache + EAGER)
**Scope** : full-app (home, explorer, characters, games, federation, admin, API DRF)
**Checklist** : `aidd_docs/templates/dev/data_checklist_django-orm.md`
**Baseline** : `aidd_docs/tasks/audits/baselines/full-app.json`

---

## Méthode & limites

- Analyse statique du code (lecture des routes hot, services, modèles, settings, tâches Celery)
- **Aucune exécution live** : django-debug-toolbar absent, pas de `pg_stat_statements`, pas de session de profilage
- Compteurs déterministes extraits du code, à reproduire par l'utilisateur dès que F0 (toolbar + silk) sera installé
- Latence p95 non mesurée — ne sera pas le signal porteur ; les compteurs requêtes/payload/Celery fan-out le sont

---

## Baseline déterministe (extrait JSON)

| Route | Queries/req (estim.) | Source | Notes |
|---|---|---|---|
| `/` (home) | ~6 | `core/views.py:18` → `get_recent_public_reports` | select_related + prefetch OK |
| `/explorer/` | ~10-12 | `core/views.py:23` (2 paginated + 3 distinct aggregations) | tags/systems aggregations non cachées |
| `/about/` | **4 .count() systématiques** | `core/views.py:81-95` (`activitypub/views.py:138-141` idem) | Hardcoded, jamais cachés |
| `/admin-dashboard/` | ~5 .count() | `core/admin_views.py:30-36` | Trafic faible, OK |
| `/u/<user>/` | ~5 | `users/views.py:57` (followers/following) | `.exists()` correct |
| `/inbox/` (AP) | ~3 + verify_signature DB | `activitypub/inbox.py:45` | Hot federation path |

Anti-patterns count :
- `@cache_page` decorator : **0 occurrence** dans tout `suddenly/`
- `cache.get_or_set` : **0**
- Fragment cache `{% cache %}` : **0**
- `assertNumQueries` dans tests : **0**
- `.icontains` sans index full-text : **7 occurrences**
- `.exists()` / `.count()` dénombrés : 32 (la majorité légitimes)

Background jobs :
- `broadcast_activity` : 1 `deliver_activity.delay()` par follower, **pas de mutualisation par sharedInbox** (`activitypub/tasks.py:235-276`)
- `refresh_remote_actors` : 100 `fetch_remote_actor.delay()` simultanés toutes les 24 h, **sans rate limit par domaine** (`activitypub/tasks.py:484-494`)

---

## Checklist learnings

- `[gap] §3: signals + transaction.on_commit pour broadcast_activity` — broadcast_activity est appelé directement dans services (pas via signal), mais §3 ne couvre pas le pattern Celery fan-out per-recipient sans shared inbox
- `[gap] §4: pas de bullet sur le risque LocMemCache + multi-worker gunicorn` — DatabaseCache fallback documenté en prod, mais en dev (default LocMem) `cache.get_or_set` est invisible cross-worker — à mentionner explicitement
- `[antipattern] DRF API qui réimplémente la logique service` — **2+ occurrences** : `CharacterViewSet.claim/adopt/fork` (vues 145-250) bypass `LinkService.create_request`, `LinkRequestViewSet.accept` (274-347) duplique `LinkService.accept_request`. **Pattern projet, non générique** → roadmap F1 + 1 issue, pas d'élévation en règle normative (single bug class par convention `feedback_bug_vs_antipattern.md`)
- `[grep] grep -rn "@cache_page\|cache\.get_or_set\|{% cache %}" suddenly/` — surface **0 résultat** sur tout le codebase, signal F1 fort
- `[grep] grep -rn "icontains\|istartswith" suddenly/` — surface 7 sites, dont 1 hot path API non indexé (search action)
- `[reword] §1: « éviter N+1 sur reverse FK »` → « auditer chaque queryset templates qui itère un reverse FK ; ajouter `prefetch_related` même si seule la `count` est utilisée (sinon `Count` annotation) »
- `[unit] §0: query = un appel ORM (`SELECT`/`INSERT`/`UPDATE`)` — formulation ambiguë sur `prefetch_related` qui émet 2 requêtes ; à clarifier en « une requête réseau au DB, pas un appel Python `.all()` »

---

## §0 — Pre-flight

| # | Item | Statut | Note |
|---|------|--------|------|
| 0.1 | Stack détecté & versions notées | 🟢 | Django 5.x + PostgreSQL + DRF (CLAUDE.md + `pyproject.toml`) |
| 0.2 | Hot routes identifiées | 🟢 | `/explorer/`, `/about/`, `/inbox/`, `CharacterViewSet.search` |
| 0.3 | Baseline 3-5 runs capturée | 🔴 | django-debug-toolbar absent → F0 |
| 0.4 | Baseline persistée JSON | 🟢 | `baselines/full-app.json` |
| 0.5 | Monorepo / multi-app vérifié | 🟢 | Mono-app Django, 5 apps internes |

## §1 — Query patterns (N+1, eager-load, batch)

| # | Item | Statut | Note |
|---|------|--------|------|
| 1.1 | `select_related` sur FK suivies en template | 🟢 | 82 occurrences dans 20 fichiers, couverture des hot paths (`core/services.py`, `games/services.py`) |
| 1.2 | `prefetch_related` sur reverse FK / M2M | 🟢 | `build_character_queryset` (`characters/services.py:338-376`), `build_game_queryset` (`games/services.py`) |
| 1.3 | `only()` / `defer()` sur listes paginées | 🔴 | **0 usage** — `Character`/`Game` listings tirent toutes les colonnes incl. `description` TEXT |
| 1.4 | `count()` / `exists()` au lieu de `len(qs)` | 🟢 | Pattern correct appliqué (`users/views.py:57-66`, `core/admin_views.py`) |
| 1.5 | `bulk_create` / `bulk_update` pour > 5 inserts | 🟡 | **0 usage** — `publish_report` (`games/services.py:66-100`) crée NPC + appearances dans une boucle (~5-10 items, borné, OK) |
| 1.6 | `in_bulk()` au lieu de N `.get(pk=)` | 🟢 | Pattern non utilisé mais inutile ici (pas de lookup massif par PK) |
| 1.7 | Query inside loop interdit | 🟡 | `users/settings_views.py:298` itère sur `Game.objects.filter(...)` ; benin (dict comprehension de < 50 items) |
| 1.8 | Aggregations via `Count` annotation, pas `.count()` en boucle | 🟢 | `build_*_queryset` utilisent `Count(..., filter=Q(...))` |

## §2 — Pagination & limites

| # | Item | Statut | Note |
|---|------|--------|------|
| 2.1 | `Paginator` ou `CursorPagination` sur listes | 🟢 | `Paginator` utilisé sur explorer (`core/views.py:35`, etc.) |
| 2.2 | Pas de `qs.all()` non borné dans une vue | 🟢 | RAS |
| 2.3 | Slicing `[:N]` cohérent (Python vs SQL) | 🟢 | Slicing SQL via `[:limit]` côté queryset |
| 2.4 | Curseur stable (PK ou updated_at) | 🟡 | Tri par `updated_at` sur Game ; risque de doublons en bord de page si égalité (faible volume MVP) |
| 2.5 | Cap server-side sur `?limit=` | 🔴 | `activitypub/federation_views.py:164` `[:5]` hardcodé OK ; mais DRF `CharacterViewSet.search` (`characters/views.py:92`) sans pagination ni `[:N]` |

## §3 — Real-time / change streams / signals

| # | Item | Statut | Note |
|---|------|--------|------|
| 3.1 | `post_save` signals enveloppés `transaction.on_commit` | 🟡 | Non audité ligne par ligne ; à vérifier sur `Report.published → broadcast_activity` |
| 3.2 | Pas de Celery `.delay()` dans `transaction.atomic` sans `on_commit` | 🔴 | `LinkService.accept_request` (`characters/services.py:132-214`) appelle des side-effects ; `broadcast_activity` à auditer |
| 3.3 | Pas de DB query dans signal handler synchrone | 🟢 | RAS visible |
| 3.4 | Channels / WebSocket : N/A | N/A | Pas de Channels dans le projet |
| 3.5 | Fan-out fédération mutualisé par sharedInbox | 🔴 | `broadcast_activity` (`activitypub/tasks.py:235-276`) émet 1 task par follower même même domaine — F2 |

## §4 — Caching

| # | Item | Statut | Note |
|---|------|--------|------|
| 4.1 | `@cache_page` sur routes anonymes hot | 🔴 | **0 usage** — `/` `/explorer/` `/about/` totalement non cachés |
| 4.2 | `cache.get_or_set` sur aggregations coûteuses | 🔴 | **0 usage** — distinct tags + game_systems re-agrégés à chaque hit |
| 4.3 | Fragment caching `{% cache %}` sur listings | 🔴 | **0 usage** |
| 4.4 | Cache backend cohérent multi-worker | 🟢 | Prod : Redis si dispo sinon DatabaseCache (`config/settings/production.py`) |
| 4.5 | LocMemCache jamais utilisé en prod | 🟢 | Conditional CACHES bien documenté |
| 4.6 | Cache invalidation explicite (signals/save) | N/A | Aucun cache → pas d'invalidation à auditer |
| 4.7 | TTL borné (≤ 5 min) sur données dynamiques | N/A | Idem |

## §5 — Payload

| # | Item | Statut | Note |
|---|------|--------|------|
| 5.1 | `gzip` / `brotli` activé | 🟡 | WhiteNoise compresse les statiques ; pas de `GZipMiddleware` actif sur les responses HTML |
| 5.2 | DRF `pagination_class` avec page_size raisonnable | 🟡 | Default DRF, pas de pagination explicite sur les actions custom |
| 5.3 | `JsonResponse` strictement nécessaire (pas de SSR doublé en JSON) | 🟢 | HTMX-first ; JSON seulement sur DRF API + ActivityPub |
| 5.4 | Images servies via `WEBP`/`AVIF` ou CDN | 🟡 | `ImageField` brut sur Character.avatar — pas de conversion |
| 5.5 | Static `ManifestStaticFilesStorage` | 🔴 | `CompressedStaticFilesStorage` au lieu de `CompressedManifestStaticFilesStorage` (`config/settings/base.py:131-132`) — pas de cache busting via hash |

## §6 — Quota & cost

| # | Item | Statut | Note |
|---|------|--------|------|
| 6.1 | `CONN_MAX_AGE` configuré | 🟢 | 60s en prod (`production.py`) |
| 6.2 | `pgbouncer` ou pool externe | 🟡 | Non documenté ; OK si déploiement ≤ 2 workers, à revoir au scale |
| 6.3 | Celery beat n'inonde pas la queue | 🟡 | `cleanup_expired_quotes` (3600s) + `refresh_remote_actors` (86400s) raisonnables ; mais 100 fetch simultanés sans throttle (`tasks.py:484`) |
| 6.4 | Fan-out fédération coût borné | 🔴 | `broadcast_activity` linéaire en N followers — F2 |
| 6.5 | Pas de `.all()` en boucle de tâche planifiée | 🟢 | Slicing `[:100]` sur `refresh_remote_actors` |

## §7 — Sécurité & access control

| # | Item | Statut | Note |
|---|------|--------|------|
| 7.1 | DRF permissions sur ViewSets | 🟢 | Vu dans `characters/views.py` |
| 7.2 | `select_for_update()` sur mutations critiques | 🟢 | `LinkService.create_request` (services.py:86-130) lock parent (cf. DEC-035) |
| 7.3 | Vue HTMX state-mutating en `@require_POST` | 🟢 | Pattern documenté `htmx-patterns.md` rule |
| 7.4 | Rate limit auth + inbox | 🟢 | `core/middleware.py:69` AuthRateLimit + `activitypub/inbox.py:37` django-ratelimit |
| 7.5 | DRF API ne contourne pas la couche service | 🔴 | `CharacterViewSet.claim/adopt/fork` (`characters/views.py:145-250`) bypass `LinkService.create_request` — race condition + aucun QUEUED ; `LinkRequestViewSet.accept` (274-347) duplique service. **Bug + duplication** → F1 |

## §8 — Schema & indexing

| # | Item | Statut | Note |
|---|------|--------|------|
| 8.1 | `Meta.indexes` sur colonnes filtrées en hot | 🟢 | Game, Report, Character, LinkRequest, CharacterLink, Follow ont des indexes |
| 8.2 | Index composites couvrant les `WHERE + ORDER BY` | 🟡 | `Game(is_public, updated_at)` OK ; pas d'index combiné sur `Character(remote, status)` |
| 8.3 | `unique_together` / `UniqueConstraint` au lieu de `unique=True` cross-fields | 🟢 | `CharacterAppearance` unique_together OK |
| 8.4 | FTS via `SearchVector` + GinIndex | 🟡 | `build_character_queryset` (`characters/services.py:366`) utilise `SearchVector("french")` mais **pas de GinIndex persisté** — recalcul du vecteur à chaque requête |
| 8.5 | Recherche textuelle hot path utilise FTS, pas `icontains` | 🔴 | DRF `CharacterViewSet.search` (`characters/views.py:92`) `name__icontains=...` ; idem `games/front_views.py:531,658`, `users/settings_views.py:393` |
| 8.6 | `pg_trgm` extension activée pour fuzzy search | 🔴 | Non détecté (pas d'extension dans migrations) |
| 8.7 | `EXPLAIN ANALYZE` runbook documenté | 🔴 | Pas de notes / runbook |

## §9 — Background jobs & async

| # | Item | Statut | Note |
|---|------|--------|------|
| 9.1 | Celery `task_acks_late=True` ou idempotence | 🟡 | `deliver_activity` retry sur 5xx, idempotence non auditée explicitement |
| 9.2 | `transaction.on_commit` avant `.delay()` | 🔴 | À auditer ; cf §3.2 |
| 9.3 | EAGER fallback sain en CI/dev | 🟢 | `production.py` : `CELERY_TASK_ALWAYS_EAGER=True` si pas de Redis |
| 9.4 | Tasks longues bornées | 🟢 | `CELERY_TASK_TIME_LIMIT=30min` (`base.py`) |
| 9.5 | Retry strategy explicite | 🟢 | `deliver_activity` retry sur 5xx (`tasks.py:186-232`) |
| 9.6 | Rate limit sortant fédération | 🔴 | `refresh_remote_actors` 100 fetch simultanés sans throttle par domaine |

## §10 — Verification & non-regression

| # | Item | Statut | Note |
|---|------|--------|------|
| 10.1 | `assertNumQueries` sur tests des routes hot | 🔴 | **0 occurrence** dans `tests/` |
| 10.2 | `pytest-django` configuré + `--reuse-db` | 🟢 | `make check` documenté CLAUDE.md |
| 10.3 | django-debug-toolbar en dev | 🔴 | Absent — F0 |
| 10.4 | django-silk staging | 🔴 | Absent |
| 10.5 | `pg_stat_statements` actif | 🔴 | Non détecté |
| 10.6 | CI fail si N+1 introduit | 🔴 | Pas de garde |

## §11 — Checklist self-audit

Voir section `## Checklist learnings` ci-dessus.

---

## Anti-patterns relevés (table)

| Pattern | Fichier:ligne | Pourquoi rejeté | Remédiation |
|---|---|---|---|
| `name__icontains=q` sur hot path API | `characters/views.py:92` | LIKE %term% → seq scan, pas d'index B-tree | FTS via `build_character_queryset` ou `pg_trgm` |
| `name__icontains=q` sur typeahead | `games/front_views.py:531,658` ; `users/settings_views.py:393` | Même cause | `pg_trgm` GinIndex sur `name` |
| 4× `.count()` non cachés sur `/about/` | `core/views.py:88-93` ; `activitypub/views.py:138-141` | Page anonyme hit fréquent, comptes peu volatiles | `cache.get_or_set("about_stats", ..., 600)` |
| Distinct tags non cachés sur `/explorer/` | `core/views.py:41-44, 61-65` | Aggregation full-table à chaque hit | `cache.get_or_set("explorer_tags", ..., 300)` |
| 0 `@cache_page` sur routes anonymes | global | Pression DB inutile | F1 décorateur `cache_page(60)` minimum |
| `CompressedStaticFilesStorage` au lieu de Manifest | `config/settings/base.py:131` | Pas de cache busting hash → headers `Cache-Control` longs impossibles | Switch `CompressedManifestStaticFilesStorage` |

---

## Roadmap

### F0 — Stabilisation (effort: 1h, risque: nul)

1. Installer `django-debug-toolbar` (dev only, gated par `DEBUG=True`)
2. Capturer baseline live 3-5 runs sur `/`, `/explorer/`, `/about/`, `/u/<demo>/`
3. Activer `pg_stat_statements` (extension Postgres + `shared_preload_libraries`) en staging
4. Mettre à jour `baselines/full-app.json` avec compteurs réels

**Critère succès** : compteurs queries/req mesurés (médiane 3-5 runs) avec min/max ; remplace les `~estim.` du baseline JSON.

### F1 — Quick wins (effort: 1 jour, risque: faible)

1. **Refactor DRF `CharacterViewSet.claim/adopt/fork`** → délégation à `LinkService.create_request` (`characters/views.py:145-250`). **Risque** : race condition actuelle (pas de `select_for_update`), aucun blocage QUEUED → 2 requêtes simultanées créent 2 `LinkRequest` PENDING. **Issue tracker** créée.
2. **Refactor DRF `LinkRequestViewSet.accept`** → délégation à `LinkService.accept_request` (`characters/views.py:274-347`). Supprime ~70 lignes dupliquées + bug latent : la version DRF n'aligne pas la création SharedSequence sur la transaction.
3. **`@cache_page(60)` sur `home`, `about`, `explorer`** (anonyme uniquement, vary par `Accept-Language`).
4. **`cache.get_or_set` sur distinct tags** (`core/views.py:41-44, 61-65`) avec TTL 300s, invalidation `post_save` sur `Tag`.
5. **Switch `CompressedManifestStaticFilesStorage`** dans `base.py` + `Cache-Control: public, max-age=31536000, immutable` sur `/static/` (déjà supporté WhiteNoise).
6. **FTS sur `CharacterViewSet.search`** : remplacer `name__icontains` par appel à `build_character_queryset(q=query, ...)` qui utilise déjà `SearchVector(french)`.

**Critère succès** :
- Queries/req sur `/about/` : 4 → 0 (cache hit) ou 4 → 1 (cache miss + valeur cachée)
- Queries/req sur `/explorer/` : 10-12 → 7-9 (distinct tags cachés)
- Race condition CharacterViewSet.claim disparaît (test `assertNumQueries` + `select_for_update`)

### F2 — Structural (effort: 2-3 jours, risque: moyen)

1. **GinIndex persisté sur `Character.name + description`** : migration `AddIndex(GinIndex(SearchVector("name", "description", config="french")))` ; `build_character_queryset` ne recalcule plus le vecteur à chaque requête.
2. **`pg_trgm` extension** + GinIndex `gin_trgm_ops` sur `User.username`, `Game.title`, `Character.name` pour les typeaheads (`games/front_views.py:531,658`, `users/settings_views.py:393`).
3. **Shared inbox optimization fédération** : grouper `broadcast_activity` par domaine, 1 POST par instance distante au lieu de 1 par follower (`activitypub/tasks.py:235-276`). Lit `actor.endpoints.sharedInbox` si dispo, fallback inbox individuelle.
4. **Rate limit per-domain `refresh_remote_actors`** : 1 tâche par instance à la fois via Celery `RateLimit` ou queue dédiée + lock Redis.
5. **`only()` / `defer()` sur listings paginés** : exclure `description` TEXT sur Character/Game listings (50-200 items × ~5KB = 250KB-1MB économisés par hit `/explorer/`).

**Critère succès** :
- `broadcast_activity` : N tasks → ~M tasks où M = nb d'instances distinctes (≤ N)
- `/explorer/` payload : −20-40% (TEXT exclus du listing)
- Typeahead < 50ms p95 sur `name__icontains` remplacé par trigram

### F3 — Monitoring (effort: 1 jour, risque: nul)

1. `django-silk` en staging + dashboard `/silk/`
2. CI : `pytest --django-db-reuse` + `assertNumQueries` sur `/`, `/explorer/`, `/about/`, `CharacterViewSet.list/retrieve` ; budget 12 queries pour `/explorer/` post-F1
3. Alerte `pg_stat_statements` si `total_time` d'une requête > 5% du total → ticket auto
4. Sentry `before_send` sample SQL > 200ms

**Critère succès** : régression N+1 bloque la PR ; toute nouvelle vue hot a un test `assertNumQueries`.

---

## Quick wins prioritaires (≤ 4, doable cette semaine)

1. **Issue + refactor DRF API → LinkService** (F1.1, F1.2) — corrige race condition, supprime duplication
2. **`@cache_page(60)` sur `/`, `/explorer/`, `/about/`** (F1.3) — gain immédiat, 0 invalidation à gérer
3. **`cache.get_or_set` distinct tags + game_systems** (F1.4) — −3 queries hot path
4. **Switch `ManifestStaticFilesStorage`** (F1.5) — cache busting sain pour `Cache-Control` long

---

## Références

- Checklist : `aidd_docs/templates/dev/data_checklist_django-orm.md`
- Pivots Django ORM : `.claude/skills/data-optimize/references/api-mapping.md`
- DEC-035 : Atomic check-then-create — lock parent row
- Memory : `feedback_bug_vs_antipattern.md` — bug single = issue, pas anti-pattern normatif
