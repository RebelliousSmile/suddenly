---
paths:
  - "**/clients/**/*.py"
  - "**/gateway/**/*.py"
  - "**/services/**/*.py"
  - "**/api/**/*.py"
  - "**/http/**/*.py"
---

# Perf pivots — httpx

Stack-specific overrides applied when `httpx` is detected. Loaded by `web-optimize`. Focus: external API call latency, connection reuse, and fault tolerance.

## §0 — Pre-flight

- `httpx.get(...)` ou `httpx.AsyncClient()` instancié par call = connexion TCP créée/fermée à chaque requête
- Détecter : `grep -rn "httpx\.get\|httpx\.post\|httpx\.AsyncClient()" . --include="*.py"` — appels directs hors singleton ou client instancié dans une boucle
- Tripwire CI : `mypy --strict` avec annotations de timeout → `httpx.TimeoutException` non catchée = fail
- Baseline TTFB : `curl -o /dev/null -s -w "%{time_starttransfer}" <provider_url>` — comparer avec les latences loggées en prod

## §1 — Critical path

N/A — httpx est un client HTTP sortant ; pas de render-blocking resources côté serveur.

## §2 — LCP

N/A — httpx ne sert pas de pages HTML ; LCP géré par le frontend séparé.

## §3 — CLS

N/A — httpx ne génère pas de layout.

## §4 — Bundle

N/A — pas de bundle JS/CSS côté httpx.

## §5 — CSS

N/A — httpx ne génère pas de CSS.

## §6 — Caching

- Réponses idempotentes (GET public) : cacher localement avant d'appeler le provider, via `cachetools.TTLCache` ou Redis
- httpx n'a pas de cache HTTP natif → cache applicatif : `result = cache.get(key) or await client.get(url)`
- `ETag` / `Last-Modified` : implémenter manuellement via headers `If-None-Match` / `If-Modified-Since`
- Ne jamais cacher des réponses contenant des données utilisateur ou des tokens OAuth

## §7 — SSR

N/A — httpx est un client sortant pur.

## §8 — INP / TBT

N/A — httpx est un client backend sans DOM.

## §9 — Backend / TTFB

- **AsyncClient en singleton** (pattern obligatoire) — jamais instancié par call :
  ```python
  # ✅ singleton module-level
  _client: httpx.AsyncClient | None = None

  def get_client() -> httpx.AsyncClient:
      global _client
      if _client is None:
          _client = httpx.AsyncClient(
              limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
              timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
          )
      return _client

  # ❌ connexion TCP créée/fermée à chaque call
  async def call_api() -> httpx.Response:
      async with httpx.AsyncClient() as client:
          return await client.get(url)
  ```
- **Timeouts explicites obligatoires** : call sans timeout peut bloquer indéfiniment l'event loop → `httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)` sur le client singleton
- **Connection pool** : `Limits(max_connections=100, max_keepalive_connections=20)` — ajuster selon `uvicorn --workers` × concurrences attendues par worker
- **Requêtes concurrentes** : `asyncio.gather(client.get(url1), client.get(url2))` — jamais séquentielles pour des calls indépendants ; max 3 séquentiels avant de passer à `gather`
- **Retry avec backoff exponentiel** :
  ```python
  import tenacity

  @tenacity.retry(
      stop=tenacity.stop_after_attempt(3),
      wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
      retry=tenacity.retry_if_exception_type(httpx.TransientError),
  )
  async def call_with_retry(url: str) -> httpx.Response: ...
  ```
- **HTTP/2** : `httpx.AsyncClient(http2=True)` pour providers qui le supportent (réduit overhead sur connexions long-lived)
- **Event hooks** pour logger la latence par call :
  ```python
  async def log_request(request: httpx.Request) -> None:
      request.extensions["start_time"] = time.perf_counter()

  async def log_response(response: httpx.Response) -> None:
      elapsed = time.perf_counter() - response.request.extensions["start_time"]
      logger.info("httpx %s %s → %d (%.2fs)",
                  response.request.method, response.url,
                  response.status_code, elapsed)

  client = httpx.AsyncClient(event_hooks={"request": [log_request], "response": [log_response]})
  ```

## §10 — Client-side storage

N/A — httpx est côté serveur Python ; pas d'accès à localStorage / sessionStorage.

## §11 — Verification

- Critère déterministe : latence p50/p95 par endpoint externe loggée via event hooks → comparer avant/après
- Connexions TCP actives : `ss -tnp | grep <port_provider>` sur le serveur — vérifier que le pool est réutilisé
- Tests : `pytest` + `respx` (mock httpx) pour valider retry et timeout sans appel réseau réel
- `httpx.MockTransport` pour tests unitaires du singleton sans mocker globalement
