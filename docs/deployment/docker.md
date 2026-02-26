# Déploiement avec Docker

Guide de déploiement de Suddenly avec Docker Compose.

**Difficulté** : Intermédiaire
**Temps estimé** : 30-45 minutes
**Prérequis** : Docker et Docker Compose installés

---

## Prérequis

- Docker 24+
- Docker Compose 2.x
- Domaine avec accès DNS
- Ports 80 et 443 disponibles

---

## Étape 1 : Structure des Fichiers

```
suddenly/
├── docker-compose.yml
├── docker-compose.override.yml  # Dev (optionnel)
├── .env
├── Dockerfile
└── nginx/
    └── suddenly.conf
```

---

## Étape 2 : Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dépendances système
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail
WORKDIR /app

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Code source
COPY . .

# Fichiers statiques
RUN python manage.py collectstatic --noinput

# Utilisateur non-root
RUN useradd -m suddenly && chown -R suddenly:suddenly /app
USER suddenly

# Port
EXPOSE 8000

# Commande
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
```

---

## Étape 3 : Docker Compose

### docker-compose.yml (Production)

```yaml
version: "3.8"

services:
  # Application Django
  web:
    build: .
    restart: unless-stopped
    env_file: .env
    environment:
      - DATABASE_URL=postgres://suddenly:${POSTGRES_PASSWORD}@db:5432/suddenly
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    networks:
      - suddenly_network

  # Base de données PostgreSQL
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_USER=suddenly
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=suddenly
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U suddenly"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - suddenly_network

  # Cache Redis
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - suddenly_network

  # Worker Celery
  celery:
    build: .
    restart: unless-stopped
    command: celery -A config worker --loglevel=info
    env_file: .env
    environment:
      - DATABASE_URL=postgres://suddenly:${POSTGRES_PASSWORD}@db:5432/suddenly
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    networks:
      - suddenly_network

  # Celery Beat (tâches planifiées)
  celery-beat:
    build: .
    restart: unless-stopped
    command: celery -A config beat --loglevel=info
    env_file: .env
    environment:
      - DATABASE_URL=postgres://suddenly:${POSTGRES_PASSWORD}@db:5432/suddenly
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    networks:
      - suddenly_network

  # Reverse proxy Nginx
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/suddenly.conf:/etc/nginx/conf.d/default.conf:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
      - certbot_www:/var/www/certbot:ro
      - certbot_conf:/etc/letsencrypt:ro
    depends_on:
      - web
    networks:
      - suddenly_network

  # Certbot pour SSL
  certbot:
    image: certbot/certbot
    volumes:
      - certbot_www:/var/www/certbot
      - certbot_conf:/etc/letsencrypt
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
  certbot_www:
  certbot_conf:

networks:
  suddenly_network:
    driver: bridge
```

---

## Étape 4 : Configuration Nginx

### nginx/suddenly.conf

```nginx
upstream suddenly {
    server web:8000;
}

server {
    listen 80;
    server_name votre-domaine.com www.votre-domaine.com;

    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirection HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com www.votre-domaine.com;

    # SSL
    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;

    # Sécurité SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # Sécurité headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # Taille upload
    client_max_body_size 10M;

    # Fichiers statiques
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Fichiers médias
    location /media/ {
        alias /app/media/;
        expires 7d;
    }

    # Application
    location / {
        proxy_pass http://suddenly;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

---

## Étape 5 : Variables d'Environnement

### .env

```bash
# Django
DEBUG=False
SECRET_KEY=votre-cle-secrete-tres-longue-et-aleatoire
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
DOMAIN=votre-domaine.com

# PostgreSQL
POSTGRES_PASSWORD=motdepasse-postgres-securise

# Sécurité
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
```

---

## Étape 6 : Déploiement

### 6.1 Premier Déploiement

```bash
# Cloner le dépôt
git clone https://github.com/votre-compte/suddenly.git
cd suddenly

# Créer .env
cp .env.example .env
# Éditer .env avec vos valeurs

# Construire les images
docker compose build

# Démarrer les services (sans SSL d'abord)
docker compose up -d db redis

# Attendre que la DB soit prête
sleep 10

# Appliquer les migrations
docker compose run --rm web python manage.py migrate

# Créer un superutilisateur
docker compose run --rm web python manage.py createsuperuser

# Démarrer tous les services
docker compose up -d
```

### 6.2 Obtenir le Certificat SSL

```bash
# Première obtention (mode staging pour test)
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email votre@email.com \
    --agree-tos \
    --no-eff-email \
    --staging \
    -d votre-domaine.com \
    -d www.votre-domaine.com

# Si OK, supprimer --staging et relancer
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email votre@email.com \
    --agree-tos \
    --no-eff-email \
    -d votre-domaine.com \
    -d www.votre-domaine.com

# Redémarrer Nginx
docker compose restart nginx
```

---

## Étape 7 : Vérification

```bash
# Statut des services
docker compose ps

# Logs
docker compose logs -f web
docker compose logs -f celery

# Test
curl -I https://votre-domaine.com/
curl "https://votre-domaine.com/.well-known/webfinger?resource=acct:admin@votre-domaine.com"
```

---

## Commandes Utiles

### Gestion des Services

```bash
# Démarrer
docker compose up -d

# Arrêter
docker compose down

# Redémarrer un service
docker compose restart web

# Voir les logs
docker compose logs -f [service]

# Shell dans un conteneur
docker compose exec web bash
```

### Maintenance

```bash
# Migrations
docker compose run --rm web python manage.py migrate

# Collectstatic
docker compose run --rm web python manage.py collectstatic --noinput

# Shell Django
docker compose run --rm web python manage.py shell

# Sauvegarde base de données
docker compose exec db pg_dump -U suddenly suddenly > backup.sql

# Restauration
cat backup.sql | docker compose exec -T db psql -U suddenly suddenly
```

### Mise à Jour

```bash
# Récupérer les mises à jour
git pull origin main

# Reconstruire
docker compose build

# Appliquer les migrations
docker compose run --rm web python manage.py migrate

# Redémarrer
docker compose up -d
```

---

## Docker Compose Override (Développement)

### docker-compose.override.yml

```yaml
version: "3.8"

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.dev
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True

  # Pas de Nginx en dev
  nginx:
    profiles:
      - production
```

---

## Dépannage

### Conteneur ne démarre pas

```bash
docker compose logs [service]
docker compose ps -a
```

### Erreur de connexion à la DB

```bash
# Vérifier que la DB est prête
docker compose exec db pg_isready -U suddenly

# Vérifier les variables d'environnement
docker compose exec web env | grep DATABASE
```

### Problème de permissions

```bash
# Vérifier les volumes
docker volume ls
docker volume inspect suddenly_static_volume
```

### Réinitialisation complète

```bash
docker compose down -v  # Supprime aussi les volumes !
docker compose build --no-cache
docker compose up -d
```

---

## Ressources

- [Documentation Docker Compose](https://docs.docker.com/compose/)
- [Docker + Django](https://docs.docker.com/samples/django/)
- [Certbot Docker](https://eff-certbot.readthedocs.io/en/stable/install.html#running-with-docker)
