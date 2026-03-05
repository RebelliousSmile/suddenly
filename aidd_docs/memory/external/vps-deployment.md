# Déploiement sur VPS

Guide de déploiement de Suddenly sur un VPS (Debian/Ubuntu).

**Difficulté** : Intermédiaire
**Temps estimé** : 1-2 heures
**Coût** : 5-20€/mois selon le fournisseur

---

## Prérequis

- VPS avec Debian 12+ ou Ubuntu 22.04+
- Accès root ou sudo
- Domaine pointant vers l'IP du VPS
- Ports 80 et 443 ouverts

---

## Étape 1 : Préparation du Serveur

### 1.1 Mise à Jour

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Installation des Dépendances

```bash
sudo apt install -y \
    python3.12 python3.12-venv python3.12-dev \
    postgresql postgresql-contrib \
    nginx \
    git \
    certbot python3-certbot-nginx \
    build-essential \
    libpq-dev
```

### 1.3 Créer un Utilisateur

```bash
sudo useradd -m -s /bin/bash suddenly
sudo mkdir -p /opt/suddenly
sudo chown suddenly:suddenly /opt/suddenly
```

---

## Étape 2 : Base de Données

### 2.1 Configuration PostgreSQL

```bash
sudo -u postgres psql << 'EOF'
CREATE USER suddenly WITH PASSWORD 'motdepasse-securise';
CREATE DATABASE suddenly OWNER suddenly;
GRANT ALL PRIVILEGES ON DATABASE suddenly TO suddenly;
\q
EOF
```

### 2.2 Optimisation PostgreSQL (Optionnel)

Éditer `/etc/postgresql/16/main/postgresql.conf` :

```ini
# Ajuster selon la RAM disponible
shared_buffers = 256MB
effective_cache_size = 768MB
maintenance_work_mem = 64MB
work_mem = 16MB
```

```bash
sudo systemctl restart postgresql
```

---

## Étape 3 : Application

### 3.1 Cloner le Code

```bash
sudo -u suddenly bash << 'EOF'
cd /opt/suddenly
git clone https://github.com/votre-compte/suddenly.git app
cd app
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
EOF
```

### 3.2 Configuration

```bash
sudo -u suddenly bash << 'EOF'
cat > /opt/suddenly/app/.env << 'ENVEOF'
# Django
DEBUG=False
SECRET_KEY=votre-cle-secrete-longue
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com

# Base de données
DATABASE_URL=postgres://suddenly:motdepasse-securise@localhost:5432/suddenly

# Domaine
DOMAIN=votre-domaine.com

# Sécurité
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
ENVEOF
EOF
```

### 3.3 Initialisation

```bash
sudo -u suddenly bash << 'EOF'
cd /opt/suddenly/app
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
EOF
```

---

## Étape 4 : Gunicorn

### 4.1 Service Systemd

```bash
sudo cat > /etc/systemd/system/suddenly.service << 'EOF'
[Unit]
Description=Suddenly Gunicorn Daemon
After=network.target postgresql.service

[Service]
User=suddenly
Group=suddenly
WorkingDirectory=/opt/suddenly/app
Environment="PATH=/opt/suddenly/app/venv/bin"
EnvironmentFile=/opt/suddenly/app/.env
ExecStart=/opt/suddenly/app/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/opt/suddenly/suddenly.sock \
    --access-logfile /var/log/suddenly/access.log \
    --error-logfile /var/log/suddenly/error.log \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 4.2 Logs

```bash
sudo mkdir -p /var/log/suddenly
sudo chown suddenly:suddenly /var/log/suddenly
```

### 4.3 Démarrage

```bash
sudo systemctl daemon-reload
sudo systemctl enable suddenly
sudo systemctl start suddenly
sudo systemctl status suddenly
```

---

## Étape 5 : Nginx

### 5.1 Configuration

```bash
sudo cat > /etc/nginx/sites-available/suddenly << 'EOF'
upstream suddenly {
    server unix:/opt/suddenly/suddenly.sock fail_timeout=0;
}

server {
    listen 80;
    server_name votre-domaine.com www.votre-domaine.com;

    # Redirection HTTPS (ajoutée par Certbot)
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com www.votre-domaine.com;

    # SSL (sera configuré par Certbot)
    # ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;

    # Sécurité
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs
    access_log /var/log/nginx/suddenly_access.log;
    error_log /var/log/nginx/suddenly_error.log;

    # Taille max upload
    client_max_body_size 10M;

    # Fichiers statiques
    location /static/ {
        alias /opt/suddenly/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Fichiers médias
    location /media/ {
        alias /opt/suddenly/app/media/;
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

        # WebSocket support (si nécessaire)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF
```

### 5.2 Activation

```bash
sudo ln -s /etc/nginx/sites-available/suddenly /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Optionnel
sudo nginx -t
sudo systemctl reload nginx
```

---

## Étape 6 : SSL avec Let's Encrypt

```bash
sudo certbot --nginx -d votre-domaine.com -d www.votre-domaine.com
```

Certbot va :
1. Obtenir le certificat
2. Configurer Nginx automatiquement
3. Mettre en place le renouvellement automatique

---

## Étape 7 : Redis (Optionnel)

Pour le cache et les sessions.

### 7.1 Installation

```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 7.2 Configuration Django

Ajouter dans `.env` :

```bash
REDIS_URL=redis://localhost:6379/0
```

---

## Étape 8 : Celery (Optionnel)

Pour les tâches asynchrones (fédération).

### 8.1 Service Celery Worker

```bash
sudo cat > /etc/systemd/system/suddenly-celery.service << 'EOF'
[Unit]
Description=Suddenly Celery Worker
After=network.target redis.service

[Service]
User=suddenly
Group=suddenly
WorkingDirectory=/opt/suddenly/app
Environment="PATH=/opt/suddenly/app/venv/bin"
EnvironmentFile=/opt/suddenly/app/.env
ExecStart=/opt/suddenly/app/venv/bin/celery \
    -A config worker \
    --loglevel=info \
    --logfile=/var/log/suddenly/celery.log
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 8.2 Service Celery Beat (Tâches Planifiées)

```bash
sudo cat > /etc/systemd/system/suddenly-celery-beat.service << 'EOF'
[Unit]
Description=Suddenly Celery Beat
After=network.target redis.service

[Service]
User=suddenly
Group=suddenly
WorkingDirectory=/opt/suddenly/app
Environment="PATH=/opt/suddenly/app/venv/bin"
EnvironmentFile=/opt/suddenly/app/.env
ExecStart=/opt/suddenly/app/venv/bin/celery \
    -A config beat \
    --loglevel=info \
    --logfile=/var/log/suddenly/celery-beat.log
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 8.3 Démarrage

```bash
sudo systemctl daemon-reload
sudo systemctl enable suddenly-celery suddenly-celery-beat
sudo systemctl start suddenly-celery suddenly-celery-beat
```

---

## Étape 9 : Vérification

```bash
# Test HTTP
curl -I https://votre-domaine.com/

# Test Webfinger
curl "https://votre-domaine.com/.well-known/webfinger?resource=acct:admin@votre-domaine.com"

# Test NodeInfo
curl https://votre-domaine.com/.well-known/nodeinfo

# Logs
sudo journalctl -u suddenly -f
sudo tail -f /var/log/suddenly/error.log
```

---

## Mise à Jour

```bash
# Script de mise à jour
sudo -u suddenly bash << 'EOF'
cd /opt/suddenly/app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
EOF

sudo systemctl restart suddenly
sudo systemctl restart suddenly-celery suddenly-celery-beat  # Si Celery
```

---

## Maintenance

### Logs

```bash
# Application
sudo journalctl -u suddenly -f
sudo tail -f /var/log/suddenly/error.log

# Nginx
sudo tail -f /var/log/nginx/suddenly_error.log

# PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```

### Sauvegarde Base de Données

```bash
sudo -u postgres pg_dump suddenly > backup_$(date +%Y%m%d).sql
```

### Rotation des Logs

```bash
sudo cat > /etc/logrotate.d/suddenly << 'EOF'
/var/log/suddenly/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 suddenly suddenly
    sharedscripts
    postrotate
        systemctl reload suddenly > /dev/null 2>&1 || true
    endscript
}
EOF
```

---

## Dépannage

### Service ne démarre pas

```bash
sudo systemctl status suddenly
sudo journalctl -u suddenly -n 50
```

### Erreur 502 Bad Gateway

1. Vérifier que Gunicorn tourne : `sudo systemctl status suddenly`
2. Vérifier le socket : `ls -la /opt/suddenly/suddenly.sock`
3. Vérifier les permissions

### Erreur de base de données

```bash
sudo -u postgres psql -c "\l"  # Liste les bases
sudo -u suddenly psql -d suddenly -c "SELECT 1;"  # Test connexion
```

---

## Ressources

- [Documentation Gunicorn](https://docs.gunicorn.org/)
- [Documentation Nginx](https://nginx.org/en/docs/)
- [Documentation Certbot](https://certbot.eff.org/docs/)
