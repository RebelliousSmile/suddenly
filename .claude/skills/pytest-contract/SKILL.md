---
name: pytest-contract
description: Use when writing contract tests for business logic, services, or critical functions. Follows the 70/20/10 testing strategy (static analysis / contract tests / e2e).
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Pytest Contract Skill

Skill pour créer des tests contrat selon la stratégie 70/20/10.

## Philosophie 70/20/10

```
70% — Static Analysis (mypy, ruff)     → Gratuit, automatique
20% — Contract Tests (pytest)          → Logique métier critique
10% — E2E Tests (playwright)           → Parcours utilisateur
```

### Quand écrire un test contrat ?

**TESTER si TOUTES ces conditions sont vraies** :
- [ ] Contient de la logique métier (pas du CRUD simple)
- [ ] Calculs complexes ou règles métier
- [ ] Un bug casserait les données ou perdrait de l'argent
- [ ] Mypy ne peut pas détecter l'erreur
- [ ] Le code change fréquemment

**NE PAS TESTER** :
- Getters/setters simples
- CRUD basique
- Wiring de framework (URLs, configs)
- Code couvert par mypy

## Structure Tests

```
tests/
├── conftest.py              # Fixtures partagées
├── contracts/               # Tests contrat (20%)
│   ├── __init__.py
│   ├── test_character_service.py
│   ├── test_link_workflow.py
│   └── test_activitypub_serialization.py
└── e2e/                     # Tests E2E (10%)
    ├── __init__.py
    └── test_claim_journey.py
```

## Template conftest.py

```python
"""
Fixtures partagées pour les tests.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    """Utilisateur standard."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def other_user(db):
    """Deuxième utilisateur pour tests multi-users."""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='testpass123'
    )


@pytest.fixture
def game(db, user):
    """Partie de test."""
    from apps.games.models import Game
    return Game.objects.create(
        title='Test Game',
        slug='test-game',
        owner=user
    )


@pytest.fixture
def npc_character(db, user, game):
    """PNJ de test."""
    from apps.characters.models import Character, CharacterStatus
    return Character.objects.create(
        name='Test NPC',
        slug='test-npc',
        status=CharacterStatus.NPC,
        creator=user,
        origin_game=game
    )


@pytest.fixture
def pc_character(db, user, game):
    """PJ de test."""
    from apps.characters.models import Character, CharacterStatus
    return Character.objects.create(
        name='Test PC',
        slug='test-pc',
        status=CharacterStatus.PC,
        owner=user,
        creator=user,
        origin_game=game
    )


@pytest.fixture
def claim_request(db, other_user, npc_character, pc_character):
    """Demande de Claim de test."""
    from apps.characters.models import LinkRequest, LinkType
    return LinkRequest.objects.create(
        link_type=LinkType.CLAIM,
        requester=other_user,
        target_character=npc_character,
        proposed_character=pc_character,
        message='Test claim message'
    )
```

## Template Test Contrat

```python
"""
Tests contrat pour {Service}.

Ces tests vérifient les contrats de la logique métier,
pas l'implémentation interne.
"""
import pytest
from apps.{app}.services import {Service}
from apps.{app}.models import {Model}


class Test{Service}:
    """{Service} contract tests."""

    # === SETUP ===

    @pytest.fixture
    def service(self):
        """Instance du service."""
        return {Service}()

    # === SUCCESS CASES ===

    def test_{action}_creates_{result}(self, service, {fixtures}):
        """
        GIVEN: {preconditions}
        WHEN: {action}
        THEN: {expected result}
        """
        result = service.{method}({params})

        assert result is not None
        assert result.{field} == {expected}

    def test_{action}_updates_{model}_status(self, service, {fixtures}):
        """Vérifie la mise à jour du statut après {action}."""
        service.{method}({params})

        {model}.refresh_from_db()
        assert {model}.status == {expected_status}

    # === EDGE CASES ===

    def test_{action}_with_{edge_case}(self, service, {fixtures}):
        """Gère le cas limite: {edge_case}."""
        # Setup edge case
        {setup}

        result = service.{method}({params})

        assert {edge_assertion}

    # === ERROR CASES ===

    def test_{action}_raises_on_{error_condition}(self, service, {fixtures}):
        """Lève une erreur si {error_condition}."""
        with pytest.raises({ExceptionType}, match="{message pattern}"):
            service.{method}({invalid_params})

    def test_{action}_with_invalid_{param}_raises(self, service, {fixtures}):
        """Valide le paramètre {param}."""
        with pytest.raises(ValueError):
            service.{method}({param}=None)
```

## Exemple Concret : CharacterLinkService

```python
"""
Tests contrat pour CharacterLinkService.
"""
import pytest
from apps.characters.services import CharacterLinkService
from apps.characters.models import (
    CharacterLink, LinkType, CharacterStatus, LinkRequestStatus
)


class TestCharacterLinkServiceAcceptClaim:
    """Tests pour CharacterLinkService.accept_claim()."""

    @pytest.fixture
    def service(self):
        return CharacterLinkService()

    # === SUCCESS ===

    def test_accept_claim_creates_character_link(
        self, service, claim_request
    ):
        """
        GIVEN: Une demande de claim valide
        WHEN: On accepte le claim
        THEN: Un CharacterLink est créé
        """
        link = service.accept_claim(claim_request)

        assert link.link_type == LinkType.CLAIM
        assert link.source == claim_request.proposed_character
        assert link.target == claim_request.target_character
        assert link.link_request == claim_request

    def test_accept_claim_updates_target_status_to_claimed(
        self, service, claim_request
    ):
        """Le PNJ cible passe en statut CLAIMED."""
        service.accept_claim(claim_request)

        claim_request.target_character.refresh_from_db()
        assert claim_request.target_character.status == CharacterStatus.CLAIMED

    def test_accept_claim_updates_request_status(
        self, service, claim_request
    ):
        """La demande passe en statut ACCEPTED."""
        service.accept_claim(claim_request)

        claim_request.refresh_from_db()
        assert claim_request.status == LinkRequestStatus.ACCEPTED
        assert claim_request.resolved_at is not None

    # === ERRORS ===

    def test_accept_claim_rejects_non_claim_request(
        self, service, db, other_user, npc_character
    ):
        """Refuse d'accepter une demande qui n'est pas un Claim."""
        from apps.characters.models import LinkRequest
        adopt_request = LinkRequest.objects.create(
            link_type=LinkType.ADOPT,
            requester=other_user,
            target_character=npc_character,
            message='Test'
        )

        with pytest.raises(ValueError, match="Not a claim"):
            service.accept_claim(adopt_request)

    def test_accept_claim_rejects_already_accepted(
        self, service, claim_request
    ):
        """Refuse d'accepter un claim déjà accepté."""
        service.accept_claim(claim_request)

        with pytest.raises(ValueError, match="already processed"):
            service.accept_claim(claim_request)


class TestCharacterLinkServiceRejectClaim:
    """Tests pour CharacterLinkService.reject_claim()."""

    @pytest.fixture
    def service(self):
        return CharacterLinkService()

    def test_reject_claim_updates_request_status(
        self, service, claim_request
    ):
        """La demande passe en statut REJECTED."""
        service.reject_claim(claim_request, reason="Not interested")

        claim_request.refresh_from_db()
        assert claim_request.status == LinkRequestStatus.REJECTED
        assert claim_request.response_message == "Not interested"

    def test_reject_claim_does_not_change_character(
        self, service, claim_request
    ):
        """Le PNJ cible reste inchangé."""
        original_status = claim_request.target_character.status

        service.reject_claim(claim_request, reason="No")

        claim_request.target_character.refresh_from_db()
        assert claim_request.target_character.status == original_status
```

## Commandes

```bash
# Lancer tous les tests contrat
pytest tests/contracts/ -v

# Avec couverture
pytest tests/contracts/ --cov=apps --cov-report=html

# Un fichier spécifique
pytest tests/contracts/test_character_service.py -v

# Un test spécifique
pytest tests/contracts/test_character_service.py::TestCharacterLinkServiceAcceptClaim::test_accept_claim_creates_character_link -v

# Parallèle
pytest tests/contracts/ -n auto
```

## Checklist Test Contrat

Avant d'écrire :
- [ ] Le code contient de la logique métier ?
- [ ] Mypy ne suffit pas à détecter les bugs ?
- [ ] Un bug aurait un impact significatif ?

Pendant l'écriture :
- [ ] Docstring GIVEN/WHEN/THEN
- [ ] Un assert principal par test
- [ ] Cas de succès + cas d'erreur
- [ ] Fixtures réutilisables dans conftest.py

Après l'écriture :
- [ ] Tests passent : `pytest tests/contracts/`
- [ ] Pas de dépendance à l'ordre d'exécution
- [ ] Pas de state partagé entre tests
