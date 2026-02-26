# Codebase Structure — Suddenly

## Structure cible

```
suddenly/
├── config/                     # Configuration Django
│   ├── settings/
│   │   ├── base.py             # Settings communs
│   │   ├── development.py      # Dev local
│   │   └── production.py       # Production
│   ├── urls.py
│   └── wsgi.py
│
├── apps/                       # Applications Django
│   ├── users/                  # Auth, profils utilisateurs
│   │   ├── models.py           # User (AbstractUser + ActivityPubMixin)
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── activitypub.py      # Sérialisation AP User
│   │   └── admin.py
│   │
│   ├── games/                  # Parties et comptes-rendus
│   │   ├── models.py           # Game, Report, ReportCast
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── activitypub.py
│   │
│   ├── characters/             # Personnages et liens
│   │   ├── models.py           # Character, CharacterLink, LinkRequest, SharedSequence
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py         # Logique Claim/Adopt/Fork ← CRITIQUE
│   │   └── activitypub.py
│   │
│   ├── quotes/                 # Citations
│   │   ├── models.py           # Quote
│   │   ├── views.py
│   │   └── urls.py
│   │
│   └── federation/             # Core ActivityPub
│       ├── models.py           # FederatedServer, Follow
│       ├── actors.py           # Classes de base acteurs AP
│       ├── activities.py       # Create, Follow, Offer, etc.
│       ├── handlers.py         # Inbox handlers ← CRITIQUE
│       ├── signatures.py       # HTTP Signatures ← CRITIQUE
│       ├── tasks.py            # Tâches async (delivery)
│       ├── webfinger.py        # Webfinger endpoint
│       └── nodeinfo.py         # NodeInfo endpoint
│
├── core/                       # Utilitaires partagés
│   ├── models.py               # BaseModel, ActivityPubMixin
│   ├── mixins.py
│   └── utils.py
│
├── templates/                  # Templates Django + HTMX
│   ├── base.html
│   ├── components/             # Composants HTMX réutilisables
│   └── [app]/                  # Templates par app
│
├── static/
│   ├── css/                    # Tailwind CSS (build ou CDN)
│   └── js/                     # Minimal JS
│
├── tests/
│   ├── contracts/              # Tests logique métier (20%)
│   │   ├── test_claim.py
│   │   ├── test_adopt.py
│   │   ├── test_fork.py
│   │   └── test_activitypub.py
│   └── e2e/                    # Tests critiques (10%)
│
├── docs/                       # Documentation
├── scripts/                    # Scripts utilitaires
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── docker-compose.yml
├── .env.example
└── CLAUDE.md
```

## Modules critiques

| Fichier | Rôle | Tests obligatoires |
|---------|------|--------------------|
| `apps/characters/services.py` | Logique Claim/Adopt/Fork | Oui |
| `apps/federation/handlers.py` | Réception activités AP | Oui |
| `apps/federation/signatures.py` | HTTP Signatures | Oui |
| `apps/federation/activities.py` | Sérialisation AP | Oui |
| `apps/users/activitypub.py` | Fédération utilisateurs | Oui |
| `core/models.py` | BaseModel, ActivityPubMixin | Oui |

## Conventions de nommage

| Élément | Convention | Exemple |
|---------|------------|---------|
| Fichiers | `snake_case` | `character_service.py` |
| Classes | `PascalCase` | `CharacterService` |
| Fonctions | `snake_case` | `get_user_characters()` |
| Constants | `SCREAMING_SNAKE` | `MAX_THEME_CARDS` |
| Apps Django | `snake_case`, singulier | `users`, `games`, `characters` |
| Tables DB | `app_model` (auto) | `users_user`, `games_game` |

## Relations entre apps

```
core/           ← importé par tout le monde (BaseModel, ActivityPubMixin)
users/          ← importé par games, characters, quotes, federation
games/          ← importé par characters
characters/     ← importé par quotes
federation/     ← importe users, games, characters (pour sérialisation)
```

**Règle** : Pas d'import circulaire. `core/` ne dépend de rien.
