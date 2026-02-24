# Suddenly — Architecture Technique

**Version** : 1.1.0
**Objectif** : Déploiement flexible (PaaS, VPS, Docker)
**Inspiré de** : [BookWyrm](https://github.com/bookwyrm-social/bookwyrm) (ActivityPub uniquement)

---

## Principe : Architecture PaaS-Friendly

Suddenly est une **application Django standard** déployable partout où Python + PostgreSQL sont disponibles. Docker est **une option**, pas une obligation.

```
┌─────────────────────────────────────────────────────────────────┐
│                     MODES DE DÉPLOIEMENT                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   PaaS Simple   │  │   VPS Manuel    │  │     Docker      │ │
│  │  (Alwaysdata,   │  │  (Debian, etc.) │  │   (Optionnel)   │ │
│  │   Railway...)   │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│          │                    │                    │           │
│          ▼                    ▼                    ▼           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Django + PostgreSQL (requis)               │   │
│  │              Redis + Celery (optionnel)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Dépendances

| Composant | Requis | Optionnel | Fallback sans |
|-----------|--------|-----------|---------------|
| **Python 3.12+** | ✅ | - | - |
| **PostgreSQL** | ✅ | - | - |
| **Redis** | - | ✅ | Cache DB Django |
| **Celery** | - | ✅ | Tâches synchrones |

**Petite instance (< 50 users)** : Django + PostgreSQL suffit
**Instance moyenne (50-500)** : + Redis recommandé
**Grande instance (500+)** : + Celery pour la fédération

---

## Stack Technique

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| **Framework** | Django 5.x | Standard, déployable partout |
| **Python** | 3.12+ | Supporté par tous les PaaS |
| **Database** | PostgreSQL | Requis (FTS, JSON, robustesse) |
| **Cache** | Redis ou DB | Redis si dispo, sinon cache DB |
| **Tasks** | Celery ou sync | Celery si Redis, sinon synchrone |
| **Templates** | Django + HTMX | Pas de build frontend |
| **CSS** | Tailwind (CDN ou build) | CDN pour simplifier |
| **ActivityPub** | Custom | Inspiré BookWyrm |

---

## Pourquoi Python/Django ?

| Critère | Python/Django | Go/Rust |
|---------|---------------|---------|
| **Contributions** | Facile, langage accessible | Barrière à l'entrée |
| **Écosystème AP** | BookWyrm comme référence | Peu de libs matures |
| **Temps de dev** | Rapide, batteries included | Plus long |
| **Maintenance** | Large communauté | Expertise requise |
| **Merge requests** | Code lisible, modifiable | Binaires = friction |

**Conclusion** : Django maximise les contributions de la communauté.

---

## Structure du Projet

```
suddenly/
├── config/                 # Configuration Django
│   ├── settings/
│   │   ├── base.py        # Settings communs
│   │   ├── development.py # Dev local
│   │   └── production.py  # Production
│   ├── urls.py
│   └── wsgi.py
│
├── apps/                   # Applications Django
│   ├── users/             # Authentification, profils
│   │   ├── models.py
│   │   ├── views.py
│   │   └── activitypub.py # Serialisation AP User
│   │
│   ├── games/             # Parties et comptes-rendus
│   │   ├── models.py      # Game, Report, ReportCast
│   │   ├── views.py
│   │   └── activitypub.py
│   │
│   ├── characters/        # Personnages et liens
│   │   ├── models.py      # Character, CharacterLink, etc.
│   │   ├── services.py    # Logique Claim/Adopt/Fork
│   │   └── activitypub.py
│   │
│   ├── quotes/            # Citations
│   │   ├── models.py
│   │   └── views.py
│   │
│   └── federation/        # Core ActivityPub
│       ├── actors.py      # Base classes acteurs AP
│       ├── activities.py  # Create, Follow, Offer, etc.
│       ├── handlers.py    # Inbox handlers
│       ├── signatures.py  # HTTP Signatures
│       └── tasks.py       # Tâches async (delivery)
│
├── core/                   # Utilitaires partagés
│   ├── mixins.py          # ActivityPubMixin, etc.
│   └── utils.py
│
├── templates/              # Templates Django + HTMX
│   ├── base.html
│   ├── components/        # Composants réutilisables
│   └── [app]/             # Templates par app
│
├── static/                 # Assets statiques
│   ├── css/
│   └── js/                # Minimal JS (HTMX principalement)
│
├── docker/                 # Configurations Docker
│   ├── Dockerfile         # Image Django
│   └── nginx/             # Config Nginx
│
├── scripts/                # Scripts utilitaires
│   └── setup.sh           # Premier setup
│
├── manage.py
├── requirements.txt        # Dépendances Python
├── docker-compose.yml      # Stack complète
├── .env.example           # Variables d'environnement
└── suddenly.toml          # Configuration instance
```

---

## Configuration Instance

Un fichier unique `suddenly.toml` pour configurer l'instance :

```toml
# suddenly.toml - Configuration de l'instance

[instance]
name = "Mon Instance Suddenly"
domain = "suddenly.example.com"
description = "Une instance pour notre communauté JdR"
admin_email = "admin@example.com"

[database]
# PostgreSQL requis
host = "localhost"
port = 5432
name = "suddenly"
user = "suddenly"
# password via variable d'environnement SUDDENLY_DB_PASSWORD

[federation]
# Activer/désactiver la fédération
enabled = true
# Instances bloquées
blocked_instances = []
# Instances autorisées uniquement (vide = toutes)
allowed_instances = []

[features]
# Inscription ouverte ou sur invitation
open_registration = true
# Approbation manuelle des inscriptions
require_approval = false
# Nombre max de parties par utilisateur (0 = illimité)
max_games_per_user = 0

[media]
# Stockage des médias
backend = "local"  # ou "s3"
max_upload_size_mb = 10
# Pour S3 (mode production)
# s3_bucket = ""
# s3_region = ""
```

---

## Installation

### Option 1 : PaaS (Alwaysdata, Railway, Heroku...)

**Prérequis** : Compte sur le PaaS avec Python + PostgreSQL

```bash
# 1. Cloner le projet
git clone https://github.com/suddenly-social/suddenly.git
cd suddenly

# 2. Configurer les variables d'environnement sur le PaaS
# DATABASE_URL=postgres://user:pass@host:5432/suddenly
# SECRET_KEY=votre-secret-genere
# DOMAIN=suddenly.example.com
# DEBUG=false

# 3. Déployer (exemple Alwaysdata)
# - Créer un site Python/Django
# - Pointer vers le repo Git
# - Configurer les variables d'environnement
# - Lancer les migrations

python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
```

**Exemple Alwaysdata** :
```
Site → Python → Django
Version Python : 3.12
Chemin : /www/suddenly
Commande WSGI : config.wsgi:application
Variables : DATABASE_URL, SECRET_KEY, DOMAIN
```

### Option 2 : VPS Manuel (Debian/Ubuntu)

```bash
# 1. Installer les dépendances
sudo apt update
sudo apt install python3.12 python3.12-venv postgresql nginx

# 2. Créer la base de données
sudo -u postgres createuser suddenly
sudo -u postgres createdb suddenly -O suddenly

# 3. Cloner et configurer
git clone https://github.com/suddenly-social/suddenly.git
cd suddenly
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Variables d'environnement
cp .env.example .env
# Éditer .env

# 5. Initialiser
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic

# 6. Configurer Gunicorn + Nginx (voir docs/deployment/)
```

### Option 3 : Docker (optionnel)

```bash
# Pour ceux qui préfèrent Docker
git clone https://github.com/suddenly-social/suddenly.git
cd suddenly
cp .env.example .env
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### Configuration (.env)

```bash
# .env - Variables d'environnement

# === REQUIS ===
SECRET_KEY=votre-secret-key-genere-64-chars
DOMAIN=suddenly.example.com
DATABASE_URL=postgres://user:pass@localhost:5432/suddenly

# === OPTIONNEL ===
DEBUG=false

# Redis (si disponible, améliore les perfs)
REDIS_URL=redis://localhost:6379/0

# Celery (si Redis disponible)
CELERY_ENABLED=false  # true si Redis dispo

# Email
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USER=noreply@example.com
EMAIL_PASSWORD=password

# Fédération
FEDERATION_ENABLED=true
```

### Développement Local

```bash
# 1. Cloner
git clone https://github.com/suddenly-social/suddenly.git
cd suddenly

# 2. Environnement Python
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

pip install -r requirements.txt
pip install -r requirements-dev.txt  # Tests, linters

# 3. PostgreSQL local
# Option A: PostgreSQL installé localement
createdb suddenly

# Option B: PostgreSQL via Docker (juste la DB)
docker run -d --name suddenly-db \
  -e POSTGRES_DB=suddenly \
  -e POSTGRES_PASSWORD=dev \
  -p 5432:5432 \
  postgres:16-alpine

# 4. Configuration
cp .env.example .env
# Éditer: DATABASE_URL=postgres://postgres:dev@localhost:5432/suddenly
# Éditer: DEBUG=true

# 5. Lancer
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## ActivityPub : Stratégie Simplifiée

### Acteurs Minimaux (MVP)

Pour simplifier, on commence avec **2 types d'acteurs** au lieu de 4 :

| Acteur | Type AP | Contenu |
|--------|---------|---------|
| **User** | `Person` | Profil, games, characters |
| **Character** | `Person` | Fiche, apparitions, quotes |

Les **Games** et **Reports** sont des **objets** (pas des acteurs) :
- `Game` → `Collection` (liste de reports)
- `Report` → `Article` (compte-rendu)
- `Quote` → `Note` (citation)

### Activités MVP

```
Phase 1 (v0.4):
- Follow/Accept/Reject (users, characters)
- Create/Update/Delete (reports, quotes)

Phase 2 (v0.5):
- Offer/Accept/Reject (claim, adopt, fork)
- Announce (partage de reports)
```

### Compatibilité Mastodon

Les reports sont convertis en `Article` avec :
- Titre du report
- Extrait du contenu
- Lien vers le report complet
- Image de couverture si disponible

---

## Frontend : HTMX + Alpine.js

**Pourquoi pas de SPA (React/Vue)** :
- Complexité accrue pour les contributeurs
- Build step supplémentaire
- SSR nécessaire pour SEO
- Surcharge pour le use case

**Stack frontend** :

```html
<!-- Base template -->
<script src="htmx.min.js"></script>      <!-- 14KB gzip -->
<script src="alpine.min.js"></script>    <!-- 8KB gzip -->
<link href="tailwind.css">               <!-- Purgé, ~10KB -->

<!-- Total: ~32KB (vs 100KB+ pour React) -->
```

**Exemple d'interaction** :

```html
<!-- Liste de personnages avec chargement dynamique -->
<div id="characters-list">
  {% for character in characters %}
    <div class="character-card">
      <h3>{{ character.name }}</h3>
      <button
        hx-post="/characters/{{ character.id }}/claim/"
        hx-target="#claim-modal"
        hx-swap="innerHTML"
      >
        Réclamer ce PNJ
      </button>
    </div>
  {% endfor %}
</div>

<!-- Pagination infinie -->
<div
  hx-get="/characters/?page={{ next_page }}"
  hx-trigger="revealed"
  hx-swap="afterend"
>
  Charger plus...
</div>
```

---

## Sécurité

### HTTP Signatures (ActivityPub)

```python
# apps/federation/signatures.py
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

def sign_request(request, actor):
    """Signe une requête HTTP pour ActivityPub."""
    headers_to_sign = ['(request-target)', 'host', 'date', 'digest']
    signature_string = build_signature_string(request, headers_to_sign)

    signature = actor.private_key.sign(
        signature_string.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    return build_signature_header(actor, headers_to_sign, signature)
```

### Rate Limiting

```python
# Mode simple: Django middleware
# Mode production: Redis + django-ratelimit

RATELIMIT_ENABLE = True
RATELIMIT_RATES = {
    'inbox': '100/h',      # Activités AP entrantes
    'api': '1000/h',       # API générale
    'auth': '10/m',        # Tentatives de connexion
}
```

---

## Métriques de Succès

| Métrique | Cible |
|----------|-------|
| Installation Docker | < 5 minutes |
| RAM minimum | 1GB |
| Temps réponse pages | < 200ms |
| Temps réponse API | < 100ms |
| Temps delivery AP | < 5s (async) |
| Contribution (PR) | Review < 48h |

---

## Roadmap Technique

### v0.1 - Fondations
- [ ] Structure projet Django + Docker
- [ ] Modèles User, Game, Report
- [ ] Authentification (django-allauth)
- [ ] Templates de base HTMX
- [ ] CI/CD GitHub Actions

### v0.2 - Personnages
- [ ] Modèles Character, CharacterAppearance
- [ ] Interface création PNJ dans reports
- [ ] Listing et recherche personnages (PostgreSQL FTS)

### v0.3 - Liens
- [ ] Modèles LinkRequest, CharacterLink
- [ ] Workflow Claim/Adopt/Fork
- [ ] Notifications (in-app + email)

### v0.4 - Fédération
- [ ] ActivityPub User/Character
- [ ] HTTP Signatures (inspiré BookWyrm)
- [ ] Inbox/Outbox handlers
- [ ] Compatibilité Mastodon

### v0.5 - Polish
- [ ] Quotes (citations)
- [ ] Recherche avancée
- [ ] Thèmes UI
- [ ] Documentation contributeurs

---

## Ce qu'on Réutilise de BookWyrm

### Gain Réel : Le Code ActivityPub

| Élément | Gain | Complexité à refaire |
|---------|------|----------------------|
| **HTTP Signatures** | 1-2 semaines | Élevée (crypto) |
| **Sérialisation JSON-LD** | 1 semaine | Moyenne |
| **Inbox handlers** | 1 semaine | Moyenne |
| **Webfinger** | 2-3 jours | Faible |
| **NodeInfo** | 1 jour | Faible |

**Total économisé** : ~4 semaines de dev ActivityPub

### Ce qu'on NE copie PAS

| Élément BookWyrm | Pourquoi on ne copie pas |
|------------------|--------------------------|
| Structure projet | Django standard suffit |
| Docker-first | On veut PaaS-friendly |
| Celery obligatoire | On veut optionnel |
| Modèles (Book, etc.) | Domaine différent |
| Frontend Bulma | On préfère HTMX + Tailwind |

### Comparaison Architectures

| Aspect | BookWyrm | Suddenly |
|--------|----------|----------|
| **Déploiement** | Docker requis | PaaS / VPS / Docker |
| **Redis** | Requis | Optionnel |
| **Celery** | Requis | Optionnel (fallback sync) |
| **Complexité install** | Moyenne | Faible |
| **Hébergeurs** | VPS uniquement | PaaS + VPS + Docker |

### Fichiers BookWyrm à Étudier/Adapter

```
bookwyrm/
├── activitypub/           # ← RÉUTILISER (adapter)
│   ├── base_activity.py   # Classes de base
│   ├── verbs.py           # Create, Follow, etc.
│   └── response.py        # Réponses AP
├── signatures.py          # ← RÉUTILISER (HTTP Signatures)
├── models/
│   └── base_model.py      # ← ÉTUDIER (ActivitypubMixin)
└── views/
    ├── inbox.py           # ← ADAPTER (handlers)
    └── outbox.py          # ← ADAPTER
```
