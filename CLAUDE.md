# Suddenly — Instructions Projet

## Description

Réseau fédéré de fiction partagée où les PNJ des uns peuvent devenir les PJ des autres. Les joueurs publient des comptes-rendus de parties et les personnages mentionnés peuvent être réclamés, adoptés ou dérivés par d'autres joueurs via ActivityPub.

**Instances prévues** :
- `suddenly.social` — Instance internationale (principale)
- `soudainement.fr` — Instance française

---

## Stack Technique

| Composant | Technologie | Notes |
|-----------|-------------|-------|
| **Backend** | Django 5.x | Python 3.12+ |
| **Database** | PostgreSQL | Requis (FTS, JSON) |
| **Cache** | Redis | Optionnel (fallback DB cache) |
| **Tasks** | Celery | Optionnel (fallback sync) |
| **Frontend** | Django + HTMX + Tailwind | SSR, pas de build JS |
| **Fédération** | ActivityPub | Inspiré BookWyrm |

### Déploiement Flexible

```
PaaS (Alwaysdata, Railway)  →  Django + PostgreSQL
VPS (Debian, Ubuntu)        →  + Nginx + Gunicorn
Docker (optionnel)          →  docker-compose
```

**Pas de Docker obligatoire** — L'app doit tourner partout où Python + PostgreSQL sont disponibles.

---

## Architecture

### Acteurs ActivityPub

| Entité | Type AP | Suivable | Description |
|--------|---------|----------|-------------|
| **User** | Person | Oui | Compte joueur |
| **Character** | Person | Oui | PJ ou PNJ |

### Objets ActivityPub

| Entité | Type AP | Description |
|--------|---------|-------------|
| **Game** | Collection | Partie/campagne |
| **Report** | Article | Compte-rendu |
| **Quote** | Note | Citation |

### Types de Liens (Offer)

| Type | Description | Résultat |
|------|-------------|----------|
| **Claim** | "Ton PNJ = mon PJ depuis le début" | Rétcon, PNJ remplacé |
| **Adopt** | "Je reprends ton PNJ" | PNJ → mon PJ |
| **Fork** | "PJ inspiré de ton PNJ" | Nouveau PJ lié |

---

## Conventions de Code

### Python/Django

- PEP 8 + type hints obligatoires
- Modèles avec UUID comme clé primaire
- `select_related`/`prefetch_related` systématiques
- Services pour logique métier complexe

### Nommage

| Élément | Convention | Exemple |
|---------|------------|---------|
| Fichiers | snake_case | `character_service.py` |
| Classes | PascalCase | `CharacterService` |
| Fonctions | snake_case | `get_user_characters()` |
| Constants | SCREAMING_SNAKE | `MAX_THEME_CARDS` |

### Commits

```
type(scope): description

Types: feat, fix, refactor, docs, test, chore
Scopes: users, games, characters, quotes, activitypub, api
```

---

## Documentation

### Architecture & Specs

| Document | Contenu |
|----------|---------|
| `documentation/ARCHITECTURE.md` | Architecture technique complète |
| `documentation/conception-jdr-activitypub.md` | Spécification fonctionnelle |
| `documentation/api/activitypub.md` | Spec ActivityPub Suddenly |

### Références

| Document | Contenu |
|----------|---------|
| `documentation/sources/bookwyrm-architecture.md` | Référence BookWyrm |

### Memory Bank (contexte rapide)

| Fichier | Usage | Charger |
|---------|-------|---------|
| `memory-bank/00-core-suddenly.md` | Vue d'ensemble | TOUJOURS |
| `memory-bank/02-development-standards.md` | Standards dev | Si coding |
| `memory-bank/03-task-workflow.md` | Workflow tâches | Si planification |

---

## Structure Projet (cible)

```
suddenly/
├── config/              # Settings Django
├── apps/
│   ├── users/          # Auth, profils
│   ├── games/          # Parties, reports
│   ├── characters/     # Personnages, liens
│   ├── quotes/         # Citations
│   └── federation/     # ActivityPub core
├── core/               # Utilitaires partagés
├── templates/          # Django + HTMX
├── static/             # CSS (Tailwind), JS minimal
└── tests/
    ├── contracts/      # Tests logique métier
    └── e2e/            # Tests critiques
```

---

## Commandes Dev

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Database
createdb suddenly
python manage.py migrate

# Dev
python manage.py runserver

# Tests
mypy apps/
pytest tests/contracts/
```

---

## Jalons

### Phase 1 : Fondations
- [ ] Structure Django + config
- [ ] Modèles User, Game, Report
- [ ] Templates HTMX de base
- [ ] Auth (django-allauth)

### Phase 2 : Personnages
- [ ] Modèles Character, Appearance
- [ ] Interface création PNJ
- [ ] Recherche (PostgreSQL FTS)

### Phase 3 : Liens
- [ ] LinkRequest, CharacterLink
- [ ] Workflow Claim/Adopt/Fork
- [ ] Notifications

### Phase 4 : Fédération
- [ ] ActivityPub (User, Character)
- [ ] HTTP Signatures
- [ ] Inbox/Outbox
- [ ] Compatibilité Mastodon

---

## Agents Claude Code

| Agent | Usage |
|-------|-------|
| `claude-code-optimizer` | Audit config Claude Code |
| `documentation-architect` | Gestion documentation |
| `technical-architect` | Décisions architecture |
| `activitypub-expert` | Fédération, signatures HTTP, Mastodon |
| `django-developer` | Modèles, vues, templates HTMX |
