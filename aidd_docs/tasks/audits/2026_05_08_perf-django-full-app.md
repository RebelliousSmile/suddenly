# Suddenly — Audit performance full-app (Django + HTMX + Alpine + Vite)

**Date** : 2026-05-08
**Stack détecté** : `django` (5.x SSR) + `vite` (5.4) + `alpine` (3.14) + `htmx` (1.9) + UnoCSS + EasyMDE
**Scope** : full-app (transversal — config Django, hot routes publiques, bundle Vite, cache, fédération)
**Checklist source** : `aidd_docs/templates/dev/perf_checklist_django.md` (Django pur) + sections `Alpine.js` / `HTMX` / `Vite` de `.claude/skills/web-optimize/references/framework-mapping.md` (concaténées)

---

## Checklist learnings

> Self-audit §12 appliqué APRÈS le rapport. Voir Phase 6 — propositions de patch en fin de doc.

- `[gap] §10 (storage)` — Aucun bullet n'oblige à **stocker** la référence renvoyée par `setInterval` pour pouvoir la `clearInterval` dans `destroy()`. Bug réel détecté en §8 (`main.js:393` — heartbeat sans handle).
- `[gap] §6` — Pas d'item explicite sur le **rebuild + redeploy frontend** : un build local frais ne sert à rien si la prod sert un `last-modified` 2 mois plus vieux que le dernier `pnpm build`.
- `[gap] §7 (HTMX section)` — Manque un bullet sur l'usage de `htmx_render(full, partial, ctx)` comme helper centralisé (anti-pattern alternatif : `if getattr(request, "htmx", False): ... else: ...` dupliqué).
- `[antipattern]` Heavy editor in entry chunk déjà listé → **vérifié** : `EasyMDE` importé top-level `main.js:9` → 100 % des pages publiques paient le coût.
- `[antipattern]` `setInterval` partiellement nettoyé dans `destroy()` (un handle stocké, l'autre pas) → candidat pour la table.
- `[grep]` `grep -n "setInterval" frontend/src/*.js | grep -v "this\.[a-z]* ="` — surface les `setInterval` dont le retour n'est pas assigné à un champ du composant Alpine.
- `[reword] §6 — WhiteNoise bullet` : "manifest enables long-cache hashed URLs" → préciser "et invalide le cache au déploiement via le hash dans le filename".
- `[fp] §3 self-hosted fonts preload` — N/A ici, fontes chargées via Google Fonts (à corriger en F1, mais le bullet reste pertinent quand les fontes seront migrées).

**Verdict** : 3 gaps + 1 anti-pattern → patches proposés en bas de doc.

---

## Baseline déterministe

| Mesure | Valeur | Source |
|---|---|---|
| `static/dist/js/main.js` | **464 KB raw** (~152 KB gzip estimé) | `ls -lh static/dist/js/` |
| `static/dist/css/main-BI6qpVsA.css` | **213 KB raw** (~33 KB gzip estimé) | `ls -lh static/dist/css/` |
| Imports top-level entry chunk | EasyMDE + CSS + UnoCSS + HTMX + Alpine | `frontend/src/main.js:7-21` |
| Composants Alpine déclarés | 11 (`theme, dropdown, modal, notifications, markdownEditor, tabs, characterStatus, passwordStrength, autosave, presence, ...`) | `frontend/src/main.js` |
| Files utilisant `select_related`/`prefetch_related` | 20 modules | `grep -rn` count |
| Files utilisant `@cache_page`/`cache.get_or_set`/`cache_control` | **0** | `grep -rn` |
| `request.htmx` direct (sans `getattr`) | **0** | `grep -n` |
| `transition-all` en code app | **0** (uniquement wireframes legacy + dist build) | `grep -rn` |
| `setInterval` sans handle stocké | **1** (`main.js:393` heartbeat) | code review |
| Routes publiques hot non cachées | `/`, `/explorer/`, `/about/` | `core/views.py` |

### PSI (cloud)

⚠️ **Quota Google PSI API épuisé** ce jour (limite anonyme ~25/jour). PSI cloud non capturé. Action user requise :

```text
1. Ouvrir https://pagespeed.web.dev/
2. Lancer 3-5 runs mobile sur https://suddenly.social/ (intervalle 5 min)
3. Coller scores LCP/CLS/INP/TBT/médiane dans ce rapport
```

### Déploiement prod

| Mesure | Valeur |
|---|---|
| `last-modified` `https://suddenly.social/` | **2026-03-06** (>2 mois de retard) |
| `https://suddenly.social/static/dist/js/main.js` | **404 Not Found** |

→ Le build local du `2026-05-08` n'a jamais été déployé. **F0 obligatoire avant tout autre fix** sinon tous les deltas mesurés seront sur du code mort.

### Métrique primaire post-fix attendue

- **Bytes** : main.js < 100 KB raw (cible 80 % de réduction via split EasyMDE)
- **SQL** : `/explorer/` ≤ 5 queries (actuel non mesuré — `django-debug-toolbar` à ajouter)
- **TTFB p95** : `/about/` < 200 ms (actuellement 4 `.count()` non cachés)

---

## §0 Pre-flight

| Item | Statut | Note |
|---|---|---|
| Métrique déterministe primaire définie | 🟡 | Ce rapport la définit ; n'existait pas avant |
| 3-5 PSI runs baseline | 🔴 | Quota épuisé — utilisateur doit lancer manuellement |
| `django-debug-toolbar` activé en dev | 🔴 | Non détecté dans `requirements/dev.txt` ni `INSTALLED_APPS` — à vérifier |
| Acceptance threshold par métrique | 🟢 | Définis ci-dessus |

## §1 Render-blocking critical path

| Item | Statut | Note |
|---|---|---|
| Pas de CSS tiers `<link rel=stylesheet>` synchrone `<head>` | 🔴 | `templates/base.html:24` charge `fonts.googleapis.com/css2?family=Inter+Crimson+Text` — render-blocking |
| `<link rel="preconnect">` réservé above-fold | 🟡 | `base.html:20-21` preconnect Google Fonts — OK car fonts above-fold, mais reste sub-optimal vs self-host |
| `collectstatic` produit hashed filenames | 🔴 | `STORAGES["staticfiles"]` = `CompressedStaticFilesStorage` à `config/settings/base.py:132` — **PAS** la variante `Manifest` |
| Critical CSS inliné | 🔴 | `{% vite_css %}` dans `<head>` `base.html:27` — render-blocking complet, 213 KB CSS |
| 3rd-party JS deferred | N/A | Pas de Plausible/GTM/Sentry détecté |
| `<script>` en fin `<body>` ou `defer` | 🟢 | `{% vite_asset "src/main.js" %}` à `base.html:338` |
| `[x-cloak]{display:none}` dans CSS critique (Alpine) | 🟡 | À vérifier dans `base.css` — non trouvé en grep direct |

## §2 LCP

| Item | Statut | Note |
|---|---|---|
| `<link rel="preload" as="image" fetchpriority="high">` hero | 🔴 | Aucun preload hero détecté dans `base.html` |
| `imagesrcset` + `imagesizes` sur preload responsive | N/A | Pas de preload du tout |
| Hero `<img>` `fetchpriority="high"` `loading="eager"` | 🔴 | À auditer page par page (home, explorer) |
| LCP image directe `<img src=webp>`, pas `<picture>` | 🟡 | À vérifier sur `/` et `/explorer/` |
| `width` + `height` sur tous `<img>` | 🟡 | Logo OK (`base.html:34` width=28 height=34) ; reste à auditer |
| Below-fold `loading="lazy"` `decoding="async"` | 🟡 | À auditer |
| `MEDIA_URL` long-cache | 🔴 | Pas de header explicite vu — dépend du serveur prod (Apache Alwaysdata par défaut) |
| Avatars resized server-side via Pillow | 🟡 | À vérifier dans `users/models.py` |

## §3 CLS

| Item | Statut | Note |
|---|---|---|
| Reserved space async content | 🟡 | Skeletons HTMX à auditer par template |
| `font-display: swap` sur `@font-face` | 🟢 | Google Fonts `&display=swap` `base.html:24` |
| Self-hosted fonts URL stable + preload | 🔴 | Fontes externes — à migrer en self-host (F1) |
| Pas de banner Django messages déplaçant le layout | 🟡 | À vérifier sur premier render après login |
| `x-if` vs `x-show` choix documenté **[alpine]** | 🟡 | Mix utilisé sans pattern documenté — pas critique |

## §4 JS bundle (critique pour Suddenly — Vite + Alpine + HTMX + EasyMDE)

| Item | Statut | Note |
|---|---|---|
| Entry chunk size + budget défini **[vite]** | 🔴 | 464 KB raw (~152 KB gzip), AUCUN budget défini |
| Heavy editor libs hors entry chunk **[vite]** | 🔴 | `EasyMDE` importé top-level `frontend/src/main.js:9` — chargé sur **toutes** les pages (home, explorer, about) alors qu'utilisé uniquement sur edit reports |
| `vite build --report` reviewed **[vite]** | 🔴 | Pas de `rollup-plugin-visualizer` configuré dans `frontend/vite.config.js` |
| Per-route bundle split **[vite]** | 🔴 | Single entry `main.js`, pas de `manualChunks` ; pas de chunk `editor.js` séparé |
| Alpine.js loadé via `<script defer>` ou Vite module **[alpine]** | 🟢 | Bundlé via Vite (`main.js:18`), `defer` natif via type=module |
| `x-init` sans travail sync lourd **[alpine]** | 🟡 | `presence.init()` `main.js:388` lance un fetch immédiat — à différer via `x-intersect` si below-fold |
| `htmx.org` importé une fois **[htmx]** | 🟢 | `frontend/src/main.js:17` — single import |
| `hx-boost` selectif **[htmx]** | 🟡 | À auditer — pas de `hx-boost` global détecté |
| Icon framework purgé < 50 KB CSS gzip | 🟡 | UnoCSS + 3 collections lazy (lucide, simple-icons, game-icons) — config OK ; mesure réelle ~33 KB gzip CSS, OK |
| Pas de `<script>` inline > 5 lignes | 🟢 | Inline `<script>` `base.html:8-12` (theme anti-flash) = 5 lignes max, OK |
| Pas de jQuery alongside Alpine | 🟢 | Pas de jQuery dans `package.json` |

## §5 CSS

| Item | Statut | Note |
|---|---|---|
| CSS bundle < 50 KB gzip marketing | 🟢 | ~33 KB gzip estimé (213 KB raw) |
| Pas de `transition-all` en app | 🟢 | 0 occurrence dans `templates/components/`, `frontend/src/` (présent uniquement dans wireframes legacy + dist build minifié) |
| Pas de `* { transition }` global | 🟢 | À confirmer ; `frontend/src/base.css` à scanner |
| `safelist` UnoCSS auditée | 🟡 | ~80 entrées dans `frontend/uno.config.js` — pas d'audit récent vs usage réel |
| CSS variables pour theme tokens | 🟢 | Theme system via CSS vars (`base.css`) |
| Pas de framework CSS CDN render-blocking | 🟢 | Bootstrap/FontAwesome absents |

## §6 Caching & hosting

| Item | Statut | Note |
|---|---|---|
| `STORAGES["staticfiles"]` = `CompressedManifestStaticFilesStorage` | 🔴 | `config/settings/base.py:132` = `CompressedStaticFilesStorage` (sans Manifest) → pas de hash filename → impossible de servir en `immutable` |
| `WHITENOISE_MAX_AGE = 31536000` | 🔴 | Non défini dans `base.py` ni `production.py` |
| HTML `Cache-Control` (private logged-in / public anon) | 🔴 | Aucun header explicite — dépend du Django default (no-cache) |
| `@cache_page` sur home/explorer/about | 🔴 | 0 décorateurs cache trouvés (`grep -rn "@cache_page\|cache_control"` = 0) |
| `@vary_on_headers("Accept-Language")` | 🔴 | Site i18n (FR/EN) — manque pour cacher correctement par langue |
| Template fragment caching `{% cache %}` | 🔴 | Aucun `{% cache %}` détecté |
| Low-level cache API sur agrégations | 🔴 | `core/views.py:88-93` 4× `.count()` à chaque hit `/about/` ; pas de `cache.get_or_set` |
| Redis configuré en prod | 🟡 | Optionnel via `REDIS_URL` (`production.py`) — fallback DatabaseCache documenté |
| `CONN_MAX_AGE = 60` sur PostgreSQL | 🟢 | `production.py` configuré |
| CDN devant `STATIC_URL` | 🔴 | Pas de Cloudflare/Bunny détecté ; Apache Alwaysdata sert directement |
| Pas de conflit Cache-Control middleware/proxy | N/A | Aucun cache config → rien à conflictuer |

## §7 SSR templates & fragments **[htmx]**

| Item | Statut | Note |
|---|---|---|
| `{% load cache %}` sur fragments coûteux | 🔴 | 0 usage |
| Détection HTMX `getattr(request, "htmx", False)` **[htmx]** | 🟢 | `core/views.py:118` — pattern correct, 0 violations |
| HTMX endpoints HTML fragments, pas JSON **[htmx]** | 🟢 | Conforme rule `03-htmx-patterns.md` |
| `@require_POST` AVANT `@login_required` **[htmx]** | 🟡 | À auditer fichier par fichier — `grep` revient 0 mais peut signifier décorateur manquant ailleurs |
| Pattern 3 templates pour actions inline **[htmx]** | 🟢 | Conforme (rule `03-htmx-patterns.md` documentée) |
| Pas de `.count()` dans templates | 🟡 | `{% if not all_tags %}` etc. à vérifier dans `core/explorer.html` |
| `{% url %}` namespaced | 🟢 | Convention respectée |

## §8 INP / TBT

| Item | Statut | Note |
|---|---|---|
| Pas de travail sync lourd `x-init` below-fold **[alpine]** | 🟡 | `presence.init()` lance un fetch + 2 setInterval immédiatement |
| Long lists rendues serveur (pas `x-for` JSON) **[alpine]** | 🟢 | Listes paginées Django (slicing `[:24]` `views.py:47, 67`) |
| `hx-trigger` debounced **[htmx]** | 🟡 | À vérifier sur typeahead `/explorer/?q=...` |
| `@input.debounce.300ms` sur Alpine **[alpine]** | 🟡 | À vérifier |
| **`setInterval` polling cleanup correct** **[alpine]** | 🔴 | `frontend/src/main.js:393` — `setInterval(() => this.heartbeat(), 10000)` retour **non stocké** → `destroy()` ne le clear pas → fuite après navigation |
| Pas de layout thrashing | 🟡 | Pas de pattern read/write DOM identifié |
| `htmx-indicator` styles préchargés | 🟢 | `frontend/src/htmx-indicator.css` importé `main.js:11` |

## §9 Backend / DB perf (CRITIQUE)

| Item | Statut | Note |
|---|---|---|
| `django-debug-toolbar` ≤ 10 SQL queries / hot page | 🔴 | Non installé/non mesuré — F0 ajout obligatoire |
| `select_related` + `prefetch_related` sur paginés | 🟢 | 20 fichiers utilisent ces helpers (couverture forte) |
| Service-layer `build_*_queryset` | 🟢 | `build_character_queryset`, `build_game_queryset` présents |
| `Meta: indexes` sur colonnes filtrées | 🟡 | À auditer modèle par modèle |
| Composite indexes multi-column | 🟡 | À auditer |
| Pas de `.count()` dans templates | 🟡 | `core/views.py:88-93` 4 `.count()` en vue (pas template) — déjà mauvais, à cacher |
| Pas de `.exists()` dans loops | 🟡 | grep n'a pas surfacé ; à confirmer |
| Agrégations cachées via `cache.get_or_set` | 🔴 | `views.py:41-44` et `:61-65` exécutent `Game.objects.filter(remote=False, tags__isnull=False).values_list('tags__name').distinct()` à **chaque hit** /explorer/ |
| `gunicorn` workers `2*cores+1` | 🟡 | Dépend du déploiement — à vérifier `Procfile` / config Alwaysdata |
| Celery pour tâches > 200 ms | 🟡 | Optionnel avec fallback `EAGER` (`production.py`) — risque que la fédération bloque la response en mode EAGER |
| `EXPLAIN ANALYZE` sur top-3 slowest | 🔴 | Non fait |
| `GinIndex` sur colonnes FTS | 🟡 | À auditer modèles `Character`, `Game`, `Report` |
| Federation outbound async (Celery) | 🟡 | Code prévu pour ; vérifier que `CELERY_TASK_ALWAYS_EAGER` n'est pas actif en prod réelle (sinon delivery bloque) |

## §10 Storage

| Item | Statut | Note |
|---|---|---|
| Pas de PII/tokens en localStorage **[alpine]** | 🟢 | Theme + UI state seulement (`base.html:9`) |
| `Alpine.$persist` namespacé **[alpine]** | 🟡 | À auditer — grep `Alpine.\$persist` |
| Quota guard try/catch | 🔴 | `localStorage.getItem('theme')` `base.html:9` sans try/catch |
| Single key prefix | 🟡 | À documenter (préfixe `suddenly:` recommandé) |
| `SESSION_COOKIE_SECURE = True` prod | 🟢 | `production.py` |
| `CSRF_COOKIE_SECURE = True` prod | 🟢 | `production.py` |
| `SESSION_COOKIE_HTTPONLY` | 🟢 | Default Django |
| `SESSION_COOKIE_SAMESITE = Lax` | 🟢 | Default Django |
| `csrftoken` Secure + SameSite=Lax | 🟢 | `production.py` (HTMX-compatible : non-HttpOnly OK) |
| HSTS ≥ 31536000 + subdomains + preload | 🟢 | `production.py` |
| Cookies < 4 KB | 🟢 | Pas de cookie custom large détecté |

## §11 Verification & non-regression

À cocher après chaque fix F0/F1/F2 :

- [ ] Delta déterministe confirmé (bytes/queries/TTFB)
- [ ] PSI 3-5 runs post-fix, médiane > max baseline
- [ ] `django-debug-toolbar` query count ≤ baseline
- [ ] `wrk -d 30s -c 10 https://suddenly.social/` p95 stable
- [ ] Pas de régression sur sibling routes (`/feed/`, `/about/`)
- [ ] `view-source:` prod confirme preload/CSS attendus
- [ ] Migration DB testée sur copie prod si schema change
- [ ] Rule mise à jour si nouveau pattern (`03-frameworks-and-libraries/`, `08-domain/`)

---

## Roadmap priorisée

### F0 — Stabilisation (bloquant, sinon tous les deltas sont sur code mort)

| Action | Effort | Risque | Référence |
|---|---|---|---|
| **Redéployer** prod : `pnpm --dir frontend build` + `python manage.py collectstatic` + push artefacts Alwaysdata | 30 min | Faible | `last-modified` 2026-03-06 → ce jour |
| Installer `django-debug-toolbar` en dev (`pip install django-debug-toolbar`, INSTALLED_APPS, MIDDLEWARE, INTERNAL_IPS) | 15 min | Nul | §9 mesure manquante |
| Capturer 3-5 PSI runs manuellement (https://pagespeed.web.dev/, mobile) sur `/`, `/explorer/`, `/about/` après redéploiement | 30 min user | Nul | Baseline PSI absente |
| Capturer SQL query count baseline via le shell snippet `perf_checklist_django.md` §Quick verification | 15 min | Nul | §9 |

### F1 — Quick wins (≤ 1 semaine, ROI élevé)

| Action | Cible | Effort | Métrique primaire |
|---|---|---|---|
| **Switch `STORAGES["staticfiles"]` → `CompressedManifestStaticFilesStorage`** + ajouter `WHITENOISE_MAX_AGE = 31536000` | `config/settings/base.py:132` + new setting | 30 min | Cache-Control `immutable` sur assets hashés ; économie bandwidth récurrente |
| **Self-host fontes** Inter + Crimson Text via WhiteNoise + `<link rel="preload" as="font">` | `templates/base.html:24` | 1 h | Suppression render-block fonts.googleapis.com (~150 ms FCP mobile) |
| **`@cache_page(300)` + `@vary_on_headers("Accept-Language")`** sur `home`, `about`, `explorer` (anonymes) | `suddenly/core/views.py:18, 23, 81` | 45 min | TTFB p95 `/about/` < 100 ms (4 `.count()` cachés) |
| **`cache.get_or_set("explorer_tags_v1", ..., 600)`** sur la query `distinct tags` | `core/views.py:41-44` + `:61-65` | 30 min | -1 query DISTINCT par hit `/explorer/` |
| **Bug fix** : stocker handle du second `setInterval` puis `clearInterval` dans `destroy()` | `frontend/src/main.js:393, 397` | 10 min | Fuite mémoire post-navigation supprimée |

### F2 — Structurel (1-3 semaines, ROI élevé mais effort)

| Action | Cible | Effort | Métrique primaire |
|---|---|---|---|
| **Split EasyMDE en chunk lazy** : `const EasyMDE = (await import('easymde')).default` à l'init du composant `markdownEditor` | `frontend/src/main.js:9, 149` | 2-3 h (test prudent — Alpine init order) | main.js entry < 100 KB raw (cible 80 % réduction) |
| **`manualChunks`** dans `vite.config.js` : split vendor (htmx, alpine, easymde) | `frontend/vite.config.js` | 1 h | Vendor chunk cacheable séparément |
| **`rollup-plugin-visualizer`** pour audit récurrent du bundle | `frontend/vite.config.js` + `pnpm add -D rollup-plugin-visualizer` | 30 min | Visibilité continue des dépendances lourdes |
| Critical CSS above-fold inliné (`vite-plugin-critical` ou hand-write tokens + layout) | `templates/base.html` + Vite plugin | 3-4 h | FCP mobile -200/300 ms |
| Ajouter `<link rel="preload" as="image" fetchpriority="high">` pour le hero de `/`, `/explorer/`, `/about/` | `core/home.html`, `core/explorer.html`, `core/about.html` | 1 h par page | LCP -300/500 ms |
| Audit `Meta: indexes` sur tous les modèles `Character`, `Game`, `Report`, `Tag` + `GinIndex` sur FTS | `*/models.py` | 4-6 h | Requêtes filter/order < 50 ms |

### F3 — Monitoring (continu)

| Action | Effort | Bénéfice |
|---|---|---|
| Intégrer `django-silk` en staging pour profiling SQL continu | 1 h | Détection régressions N+1 |
| `wrk` script CI sur `/`, `/explorer/`, `/about/` à chaque déploiement (smoke perf) | 2-3 h | Alerte sur régression p95 TTFB |
| Sentry Performance + Web Vitals tracking | 1 jour | Tracking LCP/INP/CLS terrain réel |
| Renouveler `pnpm vite build --report` à chaque ajout de lib | 0 (process) | Empêche dérive bundle |

---

## Quick wins prioritaires (4 actions, ≤ 1 semaine)

1. **F0 redéploiement** — sinon rien d'autre ne sert (30 min)
2. **`CompressedManifestStaticFilesStorage` + `WHITENOISE_MAX_AGE`** — 1 ligne de config, gain immédiat sur tous les assets hashés (30 min)
3. **`@cache_page(300)` + `cache.get_or_set` explorer tags** — 4 décorateurs + 1 wrapping, divise par >10 le TTFB sur routes publiques anonymes (1 h)
4. **Split EasyMDE en dynamic import** — biggest single-win bundle (-300 KB raw, ~75 % gzip), payback sur première requête home/explorer (2-3 h, à tester avec soin)

---

## Patches proposés sur les supports

> Self-audit §12 a remonté 3 gaps + 1 anti-pattern : seuil de proposition atteint.

### Patch 1 — `aidd_docs/templates/dev/perf_checklist_django.md`

Ajouter dans §6 (caching) :

```markdown
- [ ] **Frontend rebuild + redeploy effectif** : `last-modified` du HTML prod < date du dernier `pnpm build` local — sinon les optims locales ne sont jamais servies
```

Ajouter dans la table `## Common anti-patterns` :

```markdown
| `setInterval` sans handle stocké dans Alpine `destroy()` | Polling continue après navigation → fuite mémoire + requêtes fantômes | — |
```

### Patch 2 — `.claude/skills/web-optimize/references/framework-mapping.md`

Section `## Alpine.js` §8 — ajouter :

```markdown
- **Chaque `setInterval` retourne un handle assigné à un champ du composant** (`this._heartbeatId = setInterval(...)`) — le `destroy()` Alpine doit clear TOUS les handles, pas seulement le premier (bug typique : 2 intervals, 1 stocké, 1 oublié)
```

Section `## HTMX` §7 — ajouter :

```markdown
- Helper centralisé `htmx_render(request, full_template, partial_template, context)` plutôt que `if getattr(request, "htmx", False): ... else: ...` dupliqué dans chaque vue (réduit la surface du bug `request.htmx` direct + DRY)
```

### Patch 3 — `aidd_docs/templates/dev/perf_checklist_django.md` Quick verification

Ajouter :

```bash
# setInterval handles unstored (Alpine destroy() leak)
grep -n "setInterval" frontend/src/*.js | grep -v "this\.[a-z]* ="
```

### Validation user requise

Appliquer les patches 1, 2, 3 ? (oui/non/partiel)
