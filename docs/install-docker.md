# Installation avec Docker

Ce guide vous accompagne dans l'installation de Suddenly sur votre serveur.

## Prérequis

- Un serveur Linux (Ubuntu 22.04+ recommandé)
- Docker et Docker Compose installés
- Un nom de domaine pointant vers votre serveur
- Ports 80 et 443 ouverts

### Installation de Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Déconnectez-vous et reconnectez-vous
```

## Installation rapide

```bash
# Cloner le dépôt
git clone https://github.com/votre-repo/suddenly.git
cd suddenly

# Lancer l'installation
./scripts/install.sh
```

Le script vous demandera :
1. Votre nom de domaine
2. Une adresse email (pour les certificats SSL)

Il générera automatiquement les secrets et obtiendra les certificats Let's Encrypt.

## Installation manuelle

### 1. Configuration

```bash
# Copier le template
cp .env.example .env

# Éditer la configuration
nano .env
```

Variables à modifier :

```bash
DOMAIN=suddenly.example.com
SECRET_KEY=votre-cle-secrete-unique
POSTGRES_PASSWORD=mot-de-passe-fort
```

Générer une clé secrète :
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 2. Configuration Nginx

```bash
# Remplacer le domaine dans la config
export DOMAIN=suddenly.example.com
envsubst '${DOMAIN}' < nginx/conf.d/suddenly.conf.template > nginx/conf.d/suddenly.conf
```

### 3. Certificats SSL

```bash
# Créer une config nginx temporaire pour le challenge
cat > nginx/conf.d/temp.conf << 'EOF'
server {
    listen 80;
    server_name _;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 'OK'; }
}
EOF

# Démarrer nginx
docker compose up -d nginx

# Obtenir les certificats
docker run --rm \
    -v ./certs:/etc/letsencrypt \
    -v ./certbot-webroot:/var/www/certbot \
    certbot/certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    --email votre@email.com --agree-tos --no-eff-email \
    -d suddenly.example.com

# Supprimer la config temporaire
rm nginx/conf.d/temp.conf
docker compose down
```

### 4. Démarrage

```bash
# Télécharger les images
docker compose pull

# Démarrer les services
docker compose up -d

# Appliquer les migrations
docker compose exec web python manage.py migrate

# Créer un admin
docker compose exec web python manage.py createsuperuser
```

### 5. Vérification

- Accédez à `https://votre-domaine.com`
- Vérifiez `https://votre-domaine.com/.well-known/nodeinfo`
- Connectez-vous à l'admin : `https://votre-domaine.com/admin/`

## Commandes utiles

```bash
# Voir les logs
docker compose logs -f

# Logs d'un service spécifique
docker compose logs -f web

# Redémarrer
docker compose restart

# Arrêter
docker compose down

# Mise à jour
git pull
docker compose build
docker compose up -d
docker compose exec web python manage.py migrate

# Sauvegarde
./scripts/backup.sh

# Restauration
./scripts/restore.sh ./backups/suddenly_backup_20240101_120000
```

## Configuration avancée

### Email (SMTP)

Ajoutez à `.env` :

```bash
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=votre@email.com
EMAIL_HOST_PASSWORD=mot-de-passe
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=noreply@suddenly.example.com
```

### Monitoring (Sentry)

```bash
SENTRY_DSN=https://...@sentry.io/...
```

### Limite d'upload

```bash
MAX_UPLOAD_SIZE=10  # en Mo
```

## Dépannage

### Les certificats ne se renouvellent pas

```bash
# Vérifier le service certbot
docker compose logs certbot

# Renouveler manuellement
docker compose run --rm certbot renew
docker compose restart nginx
```

### La base de données est corrompue

```bash
# Restaurer depuis une sauvegarde
./scripts/restore.sh ./backups/suddenly_backup_XXXXXXXX_XXXXXX
```

### Problèmes de mémoire

Réduisez le nombre de workers Celery dans `docker-compose.yml` :

```yaml
celery:
  command: celery -A suddenly worker -l info -c 1  # au lieu de 2
```

## Ressources

- [Documentation Django](https://docs.djangoproject.com/)
- [ActivityPub Spec](https://www.w3.org/TR/activitypub/)
- [BookWyrm (inspiration)](https://github.com/bookwyrm-social/bookwyrm)
