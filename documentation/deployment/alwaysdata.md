# Déploiement sur Alwaysdata

Guide de déploiement de Suddenly sur [Alwaysdata](https://www.alwaysdata.com/).

**Difficulté** : Facile
**Temps estimé** : 30 minutes
**Coût** : À partir de 10€/mois (Pack 100Mo gratuit pour tests)

---

## Prérequis

- Compte Alwaysdata (gratuit pour commencer)
- Domaine configuré (ou sous-domaine Alwaysdata)
- Git installé localement

---

## Étape 1 : Configuration du Compte

### 1.1 Créer une Base PostgreSQL

1. Aller dans **Bases de données** > **PostgreSQL**
2. Cliquer sur **Ajouter une base de données**
3. Configurer :
   - Nom : `suddenly`
   - Utilisateur : créer ou utiliser existant
4. Noter les informations de connexion

### 1.2 Configurer Python

1. Aller dans **Environnement** > **Python**
2. Vérifier que Python 3.12+ est disponible
3. Si non, contacter le support ou upgrader le pack

---

## Étape 2 : Déploiement du Code

### 2.1 Connexion SSH

```bash
ssh compte@ssh-compte.alwaysdata.net
```

### 2.2 Cloner le Dépôt

```bash
cd ~/www/
git clone https://github.com/votre-compte/suddenly.git
cd suddenly
```

### 2.3 Environnement Virtuel

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.4 Configuration

Créer le fichier `.env` :

```bash
cat > .env << 'EOF'
# Django
DEBUG=False
SECRET_KEY=votre-cle-secrete-generee
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com

# Base de données (format Alwaysdata)
DATABASE_URL=postgres://compte_user:motdepasse@postgresql-compte.alwaysdata.net:5432/compte_suddenly

# Domaine
DOMAIN=votre-domaine.com

# Sécurité
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email (optionnel, SMTP Alwaysdata)
EMAIL_URL=smtp://compte@alwaysdata.net:motdepasse@smtp-compte.alwaysdata.net:587
EOF
```

### 2.5 Initialisation

```bash
source venv/bin/activate

# Migrations
python manage.py migrate

# Fichiers statiques
python manage.py collectstatic --noinput

# Créer un superutilisateur
python manage.py createsuperuser
```

---

## Étape 3 : Configuration du Site

### 3.1 Créer le Site Web

1. Aller dans **Web** > **Sites**
2. Cliquer sur **Ajouter un site**
3. Configurer :

| Champ | Valeur |
|-------|--------|
| Nom | suddenly |
| Adresses | votre-domaine.com, www.votre-domaine.com |
| Type | Python WSGI |
| Chemin de l'application | /www/suddenly/ |
| Fichier WSGI | config/wsgi.py |
| Répertoire de travail | /www/suddenly/ |
| Virtualenv | /www/suddenly/venv/ |
| Version Python | 3.12 |

### 3.2 Variables d'Environnement

Dans la configuration du site, section **Environnement** :

```
DJANGO_SETTINGS_MODULE=config.settings.production
```

### 3.3 Fichiers Statiques

Ajouter un site statique :

1. **Web** > **Sites** > **Ajouter**
2. Type : **Fichiers statiques**
3. Adresses : `votre-domaine.com/static/`
4. Répertoire : `/www/suddenly/staticfiles/`

Même chose pour les médias :

1. Adresses : `votre-domaine.com/media/`
2. Répertoire : `/www/suddenly/media/`

---

## Étape 4 : SSL/HTTPS

### 4.1 Certificat Let's Encrypt

1. Aller dans **Web** > **Certificats SSL**
2. Cliquer sur **Ajouter un certificat**
3. Sélectionner **Let's Encrypt**
4. Choisir votre domaine
5. Valider

### 4.2 Forcer HTTPS

Dans les paramètres du site :
- Cocher **Forcer HTTPS**

---

## Étape 5 : Tâches Planifiées (Optionnel)

Pour les tâches de maintenance sans Celery :

1. Aller dans **Avancé** > **Tâches planifiées**
2. Ajouter les tâches :

### Nettoyage des sessions

```bash
# Tous les jours à 3h
cd /www/suddenly && source venv/bin/activate && python manage.py clearsessions
```

### Envoi des activités en attente

```bash
# Toutes les 5 minutes
cd /www/suddenly && source venv/bin/activate && python manage.py send_pending_activities
```

---

## Étape 6 : Vérification

### 6.1 Test de Base

```bash
curl -I https://votre-domaine.com/
# Doit retourner HTTP 200
```

### 6.2 Test Webfinger

```bash
curl "https://votre-domaine.com/.well-known/webfinger?resource=acct:admin@votre-domaine.com"
# Doit retourner du JSON
```

### 6.3 Test NodeInfo

```bash
curl https://votre-domaine.com/.well-known/nodeinfo
# Doit retourner les liens NodeInfo
```

---

## Mise à Jour

```bash
ssh compte@ssh-compte.alwaysdata.net
cd ~/www/suddenly

# Récupérer les mises à jour
git pull origin main

# Activer l'environnement
source venv/bin/activate

# Mettre à jour les dépendances
pip install -r requirements.txt

# Appliquer les migrations
python manage.py migrate

# Mettre à jour les fichiers statiques
python manage.py collectstatic --noinput
```

Puis redémarrer le site dans l'interface Alwaysdata.

---

## Dépannage

### Erreur 500

1. Vérifier les logs : **Web** > **Sites** > **Logs**
2. Vérifier `.env` est bien configuré
3. Vérifier les permissions des fichiers

### Base de données inaccessible

1. Vérifier l'URL dans `.env`
2. Tester la connexion :
   ```bash
   psql "postgres://..." -c "SELECT 1;"
   ```

### Fichiers statiques 404

1. Vérifier que `collectstatic` a été exécuté
2. Vérifier la configuration du site statique
3. Vérifier les chemins

### Fédération ne fonctionne pas

1. Vérifier que HTTPS est actif
2. Vérifier le domaine dans les settings
3. Tester avec :
   ```bash
   curl -H "Accept: application/activity+json" https://votre-domaine.com/@admin
   ```

---

## Ressources

- [Documentation Alwaysdata - Python](https://help.alwaysdata.com/fr/langages/python/)
- [Documentation Alwaysdata - PostgreSQL](https://help.alwaysdata.com/fr/bases-de-donnees/postgresql/)
- [Documentation Alwaysdata - SSL](https://help.alwaysdata.com/fr/securite/ssl-tls/)
