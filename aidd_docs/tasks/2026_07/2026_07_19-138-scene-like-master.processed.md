---
name: master_plan
description: Parent plan orchestrating Scene Like (#138) — local toggle first, AP federation second
argument-hint: N/A
---

# Master Plan: Like des scènes (#138)

## Overview

- **Goal**: Permettre à un utilisateur connecté de liker/unliker une scène (`Report`) avec persistance, état reflété au chargement, et sémantique AP `Like` optionnelle.
- **Risk Score**: 5/10 (migration schéma +3 · 4 modules touchés +2)
- **Branch**: `feat/138-scene-like`
- **Ticket**: https://github.com/RebelliousSmile/suddenly/issues/138

## Child Plans

| #   | Plan                          | File            | Status  | Validated |
| --- | ----------------------------- | --------------- | ------- | --------- |
| 1   | Like local (toggle + UI)      | `./*-part-1.md` | pending | [ ]       |
| 2   | Fédération AP `Like` / `Undo` | `./*-part-2.md` | blocked | [ ]       |

<!-- Status values: pending, in-progress, done, blocked -->
<!-- RULE: Plan N+1 blocked until Plan N checkbox checked -->

## Independence guarantee

- Part 1 livre un Like local fonctionnel (toggle + persistance + état initial) sans aucune fédération. Testable et déployable seul.
- Part 2 ajoute uniquement l'envoi d'activités AP `Like` / `Undo(Like)` vers l'acteur distant. Aucune modification du schéma ni de l'UX de Part 1.

## Key decisions (baked into the plans)

- **Modèle** : `Like` dans `suddenly/games/models.py` (co-localisé avec `Report`), hérite de `BaseModel` (UUID PK + `created_at`/`updated_at`). Contrainte d'unicité `(user, report)`.
- **Compteur** : PAS de dénormalisation `likes_count` au MVP. Le bouton n'affiche aujourd'hui qu'un cœur sans nombre. L'état `liked` est annoté via `Exists` (pas de N+1). Un `Count` annoté reste ajoutable plus tard sans migration.
- **Vue** : endpoint `feed:like` (POST), toggle create/delete, décoré `@require_POST` **avant** `@login_required`, retourne le partial HTML (jamais JSON). Note : `recommend_report` actuel utilise un garde `request.method != POST` manuel + `JsonResponse` — le nouveau `like` suit la règle projet stricte (`@require_POST`).
- **Anonyme** : comportement aligné sur Recommend — bouton affiché, clic → `@login_required` redirige vers login. `liked=False` pour tout utilisateur non authentifié (pas d'annotation).
- **Fédération** : AP `Like` dirigé vers l'acteur/objet distant (pas un broadcast followers comme `Announce`). `Undo(Like)` à l'unlike. Envoi uniquement si `report.remote` et `report.ap_id` présents.

## Validation Protocol

1. Compléter Part 1, lancer `pytest -k like`, `ruff check .`, `mypy suddenly/`
2. [ ] Checkpoint 1: User confirms le like local fonctionne (toggle + refresh)
3. Débloquer Part 2, répéter
4. [ ] Final: Test d'intégration like sur scène distante → activité `Like` en queue

## Estimations

- **Confidence**: 9/10
- **Duration**: Part 1 ~0.5j · Part 2 ~0.5j
