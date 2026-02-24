# Contribuer à Suddenly

Merci de votre intérêt pour Suddenly ! Ce document explique comment contribuer au projet.

## Code de conduite

Soyez respectueux et inclusif. Nous voulons que Suddenly soit un projet accueillant pour tous.

## Comment contribuer

### Signaler un bug

1. Vérifiez que le bug n'a pas déjà été signalé dans les [issues](https://github.com/votre-repo/suddenly/issues)
2. Créez une nouvelle issue avec :
   - Description claire du problème
   - Étapes pour reproduire
   - Comportement attendu vs observé
   - Version de Suddenly et environnement

### Proposer une fonctionnalité

1. Ouvrez une issue pour discuter de l'idée avant de coder
2. Expliquez le cas d'usage et les bénéfices
3. Attendez un retour des mainteneurs

### Soumettre du code

1. Forkez le repo
2. Créez une branche (`git checkout -b feature/ma-fonctionnalite`)
3. Codez et testez
4. Commitez (`git commit -m "feat: description"`)
5. Poussez (`git push origin feature/ma-fonctionnalite`)
6. Ouvrez une Pull Request

## Environnement de développement

```bash
# Cloner votre fork
git clone https://github.com/VOTRE-USERNAME/suddenly.git
cd suddenly

# Lancer en mode dev
docker compose -f docker-compose.dev.yml up

# Appliquer les migrations
docker compose -f docker-compose.dev.yml exec web python manage.py migrate

# Créer un compte admin
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

L'application tourne sur http://localhost:8000 avec hot-reload.

## Structure du projet

```
suddenly/
├── suddenly/           # Package Django principal
│   ├── core/          # App centrale (home, utils)
│   ├── users/         # Gestion des utilisateurs
│   ├── games/         # Parties et comptes-rendus
│   ├── characters/    # Personnages et liens
│   └── activitypub/   # Fédération AP
├── templates/         # Templates HTML
├── static/           # Fichiers statiques
├── scripts/          # Scripts utilitaires
├── docs/             # Documentation
└── nginx/            # Config Nginx
```

## Conventions

### Code Python

- Suivez PEP 8
- Utilisez des type hints
- Docstrings pour les fonctions publiques
- Tests pour les nouvelles fonctionnalités

```python
def create_character(name: str, game: Game) -> Character:
    """
    Create a new character in a game.
    
    Args:
        name: Character name
        game: Parent game
        
    Returns:
        The created Character instance
    """
    ...
```

### Commits

Utilisez [Conventional Commits](https://www.conventionalcommits.org/) :

- `feat:` nouvelle fonctionnalité
- `fix:` correction de bug
- `docs:` documentation
- `style:` formatage
- `refactor:` refactoring
- `test:` tests
- `chore:` maintenance

### Tests

```bash
# Lancer les tests
docker compose -f docker-compose.dev.yml exec web pytest

# Avec couverture
docker compose -f docker-compose.dev.yml exec web pytest --cov=suddenly
```

## Domaines de contribution

### Prioritaires

- [ ] Tests unitaires et d'intégration
- [ ] Documentation utilisateur
- [ ] Traductions
- [ ] Accessibilité (a11y)
- [ ] Tests de fédération avec d'autres logiciels AP

### Fonctionnalités v0.2+

- [ ] Interface de rédaction avec mentions
- [ ] Graphe des liens entre personnages
- [ ] Notifications en temps réel
- [ ] Import/export de données

## Questions ?

- Ouvrez une issue pour les questions techniques
- Rejoignez notre [serveur Discord/Matrix] (à venir)

Merci de contribuer à Suddenly ! 🎭
