---
paths:
  - "**/serializers/**/*.py"
  - "**/serializers.py"
  - "**/views/**/*.py"
  - "**/viewsets/**/*.py"
  - "**/api/**/*.py"
  - "**/urls.py"
---

# Perf pivots — Django REST Framework

Stack-specific overrides applied when `djangorestframework` is detected. Loaded by `web-optimize`. Concatenate with `perf-pivots-django.md`.

## §0 — Pre-flight

- `DEFAULT_RENDERER_CLASSES = ['rest_framework.renderers.JSONRenderer']` en prod — `BrowsableAPIRenderer` génère du HTML + JS (overhead inutile hors dev)
- `python manage.py check` inclut les checks DRF si `rest_framework` dans `INSTALLED_APPS`
- Tripwire CI : `assertNumQueries(N, ...)` dans les tests d'endpoints → regression query count détectée à la PR
- Variance PSI N/A — DRF génère du JSON, pas des pages HTML
- Baseline TTFB : `curl -o /dev/null -s -w "%{time_starttransfer}" -H "Authorization: Bearer ..." <endpoint>` sur les endpoints critiques

## §1 — Critical path

N/A — DRF est une API JSON ; pas de render-blocking resources côté serveur.

## §2 — LCP

N/A — DRF ne sert pas de pages HTML avec images hero.

## §3 — CLS

N/A — DRF ne génère pas de layout.

## §4 — Bundle

N/A — pas de bundle JS/CSS côté DRF.

## §5 — CSS

N/A — DRF ne génère pas de CSS.

## §6 — Caching

- Endpoints publics stables : `@method_decorator(cache_page(60 * 5), name='list')` sur les ViewSets read-heavy
- `cache_control(max_age=300, public=True)` sur les réponses publiques via `@method_decorator(cache_control(...))`
- `Cache-Control: no-store` **obligatoire** sur les endpoints authentifiés — jamais cacher des données utilisateur
- `drf-extensions` : `@cache_response(timeout=60)` pour les actions nommées sur ViewSet
- ETag : `ConditionalGetMixin` de DRF pour valider `If-None-Match` automatiquement

## §7 — SSR

N/A — DRF est une API JSON pure.

## §8 — INP / TBT

N/A — DRF est un backend sans DOM.

## §9 — Backend / TTFB

- **N+1 dans les serializers** — le plus courant et le plus coûteux :
  - `UserSerializer` avec `source='profile.avatar'` → 1 query par objet si `profile` non préfetché
  - `ManyRelatedField` / `PrimaryKeyRelatedField(many=True)` → N queries si `prefetch_related` manquant
  - `NestedSerializer(many=True)` → N+1 garantis sans `prefetch_related`
  - **Fix** : toujours appliquer `select_related` / `prefetch_related` dans le `get_queryset()` du ViewSet :
    ```python
    def get_queryset(self):
        return User.objects.select_related('profile').prefetch_related('tags')
    ```
- **`SerializerMethodField` coûteux** : `get_xxx(self, obj)` exécuté par objet → N queries si elle touche la DB
  - **Fix** : annoter via `queryset.annotate(comment_count=Count('comments'))` et utiliser `source='comment_count'` dans le serializer
- **`to_representation` override** : appelé par objet, pas en bulk → éviter les queries dedans
- **Pagination obligatoire** : sans `DEFAULT_PAGINATION_CLASS`, `.list()` retourne tous les objets
  ```python
  REST_FRAMEWORK = {
      'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.CursorPagination',
      'PAGE_SIZE': 25,
  }
  ```
  Cursor pagination > page number sur grandes tables (pas d'OFFSET coûteux)
- **Authentification** :
  - `SessionAuthentication` : vérifie CSRF + session DB par request → overhead
  - `JWTAuthentication` (simplejwt) : validation locale du token → 0 query DB → préféré pour APIs pures
  - `TokenAuthentication` DRF natif : 1 query DB par request (lookup du token)
- **Permission classes** : ordonner du plus rapide au plus lent — `IsAuthenticated` avant `IsOwner` (qui fait une query)
- **`depth=N`** dans le serializer : génère des serializers imbriqués automatiques → N+1 garanti, pas de contrôle → **proscrire en prod**, écrire des serializers explicites
- **Filtrages** : `django-filter` avec `filterset_class` → filtres appliqués au niveau queryset (SQL) et non en Python post-fetch

## §10 — Client-side storage

N/A — DRF est côté serveur Python.

## §11 — Verification

- `django-silk` : profiler chaque endpoint DRF (queries SQL, durée, params) en dev
- `assertNumQueries(N, lambda: client.get('/api/users/'))` dans les tests — regression query count bloquante à la PR
- `drf-spectacular` génère l'OpenAPI schema → `redoc` ou `swagger-ui` pour l'inspection des endpoints
- Critère déterministe : query count via `assertNumQueries`, latence p50/p95 via `django-silk` ou Sentry perf traces
- Comparaison : médiane post-fix vs maximum pré-fix sur le même endpoint avec la même fixture

---

## Notes internes DRF (hors contrat web-optimize)

### Serializer design

- `read_only_fields` sur le Meta → champs non validés à l'écriture → important pour `id`, `created_at`, `updated_at`
- `write_only=True` sur les champs sensibles (password, token) → non inclus dans la réponse
- `validators=[]` pour désactiver les validators par défaut (ex. `UniqueTogetherValidator`) si géré en aval

### ViewSet vs APIView

- `ModelViewSet` : toutes les actions CRUD en une classe → pratique mais expose toutes les routes par défaut → `http_method_names = ['get', 'post']` pour restreindre
- `ReadOnlyModelViewSet` : list + retrieve uniquement → pour les APIs publiques en lecture seule
- `@action(detail=True, methods=['post'])` : actions custom sur un objet → URL `/users/{id}/activate/`

### Throttling

- `DEFAULT_THROTTLE_CLASSES` et `DEFAULT_THROTTLE_RATES` dans `REST_FRAMEWORK` settings
- `AnonRateThrottle` + `UserRateThrottle` : par IP pour les anonymes, par user pour les authentifiés
- Throttle state : stocké en cache (Redis recommandé, pas le cache mémoire qui ne partage pas entre workers)

### OpenAPI / drf-spectacular

- `@extend_schema(responses=MySerializer)` pour annoter les réponses non-standard
- `SPECTACULAR_SETTINGS['SERVE_INCLUDE_SCHEMA'] = False` en prod (ne pas exposer le schema brut)
