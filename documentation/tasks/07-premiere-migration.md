# Tâche 07 : Première Migration

**Durée estimée** : 30 min
**Phase** : 1 - Fondations
**Statut** : [ ] À faire
**Dépend de** : 02, 03, 04, 05, 06

---

## Objectif

Exécuter les migrations, créer le superuser, et valider que tout fonctionne correctement avant de passer à la Phase 2.

## Prérequis

- Toutes les tâches 01-06 complétées
- PostgreSQL accessible (base `suddenly` créée)
- Environnement virtuel activé
- `.env` configuré

## Étapes

### 1. Vérifier la configuration

```bash
# Activer l'environnement
.venv\Scripts\activate  # Windows
# ou
source .venv/bin/activate  # Linux/Mac

# Vérifier les apps
python manage.py check
```

Si des erreurs apparaissent, les corriger avant de continuer.

### 2. Créer les migrations

```bash
# Créer les migrations pour toutes les apps
python manage.py makemigrations core
python manage.py makemigrations federation
python manage.py makemigrations users
python manage.py makemigrations games
```

**Structure attendue des migrations :**

```
apps/
├── core/
│   └── migrations/
│       └── __init__.py          # core est abstrait, pas de migration
├── federation/
│   └── migrations/
│       ├── __init__.py
│       └── 0001_initial.py      # FederatedServer, Follow
├── users/
│   └── migrations/
│       ├── __init__.py
│       └── 0001_initial.py      # User
└── games/
    └── migrations/
        ├── __init__.py
        └── 0001_initial.py      # Game, Report, ReportCast
```

### 3. Appliquer les migrations

```bash
# Appliquer dans l'ordre
python manage.py migrate

# Vérifier le statut
python manage.py showmigrations
```

**Tables créées :**

- `users_user` — Utilisateurs
- `federation_federatedserver` — Instances fédérées
- `federation_follow` — Abonnements
- `games_game` — Parties
- `games_report` — Comptes-rendus
- `games_reportcast` — Distribution

Plus les tables Django (auth, sessions, allauth, etc.)

### 4. Créer le superuser

```bash
python manage.py createsuperuser
```

Renseigner :
- Username: `admin`
- Email: `admin@localhost`
- Password: (au choix, pour dev local)

### 5. Lancer le serveur de développement

```bash
python manage.py runserver
```

### 6. Vérifications manuelles

Ouvrir dans le navigateur :

| URL | Attendu |
|-----|---------|
| `http://127.0.0.1:8000/` | Page d'accueil (peut être vide) |
| `http://127.0.0.1:8000/admin/` | Interface admin Django |
| `http://127.0.0.1:8000/accounts/login/` | Page de connexion allauth |
| `http://127.0.0.1:8000/accounts/signup/` | Page d'inscription allauth |

### 7. Tester l'admin

1. Se connecter à `/admin/` avec le superuser
2. Vérifier que les sections apparaissent :
   - **Utilisateurs** → Users
   - **Fédération** → Federated servers, Follows
   - **Parties** → Games, Reports
3. Créer un utilisateur de test
4. Créer une partie de test

### 8. Tester les vues

1. Se connecter avec l'utilisateur de test
2. Aller sur la page d'accueil → doit afficher la partie créée
3. Cliquer sur la partie → page de détail
4. Créer un nouveau compte-rendu

## Validation Finale Phase 1

### Checklist

- [ ] `python manage.py check` — Aucune erreur
- [ ] `python manage.py showmigrations` — Toutes les migrations appliquées
- [ ] Admin accessible et fonctionnel
- [ ] Authentification (login/signup) fonctionne
- [ ] Pages d'accueil, détail partie, profil accessibles
- [ ] Création de partie fonctionne
- [ ] Création de compte-rendu fonctionne
- [ ] Styles Tailwind appliqués
- [ ] HTMX chargé (vérifier console navigateur)

### Tests rapides dans le shell

```bash
python manage.py shell
```

```python
# Imports
from apps.users.models import User
from apps.games.models import Game, Report
from apps.federation.models import FederatedServer, Follow

# Vérifier les modèles
User.objects.count()
Game.objects.count()

# Créer un utilisateur
user = User.objects.create_user(
    username='test',
    email='test@example.com',
    password='testpass123'
)
print(user.get_display_name())

# Créer une partie
game = Game.objects.create(
    title='Ma première partie',
    owner=user,
    game_system='City of Mist'
)
print(game.get_absolute_url())

# Vérifier les champs AP (présents mais nullable)
print(f"AP ID: {game.ap_id}")  # None
print(f"Local: {game.local}")  # True
```

## Problèmes Courants

### Erreur de migration circulaire

Si erreur de dépendance circulaire entre `users` et `federation` :

```python
# Dans apps/users/models.py, changer temporairement :
federated_server = models.ForeignKey(
    'federation.FederatedServer',
    ...
)
# En :
federated_server = models.CharField(max_length=255, null=True, blank=True)
```

Migrer, puis rétablir la FK et refaire une migration.

### Erreur "No module named 'apps.characters'"

Le modèle `ReportCast` référence `characters.Character` qui n'existe pas encore.

Solution : commenter temporairement la FK `character` dans `ReportCast` :

```python
# character = models.ForeignKey(
#     'characters.Character',
#     ...
# )
```

Cette FK sera ajoutée en Phase 2.

### Table already exists

Si les tables existent déjà :

```bash
python manage.py migrate --fake
```

## Prochaines Étapes

Phase 1 terminée ! Vous avez :
- ✅ Configuration Django complète
- ✅ Modèles User, Game, Report fonctionnels
- ✅ Templates de base avec HTMX/Tailwind
- ✅ Authentification via allauth
- ✅ Admin configuré

Passez à la **Phase 2 : Personnages et Citations** :
- App `characters` avec Character, CharacterOwnership
- App `quotes` avec Quote, SharedSequence
- Templates personnages
- Système de citations

## Références

- `documentation/memory-bank/01-project-phases.md` — Vue d'ensemble des phases
- `documentation/models/README.md` — Spécifications complètes des modèles
