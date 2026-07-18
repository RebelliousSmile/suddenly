---
paths:
  - "**/activitypub/**/*.py"
  - "**/activitypub/models.py"
  - "**/activitypub/views.py"
  - "**/activitypub/signatures.py"
  - "**/activitypub/activities.py"
  - "**/activitypub/tasks.py"
---

# AP pivots — Django ActivityPub

Stack-specific pivot for ActivityPub federation audits when `activitypub/` module + `httpx` + `cryptography` are detected. Installed by `sc-python:sniff` as `ap-pivots-django-activitypub.md`. Loaded by `ap-optimize`.

## §0 — Pre-flight

- Detection signals: `activitypub/` app directory + `httpx` in deps + `cryptography` in deps
- `manage.py check` — vérifie la configuration Django avant tout audit AP
- Inspecter `INSTALLED_APPS` : `activitypub` doit y figurer
- Baseline delivery: compter les tasks Celery AP en queue via `celery inspect active` ou Redis `LLEN celery`
- Baseline inbox: compter `ProcessedActivity.objects.count()` avant/après une action connue
- Tripwire : `grep -rn "httpx\." suddenly/activitypub/ --include="*.py" | grep -v "await\|async"` — appel httpx synchrone dans une vue async = deadlock potentiel

## §1 — Inbox idempotency

- Tout `POST /inbox` doit vérifier `ProcessedActivity.objects.filter(activity_id=id).exists()` **avant** tout traitement
- Pattern correct :
  ```python
  if ProcessedActivity.objects.filter(activity_id=activity_id).exists():
      return HttpResponse(status=200)
  ProcessedActivity.objects.create(activity_id=activity_id)
  # traitement...
  ```
- Race condition : utiliser `get_or_create` avec `select_for_update()` ou unique constraint sur `activity_id`
- Ne jamais traiter un `activity_id` déjà vu, même si le payload diffère — c'est une attaque de replay
- Détecter : `grep -n "ProcessedActivity" suddenly/activitypub/views.py` — absent = inbox non idempotente

## §2 — Signature HTTP (vérification)

- Vérifier la signature **avant** de parser l'activité — rejeter avec 401 si invalide
- Ne jamais fetcher la clé publique de l'acteur à chaque request — utiliser un cache (voir §4)
- Algorithme supporté : `rsa-sha256` (HTTP Signatures draft-cavage-http-signatures)
- Headers signés obligatoires : `(request-target)`, `host`, `date`, `digest`
- `Date` header : rejeter si > 30s d'écart (protection replay) :
  ```python
  from django.utils import timezone
  request_date = parse_http_date(request.headers.get("date", ""))
  if abs((timezone.now() - request_date).total_seconds()) > 30:
      return HttpResponse(status=401)
  ```
- Digest header : vérifier `SHA-256=<base64(sha256(body))>` contre le body reçu
- Détecter absence de vérification digest : `grep -n "digest" suddenly/activitypub/signatures.py`

## §3 — Fan-out delivery (livraison sortante)

- **Jamais de livraison synchrone dans une vue** — toujours via Celery task
- Pattern correct :
  ```python
  from django.db import transaction

  def create_activity(actor, activity_data):
      activity = Activity.objects.create(...)
      transaction.on_commit(lambda: deliver_activity.delay(activity.id))
  ```
- `transaction.on_commit` est obligatoire — sans lui, la task peut partir avant le commit DB et fetcher un objet inexistant
- Fan-out : une task par destinataire, pas une task avec une boucle de N appels httpx séquentiels
- Détecter livraison synchrone : `grep -rn "httpx\." suddenly/activitypub/views.py` — tout appel httpx direct dans une vue = bloquant
- Retry backoff : `@shared_task(bind=True, max_retries=5)` + `self.retry(countdown=2**self.request.retries)` (1s, 2s, 4s, 8s, 16s)
- Dead letter : après `max_retries`, logger l'échec + marquer l'instance comme unreachable (voir §7)

## §4 — Actor fetching & key caching

- Ne jamais fetcher l'acteur distant à chaque request inbox — 1 fetch = 1 appel réseau synchrone dans le critical path
- Pattern cache :
  ```python
  from django.core.cache import cache

  def get_actor_public_key(key_id: str) -> str:
      cached = cache.get(f"ap:pubkey:{key_id}")
      if cached:
          return cached
      actor_data = fetch_actor(key_id)  # httpx async
      pubkey = actor_data["publicKey"]["publicKeyPem"]
      cache.set(f"ap:pubkey:{key_id}", pubkey, timeout=3600)
      return pubkey
  ```
- TTL recommandé : 1h pour les clés publiques ; invalider sur réception d'un `Update Person` de l'acteur
- `PublicKeyCache` model (DB) comme fallback si Redis absent — mais Redis est préférable (TTL natif)
- Détecter fetch à chaque request : `grep -n "fetch_actor\|httpx\.get" suddenly/activitypub/signatures.py` sans `cache.get` à proximité = anti-pattern

## §5 — Outbox pagination (conformité AP)

- L'outbox DOIT retourner un `OrderedCollection` avec `first` pointant vers la première `OrderedCollectionPage`
- Structure conforme :
  ```json
  {
    "@context": "https://www.w3.org/ns/activitystreams",
    "type": "OrderedCollection",
    "totalItems": 42,
    "first": "https://example.com/users/alice/outbox?page=1"
  }
  ```
- Chaque `OrderedCollectionPage` doit avoir `partOf`, `next` (si page suivante), `prev` (si page précédente)
- Taille de page recommandée : 20–50 items ; ne jamais retourner tous les items sans pagination
- Détecter pagination absente : `grep -n "OrderedCollection" suddenly/activitypub/views.py | grep -v "Page"` — collection sans page = non conforme
- `Accept: application/activity+json` doit être supporté en plus de `application/ld+json; profile="https://www.w3.org/ns/activitystreams"`

## §6 — Rate limiting inbox

- `django-ratelimit` sur l'endpoint inbox : `@ratelimit(key='ip', rate='100/h', method='POST', block=True)`
- Rate limit par acteur distant (pas seulement par IP — les instances fédérées ont des IPs connues) :
  ```python
  @ratelimit(key=lambda group, request: request.headers.get("host", "unknown"), rate='500/h', block=True)
  ```
- Retourner `429 Too Many Requests` avec `Retry-After` header — ne pas retourner 200 silencieusement
- Détecter absence de rate limit : `grep -n "ratelimit\|rate_limit" suddenly/activitypub/views.py` — absent sur inbox POST = risque de flood

## §7 — Instance health & circuit breaker

- Tracker les échecs de livraison par instance distante : incrémenter un compteur Redis `ap:fail:<domain>`
- Circuit breaker : après N échecs consécutifs (ex. 5), passer en mode `retry_after=24h` pour ce domaine
- Ne jamais ignorer silencieusement les échecs de livraison — logger avec `logger.warning("AP delivery failed", extra={"domain": domain, "status": status_code})`
- Distinguer : `4xx` = erreur permanente (ne pas retry), `5xx` / timeout = retry avec backoff
- `410 Gone` sur un acteur = le supprimer localement (unfederate)
- Détecter swallowed exceptions : `grep -n "except" suddenly/activitypub/tasks.py | grep -v "retry\|logger"` — bare except sans retry ni log = anti-pattern

## §8 — Conformité AS2 (types d'objets)

- Types AP supportés : `Create`, `Update`, `Delete`, `Follow`, `Accept`, `Reject`, `Undo`, `Like`, `Announce`
- `@context` obligatoire sur tout objet : `"https://www.w3.org/ns/activitystreams"` (et éventuellement extensions)
- `id` doit être une URL stable et canonique (pas de `/inbox`, `/outbox` comme `id` d'activité)
- `actor` doit être l'URL de l'acteur, pas juste son `username`
- `object` dans un `Create` doit être l'objet complet (pas juste son `id`) pour la compatibilité maximale
- Détecter IDs non-URL : `grep -rn '"id"' suddenly/activitypub/ --include="*.py" | grep -v "http"` — IDs relatifs = non conformes

## §9 — Sécurité

- Ne jamais faire confiance à `actor` dans le payload — toujours vérifier que la signature HTTP correspond à l'`actor` déclaré
- SSRF sur fetch acteur : valider que l'URL de l'acteur est une URL distante valide (pas `localhost`, `127.0.0.1`, `169.254.x.x`) :
  ```python
  from urllib.parse import urlparse
  parsed = urlparse(actor_url)
  if parsed.hostname in ("localhost", "127.0.0.1") or parsed.hostname.startswith("169.254"):
      raise ValueError("SSRF attempt blocked")
  ```
- Signature sur les requêtes sortantes : signer TOUTES les requêtes de livraison avec la clé privée de l'acteur
- Rotation des clés : si clé compromise, publier un `Update Person` avec la nouvelle clé ET invalider le cache (voir §4)
- Content-Type sortant : toujours `application/activity+json` ou `application/ld+json; profile=...`

## §10 — Observabilité

- Logger chaque activité inbox reçue avec : `activity_id`, `type`, `actor`, `timestamp`, `status` (accepted/rejected/duplicate)
- Logger chaque livraison sortante avec : `activity_id`, `target_inbox`, `status_code`, `duration_ms`, `attempt`
- Métriques Redis recommandées : `ap:delivered:ok`, `ap:delivered:fail`, `ap:inbox:received`, `ap:inbox:duplicate`
- `django-silk` ou middleware custom pour mesurer la durée de `verify_signature` — ne doit pas dépasser 50ms
- Alerter si queue Celery AP dépasse N tasks (indique backlog de livraison)

## §11 — Vérification

- Critère déterministe : `ProcessedActivity.objects.count()` avant/après réception connue ; queue Celery avant/après publication
- Tests inbox : `pytest` + `respx` pour mocker les fetch d'acteurs distants ; vérifier idempotence (deux POSTs identiques → 1 seul traitement)
- Tests delivery : `@shared_task` + `django.test.override_settings(CELERY_TASK_ALWAYS_EAGER=True)` pour exécuter les tasks en sync dans les tests
- Test SSRF : `pytest` avec URL acteur `http://localhost/` → doit lever une exception avant tout fetch
- Test replay : envoyer deux fois la même activité avec le même `id` → deuxième doit retourner 200 sans traitement
