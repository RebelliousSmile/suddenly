# Revue fonctionnelle — AP Federation Quick Wins

- **Branche** : `feat/ap-federation-quick-wins`
- **Date** : 2026-05-29
- **Plan** : `2026_05_29-ap-federation-quick-wins.md`

## Conformité au plan

| Phase | Statut | Preuve |
|-------|--------|--------|
| 1 — SSRF mutualisé | ✅ | `_http.fetch_ap_actor`, 4 call sites migrés, `fetch_remote_actor` garde 30s |
| 2 — Inbox câblé + skew + 404 | ✅ | `urls.py`→`inbox.py`, stubs `views.py` supprimés, 429+Retry-After, 404 guard, date skew gracieux |
| 3 — Signature Accept/Reject | ✅ | 7 call sites `deliver_activity.delay` avec `actor_key_id`+`private_key_pem` |
| 4 — Hardening delivery | ✅ | `acks_late`, `reject_on_worker_lost`, `time_limit=150`, 410/4xx/5xx, backoff exponentiel |
| 5 — Tests + coverage | ✅ | 7 tests verts, `inbox.py`/`tasks.py` retirés de `coverage.omit` |

## Régression détectée et corrigée

| Titre | Fichiers | Score initial | Statut |
|-------|----------|---------------|--------|
| Inbox `invalid_json` retournait 403 au lieu de 400 (signature vérifiée avant parse — comportement correct, tests obsolètes) | `tests/test_views.py:296,391` | 2 — Majeur | ✅ Corrigé (mock `verify_signature`+`_check_rate_limit`) |

## Résultat final des tests

- `tests/test_views.py -k inbox` : **6 passed, 2 skipped, 0 failed**
- `tests/activitypub/` : **tous verts** (dont les 7 nouveaux quick-wins)
- 10 échecs résiduels sur `TestHomeView`/`TestProfileView` : `Missing staticfiles manifest entry` — **environnemental** (collectstatic non lancé), pré-existant, hors périmètre activitypub.

## Hors scope (reportés explicitement par le plan)

- [Mineur] Idempotence : `ProcessedActivity` créé avant succès du handler (`inbox.py:179`) — désormais actif, à traiter en F1 fiabilité.
- [Suivi] TOCTOU SSRF / DNS rebinding (`_http.py:42`).

## Verdict

Implémentation conforme au plan, 0 deal-breaker, 1 régression corrigée. Prêt pour commit.
