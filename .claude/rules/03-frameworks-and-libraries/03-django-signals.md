---
paths:
  - "suddenly/**/apps.py"
  - "suddenly/**/signals.py"
  - "suddenly/**/cache_invalidation.py"
  - "suddenly/**/notification_signals.py"
---

# Django signals — cache invalidation et handlers transverses

## Connexion

- Connecter les signaux dans `AppConfig.ready()` — jamais au top-level d'un module
- Toujours passer `dispatch_uid="<app>.<purpose>"` unique par `connect`
  **Why:** sans `dispatch_uid`, l'autoreload dev et `--reuse-db` créent des handlers dupliqués qui restent connectés
- Renommer un handler → renommer son `dispatch_uid` aussi
- Imports lazy dans `ready()` — `from suddenly.x.models import Y` à l'intérieur, pas en haut du fichier
  **Why:** le top-level s'évalue avant que toutes les apps soient prêtes

## Handlers de cache

- Vivre dans `core/cache_invalidation.py` (centralisé), pas dans chaque app
- Imports lazy dans le handler aussi — `def invalidate_x(sender, **kwargs): from ... import Z`
- Filtrer `m2m_changed.action` : agir uniquement sur `post_add / post_remove / post_clear`
  ```python
  _M2M_ACTIONS = {"post_add", "post_remove", "post_clear"}
  if action is not None and action not in _M2M_ACTIONS:
      return
  ```
  **Why:** sans filtre, le handler tire deux fois (pre + post) et invalide le cache à mauvais escient

## Service-layer cache

- Préférer `cache.get_or_set` côté service à `@cache_page` côté vue
  **Why:** invalidation déterministe par signal, granularité fine par requête, pas de couplage à la URL
- Lister les paramètres de clés dans une constante (ex. `RECENT_REPORTS_LIMITS: tuple[int, ...] = (3,)`)
  **Why:** le handler doit pouvoir énumérer toutes les clés à supprimer

## Effets de bord fédération / réseau

- Diffusion AP (`Create`, broadcast) déclenchée par un signal → toujours via `transaction.on_commit(...)`, jamais inline dans le handler
  **Why:** inline, la tâche part avant le commit — un rollback laisse une activité diffusée sans objet en base, ou la tâche lit une ligne pas encore committée

## Tests

- Pattern sentinelle : `cache.set(key, ["sentinel"], 600)` → mutation → `assert cache.get(key) is None`
- Fixture `autouse` `cache.clear()` pour isoler les tests
- Tester explicitement le filtre d'action : appeler le handler avec `action="pre_add"` et vérifier que la sentinelle survit
