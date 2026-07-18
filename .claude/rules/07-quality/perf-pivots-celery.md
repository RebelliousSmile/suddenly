---
paths:
  - "**/tasks/**/*.py"
  - "**/tasks.py"
  - "**/celery.py"
  - "**/workers/**/*.py"
  - "**/beat/**/*.py"
---

# Perf pivots — Celery

Stack-specific overrides applied when `celery` is detected. Loaded by `web-optimize`.

## §0 — Pre-flight

- `celery -A myapp inspect active` → tâches actives sur tous les workers
- `celery -A myapp inspect stats` → worker stats (concurrence, pool, prefetch count)
- Détecter les tasks sans `time_limit` : `grep -rn "@shared_task\|@app\.task" . --include="*.py" | grep -v "time_limit"` — toute task sans limite peut bloquer un worker indéfiniment
- Broker config : `CELERY_BROKER_URL` en env var, jamais hardcodé — `redis://`, `amqp://`, ou `rediss://` (TLS)
- Tripwire CI : test de la task la plus critique avec `task.apply()` (exécution synchrone) → valider la logique sans worker

## §1 — Critical path

N/A — Celery est un système de queue de tâches asynchrones ; pas de render-blocking resources.

## §2 — LCP

N/A — Celery ne sert pas de pages HTML.

## §3 — CLS

N/A — Celery ne génère pas de layout.

## §4 — Bundle

N/A — pas de bundle JS/CSS côté Celery.

## §5 — CSS

N/A — Celery ne génère pas de CSS.

## §6 — Result backend et caching

- **Result backend Redis** : `CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'`
- **TTL des résultats** : `CELERY_RESULT_EXPIRES = 3600` → éviter l'accumulation en Redis (par défaut 24h)
- `CELERY_TASK_IGNORE_RESULT = True` pour les tasks sans résultat attendu → 0 écriture Redis, -50% charge broker
- **Ne jamais stocker des objets Django** dans les résultats — sérialiser en primitives (IDs, dicts JSON)

## §7 — SSR

N/A — Celery est un système d'exécution asynchrone.

## §8 — INP / TBT

N/A — Celery est un backend sans DOM.

## §9 — Backend / TTFB et fiabilité

- **`soft_time_limit` + `time_limit` obligatoires** — sans limite, une task bloquée consomme un worker indéfiniment :
  ```python
  @shared_task(soft_time_limit=300, time_limit=360)
  def process_data(item_id: int) -> None: ...
  ```
  `soft_time_limit` lève `SoftTimeLimitExceeded` (catchable pour cleanup) ; `time_limit` tue le process après 360s.

- **`acks_late=True` + `reject_on_worker_lost=True`** pour la durabilité :
  ```python
  @shared_task(acks_late=True, reject_on_worker_lost=True)
  def critical_task(item_id: int) -> None: ...
  ```
  Ack envoyé seulement après succès → en cas de crash worker, la task est re-enqueued. Sans `acks_late`, une task est ackée à la réception et perdue si le worker crashe avant de la terminer.

- **Retry avec backoff exponentiel** :
  ```python
  @shared_task(bind=True, max_retries=3)
  def task_with_retry(self, item_id: int) -> None:
      try:
          ...
      except TransientError as exc:
          raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)
  ```
  Ne jamais `retry` une `PermanentError` (ex. objet inexistant) — c'est un bug, pas un problème transitoire.

- **Idempotence obligatoire** — les tasks peuvent être rejouées (réseau, worker crash, `acks_late`) :
  ```python
  @shared_task(acks_late=True)
  def send_email_once(email_id: int) -> None:
      email = Email.objects.select_for_update().get(id=email_id)
      if email.sent_at:
          return
      # ... envoyer l'email ...
      email.sent_at = timezone.now()
      email.save(update_fields=["sent_at"])
  ```

- **Passer des IDs, pas des objets** — les objets Django ne sont pas sérialisables par défaut et leur état peut être stale au moment de l'exécution :
  ```python
  # ✅
  process_user.delay(user.id)

  # ❌ — objet sérialisé au moment de l'appel, peut être stale à l'exécution
  process_user.delay(user)
  ```

- **Queue routing par priorité** — ne pas tout envoyer en `default` :
  ```python
  CELERY_TASK_ROUTES = {
      'myapp.tasks.send_email': {'queue': 'emails'},
      'myapp.tasks.process_video': {'queue': 'heavy'},
      'myapp.tasks.notify': {'queue': 'low'},
  }
  ```
  Workers dédiés : `celery -A myapp worker -Q emails -c 4` + `celery -A myapp worker -Q heavy -c 1`

- **Prefetch count** : `CELERY_WORKER_PREFETCH_MULTIPLIER = 1` pour les tasks longues → le worker ne réserve qu'une task à la fois, meileure répartition de charge
- **Pas d'I/O bloquant dans les tasks CPU-bound** : utiliser `process_pool` (`celery worker --pool=prefork`) pour les tasks CPU-bound, `gevent`/`eventlet` pour les tasks I/O-bound

## §10 — Client-side storage

N/A — Celery est côté serveur Python.

## §11 — Verification

- **Flower** (`pip install flower`) : `celery -A myapp flower` → dashboard temps réel (workers, tasks, queues, retries)
- `celery -A myapp inspect active` → tasks en cours ; `inspect reserved` → tasks pré-fetchées
- `celery -A myapp events` → events stream (pour debugging)
- Critère déterministe : durée médiane par task type via Flower metrics ou Sentry perf traces — `p95 < soft_time_limit / 2`
- `django-celery-beat` : vérifier que les schedules Beat n'overlappent pas — `PeriodicTask.objects.filter(enabled=True)` + comparer `interval` vs durée médiane de la task

---

## Notes internes Celery (hors contrat web-optimize)

### Django integration

- `DJANGO_SETTINGS_MODULE` en env var pour le worker : `celery -A myapp worker --loglevel=info`
- `django_celery_beat.schedulers.DatabaseScheduler` pour gérer les schedules via l'admin Django
- `@shared_task` préféré à `@app.task` pour les apps Django réutilisables (découplage du `app` Celery)

### Concurrence et pool

- `prefork` (défaut) : N processes → chaque process charge Django → `--concurrency` = nb workers
- `gevent` / `eventlet` : M threads green → idéal pour tasks I/O-bound (`pip install gevent`) → `--pool=gevent --concurrency=100`
- `solo` : un seul thread, pas de multiprocess → utile pour le debug (`--pool=solo`)

### Signals et hooks

- `task_prerun` / `task_postrun` : hooks globaux pour logging, APM, DB connection management
- `task_failure` : centraliser les alertes Sentry ou Slack sur les échecs critiques

### Monitoring

- Sentry : intégration native avec `sentry-sdk[celery]` — traces automatiques des tasks
- OpenTelemetry : `opentelemetry-instrumentation-celery` pour les traces distribuées
- Prometheus : `celery-prometheus-exporter` pour les métriques Celery dans Grafana
