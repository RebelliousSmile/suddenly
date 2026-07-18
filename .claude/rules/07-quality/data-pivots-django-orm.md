---
paths:
  - "**/models.py"
  - "**/managers.py"
  - "**/views.py"
  - "**/migrations/*.py"
---

# Data pivots — Django ORM

Stack-specific overrides for data audits when Django ORM is detected. Loaded by `data-optimize`. Concatenate with Django web pivots.

## §0 — Pre-flight

- Django Debug Toolbar (dev) → query count + duplicates par view
- `django-silk` profiler en staging — slow query report
- `connection.queries` (avec `DEBUG=True`) pour inspection ponctuelle ; jamais en prod
- Capturer le payload bytes : DevTools Network → filtre XHR/Doc → colonne "Size" agrégée ; ou `curl -o /dev/null -s -w "%{size_download}"` par endpoint
- Compteurs déterministes : `len(connection.queries)` avant/après une action (DEBUG=True) ; `django-silk` query count/view en staging — reproductible sur le même user-flow

## §1 — N+1 (LE problème Django)

- `for post in Post.objects.all(): post.author.name` → 1 query + N queries (1 par author) = N+1
- **Fix select_related** (FK / OneToOne) : `Post.objects.select_related('author')` → 1 query avec JOIN
- **Fix prefetch_related** (ManyToMany / reverse FK) : `Post.objects.prefetch_related('tags')` → 2 queries (posts + tags in [ids])
- Nested : `Post.objects.select_related('author').prefetch_related('comments__author')` — chaque niveau audité
- `Prefetch('comments', queryset=Comment.objects.select_related('author'))` pour customiser le sous-queryset
- Détecter les appels en boucle : `grep -rn "\.objects\." views.py | grep -v "select_related\|prefetch_related"` pour repérer les querysets dans des boucles
- Batch reads : `Post.objects.filter(id__in=post_ids)` → 1 query pour N objets ; `User.objects.in_bulk(ids)` → dict {id: obj}

## §2 — Pagination (select narrowing + pagination)

- Requête bornée : `Post.objects.all()[:50]` (slicing Django) ou `Paginator(qs, per_page=20)`
- Détecter requêtes sans limite : `grep -rn "objects\.all()\b" apps/ --include="*.py" | grep -v "count()\|exists()"` — tout `.all()` retourné directement à un serializer est suspect
- Pattern curseur recommandé : `Post.objects.filter(id__gt=last_id).order_by('id')[:20]` — plus efficace que `OFFSET` sur grandes tables
- Django `Paginator` exécute 1 count + 1 slice → 2 queries
- Pour grosses tables : `Paginator` lent (count plein), préférer cursor-based via `id__gt=last_id` + `limit`
- `.iterator(chunk_size=2000)` pour traverser sans charger tout en mémoire (jobs, exports)

## §3 — Real-time

N/A — Django ORM est request/response pur ; pas de souscription temps réel natif.

Pour real-time avec Django : `Django Channels` + WebSocket ou Server-Sent Events ; distinct du scope Django ORM.

## §4 — Caching layer

- Niveaux disponibles : cache Django (`cache.get/set`), per-view (`@cache_page`), template fragment (`{% cache %}`), Redis (`django-redis`), HTTP CDN
- TTL par couche : `@cache_page(60 * 15)` → 15 min ; `cache.set(key, value, timeout=300)` ; `{% cache 600 key %}` → 10 min
- Détecter cache miss systématique : `django-silk` montre les query counts identiques à chaque request sur le même endpoint — si query count > 0 sur des données invariantes, pas de cache
- `cache.get_or_set(key, callable, timeout)` pour mémoriser queries hot path
- Per-site cache via middleware (`UpdateCacheMiddleware` + `FetchFromCacheMiddleware`)
- Invalidation : signals `post_save` qui clear les keys liées (dépendance manuelle, fragile à grande échelle)

## §5 — Payload optimization

- Projection de champs : `Post.objects.only('id', 'title')` ou `.values('id', 'title')` pour sélection explicite
- `.values()` / `.values_list()` retournent des dicts/tuples plats → pas de model overhead, 2-3× plus rapide pour read-only
- Détecter overfetch : `grep -rn "objects\.all()\b\|\.values()\b" apps/ --include="*.py"` — `.all()` sans `.only()` ni `.values()` en API endpoint = overfetch
- Django compresse via GZip middleware : `django.middleware.gzip.GZipMiddleware` dans `MIDDLEWARE` ; vérifier `Content-Encoding: gzip` dans les DevTools
- `Post.objects.defer('content', 'metadata')` → exclude des champs lourds

## §6 — Quota & cost

- Auto-hébergé : pas de facturation par query ; monitorer via `slow_query_log` MySQL ou `pg_stat_statements` Postgres
- `django-silk` (staging) : rapport query count + slow queries par view
- `connection.queries` (DEBUG=True) pour inspection ponctuelle en dev
- Où consulter les métriques : Postgres → `SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 20;` ; MySQL → `SHOW STATUS LIKE 'Slow_queries'`
- Règle prioritaire Django ORM : éviter les `.all()` non bornés sur des tables > 10k lignes ; toujours paginer ou borner explicitement

## §7 — Security

- `Post.objects.filter(author=request.user)` — scope systématique par user sur toutes les queries
- `django-guardian` pour permissions objet-level
- Row-level security : `GlobalScope` avec queryset filtré par tenant dans le manager
- Ne jamais `Model.objects.get(pk=pk)` sans vérifier que l'objet appartient à l'utilisateur courant
- Règles de sécurité : définies dans les managers Django (`get_queryset(self, request)`) et vues via `get_object_or_404`
- Anti-pattern connu : `Post.objects.get(pk=pk)` sans `.filter(author=request.user)` — exposition d'objets d'autres utilisateurs
- Tests : `pytest` + `django.test.TestCase` pour tester que `GET /posts/123/` retourne 403 si `request.user != post.author`

## §8 — Schema & indexing

- `class Meta: indexes = [models.Index(fields=['user', '-created_at'])]` — composite, ordre = sélectivité
- `db_index=True` sur les champs filtrés/triés fréquemment
- Détecter requêtes sans index : `EXPLAIN ANALYZE` en Postgres ; Django `connection.queries` montre le SQL → copier dans `EXPLAIN ANALYZE`
- Dénormalisation : dupliquer les champs fréquemment lus (ex. `Post.author_name` copié depuis `User.name`) pour éviter les JOINs répétés sur hot paths
- Migrations : `python manage.py makemigrations` puis review du SQL via `sqlmigrate app NNNN`
- `AddIndex` non-concurrent lock la table → `AddIndexConcurrently` (Django 4.0+) pour Postgres prod

## §9 — Background jobs

- Celery + Redis/RabbitMQ pour tâches async : `@shared_task(bind=True, max_retries=3)` avec `self.retry(countdown=2**self.request.retries)`
- Django-Q comme alternative plus légère (un seul process)
- `transaction.on_commit(lambda: send_email.delay(user.id))` pour différer après commit réussi
- Idempotence : `Model.objects.get_or_create()` ou `update_or_create()`
- `post_save`, `post_delete` signals → coût caché à chaque save ; tester en isolation
- `bulk_create([...], ignore_conflicts=True)` skip signals → 1000× plus rapide pour imports
- `update()` (queryset) skip aussi signals + save() → utiliser quand pas de side-effect attendu

## §10 — Verification

- Critère déterministe : `len(connection.queries)` avant/après ; `django-silk` query count/view
- Baseline : Django Debug Toolbar → noter query count et temps SQL sur hot paths
- Comparaison : médiane post-fix (3-5 requêtes mesurées) vs max pre-fix ; ne déclarer un gain que si médiane post < max pré
- Observability : `django-silk` (staging), Django Debug Toolbar (dev), Sentry APM / OpenTelemetry (prod)

## §11 — Self-audit

- Faux positifs : `update()` queryset (skip signals) n'est pas un anti-pattern — valide pour bulk operations sans side-effects
- Gaps candidats : manque de couverture sur `defer()` + accès ultérieur (defer trap) ; pas de section sur `select_for_update()` pour les cas de concurrence
- N/A items : §3 Real-time (Django ORM est request/response pur)
