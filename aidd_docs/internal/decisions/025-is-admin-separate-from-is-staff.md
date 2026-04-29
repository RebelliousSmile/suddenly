# Decision: rôle is_admin distinct de is_staff

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-025        |
| Date    | 2026-04-29     |
| Feature | GMH admin panel |
| Status  | Accepted       |

## Context

Django fournit `is_staff` pour accorder l'accès à l'interface d'administration Django. Suddenly a besoin d'un rôle distinct pour les administrateurs d'instance (modération, paramètres) sans leur donner accès au Django admin.

## Decision

Ajouter un champ `is_admin = BooleanField(default=False)` sur `User`. Le décorateur `@admin_required` vérifie `is_authenticated + is_admin`. La commande `manage.py set_admin <username>` permet de promouvoir un utilisateur.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Réutiliser `is_staff` | Pas de migration | Donne accès Django admin — surface de sécurité inutile | Confond deux rôles distincts |
| Groupe Django `admins` | Extensible | Plus complexe, requiert gestion des groupes | Over-engineering pour un rôle unique |

## Consequences

- Migration de données `0007` copie `is_staff → is_admin` pour les instances existantes
- `is_staff` reste pour le Django admin uniquement
- Le panel `/gmh/` est protégé par `@admin_required`, pas `@staff_member_required`
