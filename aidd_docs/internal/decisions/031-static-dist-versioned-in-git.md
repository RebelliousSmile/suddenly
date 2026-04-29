---
name: decision
description: static/dist/ versionné dans git pour déploiement sans Node
type: decision
---

# Decision: static/dist/ versionné dans git

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-031        |
| Date    | 2026-04-29     |
| Feature | Déploiement    |
| Status  | Accepted       |

## Context

L'hébergeur principal (Alwaysdata PaaS) ne dispose pas de Node.js ni de pnpm. Le déploiement est déclenché par `git pull` + script shell sans étape de build frontend possible.

## Decision

Versionner `static/dist/` dans git. Le build frontend est exécuté en local puis commité avec le code applicatif.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Build en CI/CD | Assets toujours à jour, pas de pollution du repo | Nécessite un runner avec Node, pipeline complexe | Pas adapté à Alwaysdata sans CI dédiée |
| CDN pour les assets | Pas de build serveur | Dépendance externe, latence, versioning complexe | Trop de complexité pour le MVP |

## Consequences

- Chaque modification du frontend nécessite `pnpm run build` + commit de `static/dist/`
- Le `.gitignore` ne doit pas exclure `static/dist/`
- Le script `scripts/deploy-alwaysdata.sh` ne contient pas d'étape build — c'est intentionnel
