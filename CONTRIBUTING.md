# Contribuer à Suddenly

Merci de votre intérêt pour Suddenly ! Ce guide vous aidera à contribuer au projet.

---

## Table des Matières

1. [Code de Conduite](#code-de-conduite)
2. [Comment Contribuer](#comment-contribuer)
3. [Configuration de l'Environnement](#configuration-de-lenvironnement)
4. [Workflow de Développement](#workflow-de-développement)
5. [Standards de Code](#standards-de-code)
6. [Tests](#tests)
7. [Pull Requests](#pull-requests)
8. [Signaler un Bug](#signaler-un-bug)

---

## Code de Conduite

Ce projet adhère à un code de conduite inclusif. En participant, vous vous engagez à maintenir un environnement accueillant pour tous.

**Comportements attendus** :
- Être respectueux et bienveillant
- Accepter les critiques constructives
- Se concentrer sur ce qui est le mieux pour la communauté

---

## Comment Contribuer

### Types de Contributions

| Type | Description |
|------|-------------|
| **Bug fix** | Corriger un problème identifié |
| **Feature** | Ajouter une nouvelle fonctionnalité |
| **Documentation** | Améliorer la documentation |
| **Traduction** | Ajouter/améliorer des traductions |
| **Tests** | Ajouter des tests manquants |

### Avant de Commencer

1. **Vérifiez les issues existantes** pour éviter les doublons
2. **Créez une issue** pour discuter des changements majeurs
3. **Lisez la documentation** dans `documentation/`

---

## Configuration de l'Environnement

### Prérequis

- Python 3.12+
- PostgreSQL 16+
- Git

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-fork/suddenly.git
cd suddenly

# Créer l'environnement virtuel
python -m venv venv

# Activer (Linux/macOS)
source venv/bin/activate

# Activer (Windows)
.\venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dépendances de développement

# Créer la base de données
createdb suddenly_dev

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos paramètres

# Appliquer les migrations
python manage.py migrate

# Lancer le serveur de développement
python manage.py runserver
```

### Variables d'Environnement

```bash
# .env
DEBUG=True
SECRET_KEY=your-secret-key-for-dev
DATABASE_URL=postgres://user:pass@localhost/suddenly_dev
DOMAIN=localhost:8000
```

---

## Workflow de Développement

### Branches

```
main          ← Production, stable
├── develop   ← Développement, intégration
│   ├── feature/xxx   ← Nouvelles fonctionnalités
│   ├── fix/xxx       ← Corrections de bugs
│   └── docs/xxx      ← Documentation
```

### Processus

1. **Fork** le dépôt sur GitHub
2. **Clone** votre fork localement
3. **Créez une branche** depuis `develop`
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/ma-fonctionnalite
   ```
4. **Développez** en suivant les standards
5. **Testez** vos modifications
6. **Committez** avec des messages clairs
7. **Push** vers votre fork
8. **Créez une Pull Request** vers `develop`

---

## Standards de Code

### Python

- **Style** : PEP 8 + Black (formatter)
- **Linting** : Ruff
- **Types** : Annotations de type obligatoires (mypy)
- **Docstrings** : Format Google

```python
def calculate_score(user: User, game: Game) -> int:
    """Calcule le score d'un utilisateur pour une partie.

    Args:
        user: L'utilisateur concerné.
        game: La partie pour laquelle calculer le score.

    Returns:
        Le score calculé.

    Raises:
        ValueError: Si l'utilisateur n'a pas participé à la partie.
    """
    ...
```

### Commandes de Vérification

```bash
# Formatter
black apps/ tests/

# Linter
ruff check apps/ tests/

# Types
mypy apps/

# Tout vérifier
make lint
```

### Templates Django

- Indentation : 2 espaces
- Classes Tailwind : ordonnées (layout → spacing → typography → colors)
- HTMX : attributs préfixés `hx-`

### Commits

Format : `type(scope): description`

```
feat(characters): add fork relationship display
fix(federation): handle timeout on remote inbox
docs(api): update ActivityPub endpoints
test(games): add report publication tests
refactor(users): extract avatar processing
```

Types : `feat`, `fix`, `docs`, `test`, `refactor`, `style`, `chore`

---

## Tests

### Structure

```
tests/
├── unit/           # Tests unitaires (rapides, isolés)
├── integration/    # Tests d'intégration (DB, services)
├── contracts/      # Tests de contrat ActivityPub
└── conftest.py     # Fixtures partagées
```

### Exécution

```bash
# Tous les tests
pytest

# Tests unitaires uniquement
pytest tests/unit/

# Tests avec couverture
pytest --cov=apps --cov-report=html

# Tests en parallèle
pytest -n auto

# Un fichier spécifique
pytest tests/unit/test_characters.py

# Verbose
pytest -v
```

### Ratio Recommandé

| Type | Ratio | Description |
|------|-------|-------------|
| Unit | 70% | Rapides, logique métier |
| Integration | 20% | DB, services externes |
| Contract | 10% | Compatibilité ActivityPub |

### Écrire un Test

```python
import pytest
from apps.characters.models import Character

class TestCharacterStatus:
    """Tests pour les changements de statut des personnages."""

    def test_npc_can_be_claimed(self, npc_character: Character) -> None:
        """Un PNJ peut être réclamé."""
        assert npc_character.can_be_claimed() is True

    def test_pc_cannot_be_claimed(self, pc_character: Character) -> None:
        """Un PJ ne peut pas être réclamé."""
        assert pc_character.can_be_claimed() is False
```

---

## Pull Requests

### Checklist

Avant de soumettre :

- [ ] Les tests passent (`pytest`)
- [ ] Le code est formatté (`black`)
- [ ] Pas d'erreurs de lint (`ruff check`)
- [ ] Les types sont corrects (`mypy`)
- [ ] La documentation est à jour si nécessaire
- [ ] Les migrations sont incluses si nécessaire

### Template PR

```markdown
## Description

Brève description des changements.

## Type de changement

- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Breaking change
- [ ] Documentation

## Comment tester

1. Étape 1
2. Étape 2
3. Résultat attendu

## Screenshots (si applicable)

## Checklist

- [ ] Tests ajoutés/mis à jour
- [ ] Documentation mise à jour
- [ ] Migrations incluses
```

### Review

- Un reviewer minimum requis
- Répondez aux commentaires
- Squash des commits avant merge

---

## Signaler un Bug

### Avant de Signaler

1. Vérifiez que le bug n'est pas déjà signalé
2. Testez avec la dernière version
3. Isolez le problème

### Template Issue

```markdown
## Description

Description claire et concise du bug.

## Reproduction

1. Aller à '...'
2. Cliquer sur '...'
3. Voir l'erreur

## Comportement Attendu

Ce qui devrait se passer.

## Environnement

- OS: [ex: Ubuntu 22.04]
- Python: [ex: 3.12.1]
- Version Suddenly: [ex: 0.1.0]

## Logs

```
Coller les logs pertinents ici
```

## Screenshots

Si applicable.
```

---

## Ressources

- **Documentation** : `documentation/`
- **Architecture** : `documentation/ARCHITECTURE.md`
- **API ActivityPub** : `documentation/api/activitypub.md`
- **Modèles** : `documentation/models/README.md`

---

## Questions ?

- Ouvrez une issue avec le tag `question`
- Rejoignez les discussions sur le dépôt GitHub

Merci de contribuer à Suddenly !
