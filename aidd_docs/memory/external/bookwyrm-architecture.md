# BookWyrm — Architecture de Référence

> Réseau social fédéré pour le suivi de livres (alternative à Goodreads). Référence ActivityPub pour Suddenly.

## Stack

- Django + PostgreSQL + Celery + Redis + ActivityPub
- Frontend : Django Templates + Bulma (SSR)
- Déploiement : Docker + Nginx + Gunicorn

## Patterns réutilisables pour Suddenly

### 1. Remote vs Local

```python
class FederatedMixin:
    local = BooleanField(default=True)
    remote_id = CharField(unique=True, null=True)

    def save(self):
        if self.local and not self.remote_id:
            self.remote_id = f"https://{DOMAIN}/{self.path}"
        super().save()
```

### 2. Inbox/Outbox pattern

```python
def receive_activity(request, user_id):
    activity = json.loads(request.body)
    handlers = {'Follow': handle_follow, 'Create': handle_create, ...}
    return handlers[activity['type']](activity)
```

### 3. Celery pour fédération

```python
@celery_app.task
def broadcast_activity(activity, recipients):
    for inbox_url in recipients:
        sign_and_send(activity, inbox_url)
```

### 4. Soft delete

```python
def delete_user(user):
    user.is_active = False
    user.email = mangle_email(user.email)
    user.statuses.update(deleted=True, content="")
    user.save()
```

## Types AP BookWyrm → Suddenly

| BookWyrm | Suddenly |
|----------|----------|
| Book, Author | Game, Character |
| Review, Comment | Report, Quote |
| Shelf | Game status / Character status |
| Follow User | Follow Game, Follow Character |

## Types AP à adapter

```python
SUDDENLY_TYPES = {
    'Report': 'Article',
    'Quote': 'Note',
    'Character': 'Person',
    'Game': 'Collection',
    'LinkRequest': 'Offer',
}
```

## Fichiers BookWyrm à étudier

- `activitypub/` — base classes (réutiliser/adapter)
- `signatures.py` — HTTP Signatures (réutiliser)
- `models/base_model.py` — ActivitypubMixin (étudier)
- `views/inbox.py`, `views/outbox.py` — handlers (adapter)

## Différences architecturales

| | BookWyrm | Suddenly |
|-|----------|----------|
| Déploiement | Docker requis | PaaS / VPS / Docker |
| Redis | Requis | Optionnel |
| Celery | Requis | Optionnel (fallback sync) |
