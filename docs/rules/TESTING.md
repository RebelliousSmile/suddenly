---
name: testing
description: Stratégie de tests pour Suddenly (70/20/10)
---

# Testing — Règles

## Stratégie 70/20/10

| Niveau | % | Outils | Cible |
|--------|---|--------|-------|
| **Analyse statique** | 70% | mypy, ruff, black | Tous les fichiers `apps/` |
| **Tests contrats** | 20% | pytest + pytest-django | Logique métier critique |
| **Tests E2E** | 10% | pytest | Parcours utilisateurs critiques |

## Outils

- **mypy** : vérification types statique (strict)
- **ruff** : linter Python
- **black** : formateur
- **pytest** : runner de tests
- **pytest-django** : fixtures Django (TestCase, Client)

## Commandes

```bash
# Analyse statique (70%)
mypy apps/ --strict
ruff check apps/
black --check apps/

# Tests contrats (20%)
pytest tests/contracts/ -v

# Tests E2E critiques (10%)
pytest tests/e2e/ -m critical

# Check qualité complet
make quality
```

## Ce qu'il FAUT tester

**OBLIGATOIRE** (tests contrats) :
- Claim/Adopt/Fork logic → `tests/contracts/test_claim.py`, `test_adopt.py`, `test_fork.py`
- Transitions de statut Character (NPC → CLAIMED/ADOPTED/FORKED)
- Sérialisation/désérialisation ActivityPub
- HTTP Signatures (création et vérification)
- Permissions (qui peut Claim quoi)
- Workflow SharedSequence (obligatoire pour valider un lien)

**OBLIGATOIRE** (tests E2E critiques) :
- Publication d'un CR avec personnages
- Flux complet Adopt (demande → acceptation → séquence)
- Réception d'une activité AP entrante

## Ce qu'il NE FAUT PAS tester

- CRUD Django simple (vues liste/détail)
- Opérations Django ORM basiques
- Rendu de templates
- Migrations

## Couverture cible

| Périmètre | Cible |
|-----------|-------|
| Chemins critiques (federation, links) | 90% |
| Logique métier (services) | 70% |
| Minimum global | 50% |

## Règles de test

1. **Never mock functional components** — ne jamais mocker les services métier
2. **Tests first for bug fixes** — toujours écrire un test qui reproduit le bug avant de le corriger
3. **Fixtures Django** — utiliser `pytest-django` et `django.test.Client`
4. **DB isolation** — chaque test dans une transaction rollback (`@pytest.mark.django_db`)

## Structure des tests

```
tests/
├── contracts/
│   ├── conftest.py         # Fixtures partagées
│   ├── test_claim.py       # Logique Claim
│   ├── test_adopt.py       # Logique Adopt
│   ├── test_fork.py        # Logique Fork
│   ├── test_activitypub.py # Sérialisation AP
│   └── test_signatures.py  # HTTP Signatures
└── e2e/
    ├── conftest.py
    ├── test_report_publication.py  # Publication CR
    └── test_adopt_flow.py          # Flux Adopt complet
```

## Modules critiques à tester

| Module | Tests minimaux |
|--------|---------------|
| `apps/characters/services.py` | Tous les cas Claim/Adopt/Fork |
| `apps/federation/handlers.py` | Follow, Create, Offer, Accept, Reject |
| `apps/federation/signatures.py` | Signature valide, invalide, expirée |
| `core/models.py` | ActivityPubMixin.get_ap_id() |
