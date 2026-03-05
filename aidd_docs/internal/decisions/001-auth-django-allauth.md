# Decision: Auth via django-allauth

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-001        |
| Date    | 2026-03-05     |
| Feature | Authentification |
| Status  | Accepted       |

## Context

US-01 nécessite un système d'inscription et de connexion. Le projet doit choisir entre une solution maison, django-allauth, ou un SSO/OAuth dès le MVP.

## Decision

Utiliser django-allauth comme seul mécanisme d'authentification au MVP. OAuth/SSO (Google, Discord) reporté post-MVP.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Auth Django native | Zéro dépendance | Pas de social auth, pas de gestion email | Trop limité pour évoluer |
| OAuth/SSO dès le MVP | UX moderne | Complexité, dépendances externes | Over-engineering pour le MVP |

## Consequences

- django-allauth gère inscription, login, reset password, email verification
- Le modèle User reste compatible avec un ajout OAuth ultérieur
- Pas de "Login with Google/Discord" au lancement
