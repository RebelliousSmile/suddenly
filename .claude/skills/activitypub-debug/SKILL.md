---
name: activitypub-debug
description: Use when debugging ActivityPub federation issues, HTTP signature errors, inbox/outbox problems, webfinger failures, or remote actor discovery issues.
allowed-tools: Read, Grep, Glob, Bash, WebFetch
---

# ActivityPub Debug Skill

Skill pour diagnostiquer et résoudre les problèmes de fédération ActivityPub.

## Diagnostic Rapide

### 1. Vérifier les endpoints locaux

```bash
# Webfinger
curl -s "http://localhost:8000/.well-known/webfinger?resource=acct:admin@localhost:8000" | python -m json.tool

# NodeInfo
curl -s "http://localhost:8000/.well-known/nodeinfo" | python -m json.tool

# Actor (User)
curl -s -H "Accept: application/activity+json" "http://localhost:8000/@admin" | python -m json.tool

# Actor (Character)
curl -s -H "Accept: application/activity+json" "http://localhost:8000/characters/detective-marlowe" | python -m json.tool
```

### 2. Tester une instance distante

```bash
# Webfinger distant
curl -s "https://remote.instance/.well-known/webfinger?resource=acct:user@remote.instance" | python -m json.tool

# Actor distant
curl -s -H "Accept: application/activity+json" "https://remote.instance/@user" | python -m json.tool

# NodeInfo distant (vérifier si Suddenly)
curl -s "https://remote.instance/nodeinfo/2.0" | python -m json.tool | grep -A2 "software"
```

### 3. Vérifier les logs

```bash
# Logs ActivityPub (si configuré)
tail -100 logs/activitypub.log | grep -i error

# Logs Django
tail -100 logs/django.log | grep -i "inbox\|outbox\|signature"

# Requêtes récentes dans la DB
python manage.py shell -c "
from apps.federation.models import ActivityLog
for log in ActivityLog.objects.order_by('-created_at')[:10]:
    print(f'{log.created_at} {log.activity_type} {log.status}')
"
```

## Problèmes Courants

### Signature HTTP invalide

**Symptômes** : 401/403 sur inbox distant, "Invalid signature"

**Diagnostic** :
```python
# Vérifier que les clés existent
python manage.py shell -c "
from apps.users.models import User
user = User.objects.get(username='admin')
print('Public key:', 'OK' if user.public_key else 'MISSING')
print('Private key:', 'OK' if user.private_key else 'MISSING')
"
```

**Causes fréquentes** :
1. Horloge désynchronisée (> 5 min de décalage)
2. Clés non générées
3. Mauvais format de signature
4. Headers manquants (Date, Digest, Host)

**Solution** :
```bash
# Synchroniser l'horloge
sudo ntpdate pool.ntp.org

# Régénérer les clés
python manage.py shell -c "
from apps.users.models import User
from apps.federation.crypto import generate_key_pair
user = User.objects.get(username='admin')
user.public_key, user.private_key = generate_key_pair()
user.save()
print('Keys regenerated')
"
```

### Acteur non trouvé (404)

**Symptômes** : "Actor not found", webfinger échoue

**Diagnostic** :
```bash
# Vérifier le format de la requête
curl -v "https://instance/.well-known/webfinger?resource=acct:user@instance"

# Vérifier que l'acteur existe
python manage.py shell -c "
from apps.users.models import User
print(User.objects.filter(username='admin').exists())
"
```

**Causes fréquentes** :
1. Mauvais format `acct:` (manque le @domain)
2. Username inexistant
3. Acteur non local (local=False)

### Inbox rejette l'activité

**Symptômes** : 400/422 sur POST inbox

**Diagnostic** :
```python
# Activer le logging détaillé temporairement
# Dans settings.py :
LOGGING['loggers']['apps.federation'] = {
    'level': 'DEBUG',
    'handlers': ['file'],
}
```

**Causes fréquentes** :
1. Type d'activité non supporté
2. Champs obligatoires manquants
3. Acteur bloqué
4. Signature invalide (voir ci-dessus)

### Contenu non fédéré

**Symptômes** : Report publié mais non visible sur instances distantes

**Diagnostic** :
```python
# Vérifier la file d'envoi
python manage.py shell -c "
from apps.federation.models import OutgoingActivity
pending = OutgoingActivity.objects.filter(status='PENDING')
print(f'{pending.count()} activités en attente')
for act in pending[:5]:
    print(f'  {act.activity_type} -> {act.target_inbox}')
"
```

**Causes fréquentes** :
1. Celery non démarré (si async)
2. Aucun follower distant
3. Visibilité non publique
4. Erreurs de livraison (voir logs)

## Commandes de Test

### Envoyer une activité de test

```python
python manage.py shell << 'EOF'
from apps.federation.delivery import deliver_activity
from apps.users.models import User

user = User.objects.get(username='admin')
activity = {
    "@context": "https://www.w3.org/ns/activitystreams",
    "type": "Create",
    "actor": user.ap_id,
    "object": {
        "type": "Note",
        "content": "Test federation"
    }
}

# Test vers une inbox spécifique
result = deliver_activity(activity, "https://remote.instance/inbox", user)
print(f"Delivery: {result}")
EOF
```

### Vérifier la compatibilité Mastodon

```bash
# Tester avec une instance Mastodon connue
curl -s -H "Accept: application/activity+json" \
    "https://mastodon.social/@Gargron" | python -m json.tool | head -30
```

## Checklist Debug

- [ ] Webfinger répond correctement
- [ ] Acteur accessible en JSON-LD
- [ ] Clés publiques/privées présentes
- [ ] Horloge synchronisée
- [ ] Logs sans erreur
- [ ] Celery actif (si utilisé)
- [ ] Followers distants existent
