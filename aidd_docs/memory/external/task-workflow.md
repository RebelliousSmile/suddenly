# Task Workflow (historique)

> Workflow de développement défini avant l'adoption d'AIDD. Conservé comme référence historique.
> Le workflow actif est maintenant dans `.claude/rules/custom/09-aidd-workflow.md`.

## Flux

```
Tâche → Plan → Review Plan → Implementation → Tests → Review Code → Commit
         ↑         ↓                              ↑         ↓
         └── Fix ──┘                              └── Fix ──┘
```

## DIRECT vs STEP-BY-STEP

| Mode | Conditions |
|------|-----------|
| DIRECT | < 2h, < 3 fichiers, complexité faible |
| STEP-BY-STEP | > 2h, > 3 fichiers, complexité moyenne/haute |

## Commandes de validation

```bash
# Statique (70%)
mypy apps/ --strict && ruff check apps/ && black --check apps/

# Tests contrats (20%)
pytest tests/contracts/ -v

# Tests E2E critiques (10%)
pytest tests/e2e/ -m critical
```

## Modules critiques (tests obligatoires)

| Module | Raison |
|--------|--------|
| `suddenly/characters/services.py` | Logique Claim/Adopt/Fork |
| `suddenly/activitypub/inbox.py` | Réception activités fédération |
| `suddenly/activitypub/serializers.py` | Sérialisation ActivityPub |
| `suddenly/activitypub/signatures.py` | HTTP Signatures |
