# Guides de Déploiement Suddenly

Ce dossier contient les guides de déploiement pour différentes plateformes.

## Plateformes Supportées

| Plateforme | Difficulté | Coût | Recommandé pour |
|------------|------------|------|-----------------|
| [Alwaysdata](./alwaysdata.md) | Facile | ~10€/mois | Débutants, petites instances |
| [VPS](./vps.md) | Intermédiaire | ~5-20€/mois | Contrôle total, instances moyennes |
| [Docker](./docker.md) | Intermédiaire | Variable | Développeurs, CI/CD |

## Prérequis Communs

### Obligatoires

- **Python 3.12+**
- **PostgreSQL 16+**
- **Domaine** avec accès DNS
- **HTTPS** (certificat SSL)

### Optionnels

- **Redis** : Cache et sessions (recommandé en production)
- **Celery** : Tâches asynchrones (recommandé pour fédération)

## Architecture de Déploiement

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Reverse Proxy                             │
│                 (Nginx / Caddy / PaaS)                       │
│                    HTTPS termination                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application                               │
│                 Gunicorn + Django                            │
└─────────────────────────────────────────────────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  PostgreSQL  │    │    Redis     │    │    Celery    │
│   (requis)   │    │  (optionnel) │    │  (optionnel) │
└──────────────┘    └──────────────┘    └──────────────┘
```

## Configuration Commune

### Variables d'Environnement

```bash
# Obligatoires
SECRET_KEY=une-cle-secrete-longue-et-aleatoire
DATABASE_URL=postgres://user:pass@host:5432/suddenly
DOMAIN=suddenly.example.com
ALLOWED_HOSTS=suddenly.example.com

# Production
DEBUG=False
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Optionnelles
REDIS_URL=redis://localhost:6379/0
EMAIL_URL=smtp://user:pass@smtp.example.com:587
MEDIA_URL=https://cdn.example.com/media/
```

### Génération de SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Checklist Post-Déploiement

- [ ] HTTPS fonctionne
- [ ] Webfinger répond : `/.well-known/webfinger?resource=acct:admin@domain`
- [ ] NodeInfo accessible : `/.well-known/nodeinfo`
- [ ] Création de compte fonctionne
- [ ] Upload de médias fonctionne
- [ ] Fédération avec une autre instance testée

## Support

En cas de problème :
1. Consultez les logs (`journalctl`, fichiers de log)
2. Vérifiez la configuration
3. Ouvrez une issue sur GitHub
