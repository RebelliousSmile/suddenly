---
paths:
  - "manage.py"
  - "**/settings.py"
  - "**/settings/*.py"
  - "**/wsgi.py"
  - "**/asgi.py"
  - "**/urls.py"
  - "**/views.py"
  - "**/templates/**/*.html"
---

# Perf pivots — Django

Stack-specific overrides applied when `django` is in `requirements.txt` / `pyproject.toml`. Loaded by `web-optimize`.

## §0 — Pre-flight

- `DEBUG=False` en prod **OBLIGATOIRE** (sinon stack traces fuites + perf)
- Django Debug Toolbar : `INSTALLED_APPS` uniquement en dev (via `if DEBUG`)
- `python manage.py check --deploy` → audit sécurité + perf settings
- Build warnings : `python manage.py collectstatic --noinput 2>&1` — warning `WARNINGS: security.*` = load-bearing ; `Post-processed ... files copied` = nominal
- Warnings load-bearing : `django.security.W004` (SECRET_KEY faible), `django.core.W003` (ALLOWED_HOSTS vide), `django.middleware.W001` (SecurityMiddleware manquant) — ne jamais ignorer
- Variance PSI Django : 3-5 runs minimum via Lighthouse CI ; la variation liée au TTFB Gunicorn peut atteindre ±15 points — ne déclarer un gain que si médiane post-fix > max pré-fix
- Tripwire CI : `python manage.py check --deploy --fail-level WARNING` dans le pipeline CI échoue si warning sécurité détecté

## §1 — Critical path

- Templates Django : `{% load static %}` + ManifestStaticFilesStorage → URLs hashées
- `<link rel="stylesheet" href="{% static 'critical.css' %}">` pour CSS critique
- `whitenoise.middleware.WhiteNoiseMiddleware` pour servir static avec cache headers immutable
- CSS critique inline : `whitenoise.storage.CompressedManifestStaticFilesStorage` sert les assets avec `Cache-Control: max-age=31536000, immutable` ; pour inliner le CSS critique : Tailwind `@layer base` / `@layer components` dans `critical.css` + `{% include 'critical.css' %}` dans le `<head>` du template de base
- Scripts bloquants : `<script src="{% static 'app.js' %}">` sans `defer` bloque le rendu → toujours `<script defer src="{% static 'app.js' %}">`
- Identifier les scripts sans defer : `grep -rn "<script src" templates/ --include="*.html" | grep -v defer | grep -v async`
- Scripts tiers différés : `<script defer src="https://www.googletagmanager.com/gtm.js">` dans `{% block scripts %}` en bas de page

## §2 — LCP

- Image above-fold dans les templates Django : `<img src="{% static 'images/hero.webp' %}" fetchpriority="high" loading="eager" width="1440" height="800">`
- `<picture>` INTERDIT above-fold — utiliser `<img>` natif directement
- Preload LCP : `{% block head %}<link rel="preload" as="image" href="{% static 'images/hero.webp' %}">{% endblock %}`
- Si Cloudinary/S3 : URL stable sans hash Vite → preload direct avec l'URL absolue
- Responsive hero : `<img srcset="{% static 'hero-400.webp' %} 400w, {% static 'hero-1440.webp' %} 1440w" sizes="100vw" fetchpriority="high">`

## §3 — CLS

- `width` et `height` obligatoires sur tout `<img>` dans les templates : `<img src="..." width="800" height="600">` ou `aspect-ratio` CSS
- FOUT : `@font-face { font-display: swap; }` dans le CSS Django ; Google Fonts : ajouter `&display=swap` à l'URL
- Éléments dynamiques (cookie banner, auth UI) : réserver l'espace avec un min-height dans le CSS avant le mount JS

## §4 — Bundle

- Si Vite intégré (`django-vite`) : voir `perf-pivots-vite.md` ; tag `{% vite_asset %}` lit le manifest
- Sinon, collectstatic + ManifestStaticFilesStorage → assets hashés natifs
- Code splitting N/A si pas de Vite/webpack → JS traditionnel `<script defer>` ; taille du bundle auditée via `python manage.py collectstatic --noinput && du -sh staticfiles/`
- Import lazy N/A avec JS traditionnel sans bundler ; si `django-vite` : `const MyModule = () => import('./module.js')` côté JS

## §5 — CSS

- Tailwind + Django : `content: ['templates/**/*.html', 'apps/**/*.html']` dans `tailwind.config.js` pour le purge
- Purge automatique via Tailwind JIT ; vérifier : `pnpm run build` puis `du -sh static/css/tailwind.css`
- Propriétés à éviter : `transition: all` (déclenche composite + paint) → `transition: color, background-color`
- Détecter : `grep -rn "transition.*all\|transition: all" static/ apps/ --include="*.css" --include="*.html"`

## §6 — Caching

- `CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', ...}}`
- `@cache_page(60 * 15)` decorator pour pages full SSR cachables
- Template fragment caching : `{% cache 600 sidebar request.user.username %}` pour blocs lourds
- `cache.get_or_set(key, callable, timeout)` pour mémoriser queries hot path
- `Cache-Control: public, max-age=31536000, immutable` sur `STATIC_URL` (Whitenoise le fait avec `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'`)
- Routes HTML cachables : `@vary('Accept-Encoding') @cache_page(60)` pour les vues publiques ; routes authentifiées : `@never_cache` obligatoire
- Assets hashés : `CompressedManifestStaticFilesStorage` sert `Cache-Control: max-age=31536000, immutable` automatiquement — aucune config CDN supplémentaire nécessaire

## §7 — Server-side rendering

- Django SSR natif : toutes les routes sont SSR par défaut ; routes statiques = pages cachées via `@cache_page`
- Templates Django compilés à la première utilisation puis cachés ; `loaders` configurés en prod :
  ```python
  TEMPLATES = [{
    'OPTIONS': {
      'loaders': [
        ('django.template.loaders.cached.Loader', [
          'django.template.loaders.filesystem.Loader',
          'django.template.loaders.app_directories.Loader',
        ]),
      ],
    },
  }]
  ```
- `{% include %}` profond → coût ; préférer `{% with %}` pour mémoriser une expression
- Context processors : chaque processor execute à CHAQUE render → auditer leur coût (queries DB cachées notamment)
- Composants client-only : éléments nécessitant `window` → wrappés dans `{% if user.is_authenticated %}` côté template ; Alpine.js / htmx pour interactions client sans SSR complet
- Hydration mismatch N/A — Django SSR pur sans hydration JS frontend (sauf si couplé à un framework JS)

## §8 — INP / TBT

- Django SSR pur, mais si htmx / Alpine : voir leurs pivots
- Forms server-side validation : éviter le full reload, préférer htmx swap
- Travail synchrone coûteux côté navigateur : différer via `requestIdleCallback(() => { heavyWork() })` dans les templates Django qui embarquent du JS inline
- Django n'a pas d'accès direct aux event listeners — les patterns `passive: true` et `debounce` relèvent du JS embarqué dans les templates

## §9 — Backend / runtime

- **ASGI > WSGI** pour async views et long-lived connections (SSE, WebSocket via Channels)
- Gunicorn workers : `2 × CPU + 1` ; threading vs async workers selon I/O bound
- **Middleware budget** : chaque middleware execute par request → audit `MIDDLEWARE` liste, ordre matters
  - `SessionMiddleware` lit DB par request (sauf `SESSION_ENGINE = 'django.contrib.sessions.backends.cache'`)
  - `LocaleMiddleware` parse Accept-Language
- Chemin critique : view → ORM query → template render → response ; max 3 queries séquentielles avant d'utiliser `select_related` / `prefetch_related`
- Connexion data layer : voir `data-pivots-django-orm.md`
- ORM N+1 → voir `data-pivots-django-orm.md`
- Celery / Django-Q pour tâches async (emails, imports, exports)
- Cold start : Gunicorn/WSGI = process long-lived, pas de cold start problématique sauf si déployé sur Lambda (rare)

## §10 — Storage

- SSR Django : `localStorage` / `sessionStorage` / `document.cookie` uniquement côté JS (navigateur) — le code Python côté serveur ne peut jamais y accéder
- Guard côté template : ne jamais supposer que `localStorage` est disponible dans du JS embarqué sans `if (typeof localStorage !== 'undefined')`
- Items SSR-guard JS (`process.client`, `typeof window`) **N/A** — Django ne pré-rend pas de composants JS
- Sessions Django : DB par défaut (1 query/request) — passer en cache backend (`SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'` ou pur `cache`)

## §11 — Verification

- `silk` profiler pour mesurer view + queries par endpoint
- `django-debug-toolbar` (dev) → query count, time, panel SQL
- Sentry / OpenTelemetry pour APM en prod
- Critère déterministe : taille CSS (`du -sh staticfiles/css/`), query count via Django Debug Toolbar, TTFB via `curl -o /dev/null -s -w "%{time_starttransfer}"` sur hot paths
- Comparaison : médiane 5 runs post-fix vs maximum 5 runs pré-fix ; ne déclarer gain PSI que si médiane post > max pré
