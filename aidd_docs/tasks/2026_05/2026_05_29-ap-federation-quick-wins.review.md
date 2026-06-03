# Revue de code — AP Federation Quick Wins

- **Branche** : `feat/ap-federation-quick-wins`
- **Base** : `main`
- **Date** : 2026-05-29
- **Périmètre** : `suddenly/activitypub/{_http,signatures,inbox,tasks,views,urls}.py`, `pyproject.toml`, `tests/activitypub/test_quick_wins.py`
- **Référentiel** : `.claude/rules/` (ap-pivots, 08-activitypub, perf-pivots-celery, dry-refactor)

## Verdict global

Implémentation fidèle au plan, conforme aux règles. Aucun bloqueur. Tous les critères d'acceptance sont satisfaits, 7 tests verts, mypy clean. Deux points de fiabilité hérités deviennent actifs avec le câblage de `inbox.py` — à traiter en suivi, hors scope quick wins.

---

## Findings

### [MAJEUR] Activité marquée traitée même si le handler échoue — `inbox.py:179-186`

`process_inbox` crée `ProcessedActivity` (idempotence) **avant** d'exécuter le handler, puis catch l'exception du handler et retourne quand même 202. Conséquence : si un handler lève (ex. réseau pendant `get_or_create_remote_user`), l'activité est définitivement marquée traitée — le remote qui réessaiera recevra 202 "duplicate" et l'effet de bord ne se produira jamais.

- **Pré-existant** dans `inbox.py`, mais ce chemin devient **live** avec la Phase 2 (avant, l'endpoint actif était `views.py`).
- **Hors scope** des quick wins, mais à inscrire en suivi (F1 fiabilité).
- **Fix suggéré** : ne créer `ProcessedActivity` qu'après succès du handler, ou wrapper handler+création dans une `transaction.atomic()` avec rollback de la ligne sur exception.

### [MINEUR] SSRF — fenêtre TOCTOU / DNS rebinding — `_http.py:42-61`

Le guard résout le hostname (`getaddrinfo`) pour valider les IP, puis `httpx` se reconnecte **par hostname** (nouvelle résolution DNS). Un attaquant contrôlant le DNS peut renvoyer une IP publique au check puis une IP privée à la requête réelle.

- **Pré-existant** (copié verbatim depuis `federation_views._fetch_actor`) — pas une régression. La mutualisation est correcte (DRY respecté).
- **Fix idéal (suivi)** : résoudre une fois, puis passer l'IP validée à httpx via `Host` header + connexion sur l'IP, ou utiliser un transport custom qui pin l'IP résolue.

### [MINEUR] `acks_late=True` → re-livraison possible en double — `tasks.py:186-193`

Avec `acks_late=True` + `time_limit`, une task tuée (timeout/crash worker) est ré-enfilée → `deliver_activity` peut POSTer deux fois la même activité au remote.

- **Acceptable** : les inbox AP distantes sont idempotentes par `id` d'activité (c'est exactement ce que notre §1 implémente côté réception). Le risque est borné côté remote.
- **Conforme** à `perf-pivots-celery §9` (durabilité prime). Aucun changement requis ; noté pour traçabilité.

### [NIT] Double lookup de l'acteur local — `inbox.py:74/87/100`

Le guard 404 appelle `get_local_actor(...)`, puis `process_inbox` → handler rappelle `get_local_actor(...)`/`get_local_actor` en interne. 2 requêtes DB pour la même entité.

- Acceptable pour la clarté sécuritaire (fail-fast 404). Optimisable en passant l'instance résolue à `process_inbox` si besoin perf.

### [NIT] `import ipaddress` dans la boucle — `_http.py:47`

`import ipaddress` est à l'intérieur de la boucle `for ... in resolved`. Fonctionne (import caché), mais le déplacer en tête de fonction (à côté de `socket`) serait plus propre. Style hérité de l'original.

---

## Points conformes (vérifiés)

- **DRY (rule of three)** : les 4 fetches httpx dupliqués consolidés dans `fetch_ap_actor` ✓ — exactement la règle `dry-refactor`.
- **Date skew** : `parse_http_date` → `datetime.fromtimestamp(ts, tz=UTC)` vs `timezone.now()`, deux datetimes aware, comparaison correcte ; skip gracieux si header absent/non parseable ✓.
- **Ordre `process_inbox`** : rate-limit → signature → parse → actor domain → idempotence → handler — conforme DEC-021 (rate-limit avant signature) ✓.
- **429 + Retry-After** sur rate limit ✓ ; **403** sur signature/skew invalides (cohérent, pas de faux 401) ✓.
- **`deliver_activity`** : 410→log+return (aucune suppression d'acteur, conforme au scope), autres 4xx→log+return, 5xx + RequestError→retry exponentiel `2**n*60` ✓. `self.retry` (raise `Retry`) non capté par `except httpx.RequestError` ✓.
- **Signature sortante** : 7 call sites `deliver_activity.delay` passent tous `actor_key_id`+`private_key_pem` ; fallback `(None,None)` géré ✓.
- **`fetch_remote_actor`** conserve son timeout 30s ✓.
- **Nettoyage imports** `views.py` (`json`, `csrf_exempt`, `require_POST` retirés), stubs morts supprimés ✓.
- **Type hints** présents partout, mypy `Success: no issues found in 16 source files` ✓.

---

## Scores

- **Complétude** : 10/10 — toutes les tâches et critères d'acceptance du plan sont implémentés.
- **Qualité** : 8.5/10 — code propre et conforme ; -1.5 pour le risque idempotence/handler (MAJEUR hérité désormais actif) et la TOCTOU SSRF.

## Suivi recommandé (hors quick wins)

1. [MAJEUR] Idempotence : ne marquer `ProcessedActivity` qu'après succès handler.
2. [MINEUR] SSRF : pin de l'IP résolue pour fermer la fenêtre DNS rebinding.
