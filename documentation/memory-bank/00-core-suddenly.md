# Suddenly - Core Memory Bank

## TL;DR (30 secondes)

**Suddenly** : Réseau fédéré de fiction partagée via ActivityPub
**Concept** : Les PNJ des uns deviennent les PJ des autres
**Stack** : Django + PostgreSQL (Redis/Celery optionnels)
**Déploiement** : PaaS, VPS, ou Docker (flexible)
**Instances** : `suddenly.social` (international) / `soudainement.fr` (FR)

---

## Pitch

Un réseau de comptes-rendus de parties JdR où les PNJ mentionnés deviennent des points d'ancrage que d'autres joueurs peuvent réclamer, adopter ou dériver.

**"Suddenly"** = ce moment où l'inattendu surgit, quand un personnage apparaît soudainement dans une autre histoire.

---

## Stack Technique

```
Requis      : Python 3.12+ / Django 5.x / PostgreSQL
Optionnel   : Redis (cache) / Celery (tasks async)
Frontend    : Django Templates + HTMX + Tailwind
Fédération  : ActivityPub (inspiré BookWyrm)
```

### Déploiement

| Mode | Prérequis | Usage |
|------|-----------|-------|
| **PaaS** | Python + PostgreSQL | Alwaysdata, Railway |
| **VPS** | + Nginx, Gunicorn | Debian, Ubuntu |
| **Docker** | Docker Compose | Optionnel |

---

## Architecture ActivityPub

### Acteurs (suivables, ont inbox/outbox)

| Entité | Type AP | Description |
|--------|---------|-------------|
| **User** | Person | Compte joueur |
| **Character** | Person | PJ ou PNJ |
| **Game** | Group | Partie/campagne |

### Objets (créés, partagés)

| Entité | Type AP | Description |
|--------|---------|-------------|
| **Report** | Article | Compte-rendu |
| **Quote** | Note | Citation |

### Liens (Offer spécifiques)

| Type | Description | Résultat |
|------|-------------|----------|
| **Claim** | "Ton PNJ = mon PJ" | Rétcon |
| **Adopt** | "Je reprends ton PNJ" | Transfert |
| **Fork** | "PJ inspiré" | Nouveau lié |

---

## Modèles Principaux

```
User ──1:N──> Game (owner)
User ──1:N──> Character (owner/creator)
Game ──1:N──> Report
Game ──1:N──> Character (origin)
Character ──N:M──> Report (via Appearance)
Character ──N:M──> Character (via Link)
Character ──1:N──> Quote
```

### Statuts Character

```
NPC → CLAIMED → (remplacé par PJ existant)
NPC → ADOPTED → PC (nouveau propriétaire)
NPC → FORKED  → (nouveau PJ lié créé)
```

---

## Documentation Clé

| Document | Contenu |
|----------|---------|
| `CLAUDE.md` | Instructions projet |
| `ARCHITECTURE.md` | Architecture technique |
| `api/activitypub.md` | Spec ActivityPub |
| `conception-jdr-activitypub.md` | Specs fonctionnelles |

---

## Commandes Rapides

```bash
# Dev local
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
createdb suddenly
python manage.py migrate
python manage.py runserver

# Tests
mypy apps/
pytest tests/contracts/
```

---

## Jalons MVP

1. **Fondations** : Django + User + Game + Report
2. **Personnages** : Character + Appearances + Quotes
3. **Liens** : Claim / Adopt / Fork workflow
4. **Fédération** : ActivityPub complet
