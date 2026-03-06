# Déploiement sur Alwaysdata

Guide de déploiement de Suddenly sur Alwaysdata (PaaS).

**Difficulté** : Facile
**Coût** : ~10€/mois
**Prérequis** : Compte Alwaysdata, domaine configuré

---

## Étape 1 : Créer les ressources dans le panel

- **Base de données** PostgreSQL → noter host, port, nom, user, password
- **Site** Python WSGI (voir configuration ci-dessous)

> Alwaysdata ne propose pas Redis — le projet bascule automatiquement sur DB cache si `REDIS_URL` est absent.

---

## Étape 2 : Cloner le dépôt en SSH

```bash
ssh user@ssh-user.alwaysdata.net
cd /home/<user>/www/
git clone https://github.com/RebelliousSmile/suddenly.git soudainement
```

---

## Étape 3 : Installer les dépendances

```bash
cd /home/<user>/www/soudainement
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e ".[federation]"
```

---

## Étape 4 : Générer les clés ActivityPub

```bash
mkdir -p /home/<user>/www/soudainement/keys
cd /home/<user>/www/soudainement/keys
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

---

## Étape 5 : Initialiser la base de données

Exporter les variables d'env manuellement (elles ne sont pas disponibles en SSH) :

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
export SECRET_KEY="..."
export DOMAIN=soudainement.fr
export ALLOWED_HOSTS=soudainement.fr,www.soudainement.fr
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
```

> **Important** : encoder les caractères spéciaux du mot de passe :
> ```bash
> python3 -c "from urllib.parse import quote_plus; print(quote_plus('mot_de_passe'))"
> ```

```bash
python manage.py migrate
python manage.py createcachetable
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

---

## Étape 6 : Configurer le site dans le panel

| Champ | Valeur |
|-------|--------|
| Chemin de l'application | `www/soudainement/suddenly/wsgi.py` |
| Répertoire de travail | `www/soudainement/` |
| Version Python | `3.12` |
| Répertoire du virtualenv | `www/soudainement/venv` |
| Chemins statiques | `/static/ staticfiles/` et `/media/ media/` |

> **Pièges** :
> - Le fichier WSGI est dans `suddenly/wsgi.py`, **pas** `config/wsgi.py`
> - Les chemins statiques sont **relatifs au répertoire de travail** (ne pas mettre le chemin absolu)

### Variables d'environnement (format `FOO=bar` sans `export`)

```
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<généré>
DOMAIN=soudainement.fr
ALLOWED_HOSTS=soudainement.fr,www.soudainement.fr
DATABASE_URL=postgresql://user:password_encodé@host:5432/dbname
```

---

## Étape 7 : SSL

Activer Let's Encrypt via le panel Alwaysdata pour le domaine.

---

## Étape 8 : Tâches planifiées

Dans le panel → Tâches planifiées. Variables d'env à renseigner dans chaque tâche (même format que le site).

**Nettoyage sessions** (quotidien) :
```
Fréquence : 0 3 * * *
Commande  : /home/<user>/www/soudainement/venv/bin/python /home/<user>/www/soudainement/manage.py clearsessions
```

**Nettoyage citations éphémères** (horaire) :
```
Fréquence : 0 * * * *
Commande  : /home/<user>/www/soudainement/venv/bin/python /home/<user>/www/soudainement/manage.py shell -c "from suddenly.activitypub.tasks import cleanup_expired_quotes; cleanup_expired_quotes()"
```

---

## Mise à jour

```bash
cd /home/<user>/www/soudainement
git pull
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
```

Puis redémarrer le site depuis le panel.

---

## Checklist post-déploiement

```
[ ] https://domaine.fr répond
[ ] https://domaine.fr/.well-known/webfinger?resource=acct:admin@domaine.fr
[ ] https://domaine.fr/.well-known/nodeinfo
[ ] Création de compte fonctionne
[ ] Fédération testée avec une autre instance
```
