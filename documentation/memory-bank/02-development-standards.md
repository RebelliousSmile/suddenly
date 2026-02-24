# Development Standards

**Last Updated**: 2026-01-02
**Project**: Suddenly
**Version**: 1.0.0

---

## Philosophy

This project follows three core principles:

### KISS (Keep It Simple, Stupid)
- Prefer simple solutions over complex ones
- Avoid over-engineering
- Code should be easy to understand and maintain

### YAGNI (You Aren't Gonna Need It)
- Don't implement features until they're actually needed
- Avoid speculative generality
- Focus on current requirements (MVP first)

### DRY (Don't Repeat Yourself)
- Extract common patterns into reusable functions/components
- Maintain single source of truth
- Refactor duplication when you see it 3+ times

---

## File Creation Rules

### When to Create New Files

**CREATE a new file when**:
- Functionality exceeds ~300 lines in existing file
- Clear single responsibility emerges
- Reusable across multiple Django apps
- Improves testability

**DO NOT CREATE files for**:
- One-off helpers (keep in utils.py)
- Single-use utilities
- Temporary operations
- Over-abstraction

### Naming Conventions

**Python/Django conventions:**

| Element | Convention | Example |
|---------|------------|---------|
| Files/Modules | snake_case | `character_service.py` |
| Functions | snake_case | `get_user_characters()` |
| Classes | PascalCase | `CharacterService` |
| Constants | SCREAMING_SNAKE | `MAX_THEME_CARDS = 4` |
| Variables | snake_case | `active_games` |
| Django Apps | snake_case, singular | `character`, `game`, `activitypub` |

---

## Code Quality Standards

### General Rules

- Max function length: **50 lines** (prefer < 20)
- Max file length: **500 lines** (split if larger)
- Max parameters: **5** (use dataclasses/dicts if more)
- Comment policy: Document **WHY**, not **WHAT**

### Type Hints (Mandatory)

```python
# Always use type hints
def get_character(character_id: int) -> Character | None:
    return Character.objects.filter(id=character_id).first()

# Use typing module for complex types
from typing import List, Optional, Dict

def get_user_games(user: User) -> List[Game]:
    ...
```

### Error Handling

```python
# Use specific exceptions
class CharacterNotFoundError(Exception):
    pass

class PermissionDeniedError(Exception):
    pass

# Handle at appropriate level
def claim_character(user: User, character_id: int) -> CharacterLink:
    character = get_object_or_404(Character, id=character_id)

    if character.status != CharacterStatus.NPC:
        raise ValidationError("Character already claimed")

    if not can_claim(user, character):
        raise PermissionDeniedError("Cannot claim this character")

    return CharacterLink.objects.create(...)
```

### Django-Specific Patterns

```python
# Querysets: Always use select_related/prefetch_related
characters = Character.objects.select_related(
    'owner', 'creator', 'origin_game'
).prefetch_related('appearances')

# Avoid N+1 queries
# BAD:
for game in games:
    print(game.owner.username)  # N+1!

# GOOD:
games = Game.objects.select_related('owner')
for game in games:
    print(game.owner.username)  # Single query
```

---

## Architecture Patterns

### Mandatory Patterns

1. **Fat Models, Thin Views**: Business logic in models/services, not views
2. **UUID Primary Keys**: All models use UUID for ActivityPub compatibility
3. **Soft Delete**: Never hard delete federated content
4. **Service Layer**: Complex operations in `services/` modules

### Project Structure

```
suddenly/
├── apps/
│   ├── users/           # User management, authentication
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── services.py
│   │   └── activitypub.py
│   ├── games/           # Games and Reports
│   ├── characters/      # Characters, Links, Appearances
│   ├── quotes/          # Character quotes
│   └── activitypub/     # Federation core
│       ├── actors.py
│       ├── activities.py
│       └── handlers.py
├── core/                # Shared utilities
│   ├── mixins.py
│   └── utils.py
├── config/              # Django settings
└── templates/
```

### Critical Modules

| Module | Purpose | Must Have Tests |
|--------|---------|-----------------|
| `activitypub/handlers.py` | Process incoming activities | Yes |
| `characters/services.py` | Claim/Adopt/Fork logic | Yes |
| `users/activitypub.py` | User federation | Yes |

---

## Testing Strategy

### Test Distribution (70/20/10)

- **70%** Static analysis (mypy, ruff, black)
- **20%** Contract tests (critical business logic)
- **10%** E2E tests (critical user journeys)

### Test Commands

```bash
# Static validation
mypy apps/ --strict
ruff check apps/
black --check apps/

# Contract tests
pytest tests/contracts/ -v

# E2E tests (critical only)
pytest tests/e2e/ -m critical

# Complete quality check
make quality  # Runs all above
```

### What to Test

**MUST test:**
- Claim/Adopt/Fork logic
- ActivityPub serialization/deserialization
- Permission checks
- Character status transitions

**DON'T test:**
- Simple CRUD views
- Django ORM operations
- Template rendering

### Test Coverage Targets

- Critical paths (federation, links): **90%**
- Business logic: **70%**
- Overall minimum: **50%**

---

## Documentation Standards

### Code Documentation

```python
def claim_character(
    requester: User,
    target_character: Character,
    proposed_character: Character,
    message: str
) -> LinkRequest:
    """
    Create a Claim request for a character.

    A Claim means "your NPC was actually my PC all along" (retcon).
    The target NPC will be replaced by the proposed PC if accepted.

    Args:
        requester: User making the claim
        target_character: The NPC to claim
        proposed_character: The PC that "was" the NPC
        message: Explanation of why this makes narrative sense

    Returns:
        LinkRequest with status PENDING

    Raises:
        ValidationError: If target is not an NPC
        PermissionDeniedError: If requester doesn't own proposed_character
    """
```

### README Files

Required READMEs:
- `/README.md`: Project overview, setup, quick start
- `/apps/activitypub/README.md`: Federation protocol details
- `/documentation/`: All specs and architecture docs

---

## Security Standards

### Input Validation

```python
# Always validate user input
from django.core.validators import validate_email

# Use Django forms for complex validation
class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['title', 'content']

    def clean_content(self):
        content = self.cleaned_data['content']
        # Sanitize markdown, check for XSS
        return bleach.clean(content, tags=ALLOWED_TAGS)
```

### ActivityPub Security

```python
# Always verify HTTP signatures on incoming activities
def verify_signature(request) -> bool:
    """Verify that the activity comes from the claimed actor."""
    ...

# Never trust remote content blindly
def process_incoming_activity(activity: dict):
    if not verify_signature(request):
        raise SecurityError("Invalid signature")

    # Validate actor exists and matches
    actor_id = activity.get('actor')
    if not is_valid_actor(actor_id):
        raise SecurityError("Unknown actor")
```

### Data Protection

- Never commit `.env` files
- Use `django-environ` for config
- Hash passwords with Django's built-in hasher
- Encrypt sensitive federation data in transit

---

## Git Workflow

### Commit Message Convention

```
type(scope): description

Types:
- feat: New feature
- fix: Bug fix
- refactor: Code refactoring
- docs: Documentation
- test: Adding tests
- chore: Maintenance

Examples:
- feat(characters): add Claim request workflow
- fix(activitypub): handle missing inbox URL
- refactor(games): extract service layer
```

### Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code |
| `develop` | Integration branch |
| `feat/*` | New features |
| `fix/*` | Bug fixes |

---

## Performance Guidelines

### Performance Budgets

| Metric | Target |
|--------|--------|
| Page load | < 2s |
| API response | < 200ms |
| Database queries per page | < 10 |
| ActivityPub delivery | < 5s async |

### Django Performance

```python
# Use database indexes
class Character(models.Model):
    status = models.CharField(db_index=True)
    origin_game = models.ForeignKey(Game, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'origin_game']),
        ]

# Paginate querysets
from django.core.paginator import Paginator

def list_characters(request):
    characters = Character.objects.all()
    paginator = Paginator(characters, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'characters/list.html', {'page': page})
```

---

## Project-Specific Notes

### ActivityPub Conventions

- All actors (User, Game, Character) have `remote_id`, `inbox`, `outbox`
- Use `local` boolean to distinguish local vs federated content
- Celery for async federation tasks
- Transform custom types (Report, Quote) to Article/Note for Mastodon

### Character Status Flow

```
NPC (created) → CLAIMED (retcon) → PC
NPC (created) → ADOPTED (takeover) → PC
NPC (created) → FORKED (derivative) → new PC + original NPC remains
```

### Quote Visibility

```
EPHEMERAL → disappears after session
PRIVATE   → only creator sees
PUBLIC    → federated to followers
```
