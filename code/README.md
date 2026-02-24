# 🎭 Suddenly

**Réseau fédéré de fiction partagée**

Un réseau de comptes-rendus de parties où les PNJ des uns peuvent devenir les PJ des autres.

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## ✨ Concept

Les joueurs publient leurs comptes-rendus de partie. Les PNJ mentionnés deviennent des points d'ancrage que d'autres joueurs peuvent **réclamer**, **adopter** ou **dériver** pour tisser des liens entre fictions indépendantes.

Le nom "Suddenly" évoque ce moment où l'inattendu surgit — quand un personnage apparaît *soudainement* dans une autre histoire.

## 🚀 Installation

### Option rapide (Docker)

```bash
git clone https://github.com/votre-repo/suddenly.git
cd suddenly
./scripts/install.sh
```

Le script vous guidera pour configurer votre domaine et obtenir les certificats SSL.

### Option développement

```bash
# Cloner le repo
git clone https://github.com/votre-repo/suddenly.git
cd suddenly

# Lancer l'environnement de dev
docker compose -f docker-compose.dev.yml up

# Dans un autre terminal, appliquer les migrations
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser

# Accéder à http://localhost:8000
```

### Option PaaS

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## 📋 Prérequis

- Docker et Docker Compose
- Un domaine pointant vers votre serveur
- Ports 80 et 443 ouverts

## 🔧 Configuration

Copiez `.env.example` vers `.env` et modifiez les valeurs :

```bash
cp .env.example .env
```

Variables essentielles :

| Variable | Description |
|----------|-------------|
| `DOMAIN` | Domaine de votre instance |
| `SECRET_KEY` | Clé secrète Django (générée automatiquement) |
| `POSTGRES_PASSWORD` | Mot de passe de la base de données |

## 🔗 Types de liens entre personnages

### Claim (rétcon)
> "Ton PNJ c'était mon PJ depuis le début."

### Adopt (reprise)
> "Ton PNJ m'intéresse, j'en fais mon PJ à partir de maintenant."

### Fork (dérivation)
> "Je crée un PJ inspiré de ton PNJ, mais distinct."

## 🌐 Fédération

Suddenly utilise ActivityPub pour se fédérer avec d'autres instances Suddenly et le reste du Fediverse (Mastodon, BookWyrm...).

Chaque entité est un acteur ActivityPub :
- **Joueurs** — publient des parties
- **Parties** — regroupent des comptes-rendus
- **Personnages** — peuvent être suivis et liés

## 📚 Documentation

- [Guide d'installation](docs/install-docker.md)
- [Configuration avancée](docs/configuration.md)
- [API ActivityPub](docs/activitypub.md)
- [Contribution](CONTRIBUTING.md)

## 🛠 Stack technique

- **Backend** : Python / Django 5
- **Base de données** : PostgreSQL 16
- **Cache / Queue** : Redis 7
- **Tâches async** : Celery
- **Fédération** : ActivityPub
- **Reverse proxy** : Nginx

## 📜 Licence

AGPL-3.0 — Voir [LICENSE](LICENSE)

## 🙏 Inspirations

- [BookWyrm](https://github.com/bookwyrm-social/bookwyrm) — Réseau social fédéré pour les livres
- [Mastodon](https://github.com/mastodon/mastodon) — Réseau social fédéré
- L'écosystème du jeu de rôle solo

---

*Suddenly* — Quand les histoires se croisent. 🎭
