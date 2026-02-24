# Task Workflow Configuration

**Project**: Suddenly
**Last Updated**: 2026-01-02

---

## TL;DR

```
Tache → Plan → Review Plan → Implementation → Tests → Review Code → Commit
         ↑         ↓                              ↑         ↓
         └── Fix ──┘                              └── Fix ──┘
```

**Principe** : Valider le plan AVANT d'implementer, corriger en boucle jusqu'a approbation.

---

## Workflow Visuel

```
┌─────────────────────────────────────────────────────────┐
│                    TASK WORKFLOW                        │
└─────────────────────────────────────────────────────────┘

[1] Analyse Tache
        ↓
[2] Redaction Plan ←───────────────┐
        ↓                          │
[3] Review Plan → ◆ Approuve? ◆    │
                   ↙ Non    ↘ Oui  │
              Corriger Plan ───────┘
                              ↓
[4] Implementation (DIRECT ou STEP-BY-STEP)
        ↓
[5] Tests (70/20/10)
        ↓
[6] Review Code → ◆ Approuve? ◆
                  ↙ Non    ↘ Oui
              Corriger ────→ Commit
```

---

## Configuration: Strategie Implementation

### Criteres DIRECT vs STEP-BY-STEP

```yaml
DIRECT (implementation unique + commit):
  conditions:
    - Temps estime: < 2 heures
    - Fichiers a modifier: < 3 fichiers
    - Complexite: Faible
  exemples:
    - "Ajouter champ au modele"
    - "Fix bug validation"
    - "Update config"

STEP-BY-STEP (jalons + commits par jalon):
  conditions:
    - Temps estime: > 2 heures
    - Fichiers a modifier: > 3 fichiers
    - Complexite: Moyenne ou Haute
  exemples:
    - "Implementer systeme Claim/Adopt/Fork"
    - "Ajouter federation ActivityPub"
    - "Refactorer couche services"
```

---

## Configuration: Agents pour Review

### Agents Review Plan (Etape 3)

```yaml
PLAN_REVIEW_AGENTS:
  - technical-architect:
      purpose: "Architecture, performance, securite"

  - documentation-architect:
      purpose: "Coherence avec specs, documentation"
```

**Performance**: Lancer tous les agents en **UN message** (execution parallele).

### Agents Review Code (Etape 6)

```yaml
CODE_REVIEW_AGENTS:
  - technical-architect:
      purpose: "Qualite code, performance, conventions"

  - claude-code-optimizer:
      purpose: "Configuration Claude Code si modifiee"
```

---

## Configuration: Commandes de Test

### Validation Statique (70%)

```yaml
COMMAND_VALIDATE: "mypy apps/ --strict && ruff check apps/ && black --check apps/"
```

### Tests Contrats (20%)

```yaml
COMMAND_TEST_CONTRACTS: "pytest tests/contracts/ -v"
```

### Tests E2E Critiques (10%)

```yaml
COMMAND_TEST_E2E_CRITICAL: "pytest tests/e2e/ -m critical"
```

### Check Qualite Complet

```yaml
COMMAND_QUALITY: "make quality"

# Equivalent a:
# mypy apps/ && ruff check apps/ && black --check apps/ && pytest tests/contracts/ && pytest tests/e2e/ -m critical
```

---

## Configuration: Serveur Dev

```yaml
DEV_SERVER:
  command: "python manage.py runserver"
  port: 8000
  url: "http://localhost:8000"
```

---

## Configuration: Checkpoints

### Frequence des Checkpoints

```yaml
CHECKPOINTS:
  - Apres chaque jalon (mode STEP-BY-STEP)
  - Apres 2 heures de travail continu
  - Avant refactoring majeur
  - Apres implementation feature critique (federation, links)
```

### Questions Checkpoint

```
1. L'implementation correspond-elle aux attentes?
2. Y a-t-il des problemes visuels/fonctionnels?
3. Doit-on continuer au prochain jalon?
```

---

## Configuration: Convention Commits

```yaml
COMMIT_FORMAT: "type(scope): description"

TYPES:
  - feat: Nouvelle fonctionnalite
  - fix: Correction de bug
  - refactor: Refactoring sans changement fonctionnel
  - docs: Documentation
  - test: Ajout/modification tests
  - chore: Maintenance, config

SCOPES:
  - users: Module utilisateurs
  - games: Module parties
  - characters: Module personnages
  - quotes: Module citations
  - activitypub: Federation
  - api: Endpoints API

EXEMPLES:
  - "feat(characters): add Claim workflow"
  - "fix(activitypub): handle missing inbox URL"
  - "refactor(games): extract service layer"
  - "test(characters): add contract tests for status transitions"
```

---

## Benefices des Boucles de Feedback

### Gain de Temps Quantifie

**Sans boucles (lineaire)**:
```
Plan incorrect → Implementation complete (4h) → Review echoue
→ Rework complet (4h) = 8h total
```

**Avec boucles (iteratif)**:
```
Plan incorrect → Review plan (10 min) → Ajustement (15 min)
→ Implementation correcte (4h) → Review passe = 4h25min

GAIN: 3h35min (45% temps economise)
```

### Amelioration Qualite

| Metrique | Sans boucles | Avec boucles |
|----------|--------------|--------------|
| Taux succes 1er essai | 70% | 90% |
| Taux rework | 30% | 10% |
| Detection problemes | Post-implementation | Pre-implementation |

---

## Integration avec Agents

Ce workflow est orchestre par les agents disponibles :

| Agent | Role dans Workflow |
|-------|-------------------|
| `technical-architect` | Review plan + Review code |
| `documentation-architect` | Coherence documentation |
| `claude-code-optimizer` | Si config Claude Code modifiee |

**Principe** : Lire ce fichier pour la configuration, utiliser les agents pour l'execution.

---

## Checklist Customisation

- [x] Seuils DIRECT vs STEP-BY-STEP definis
- [x] Agents review plan configures
- [x] Agents review code configures
- [x] Commandes test definies
- [x] Serveur dev configure
- [x] Convention commits definie
- [x] Checkpoints definis

---

## Modules Critiques (Tests Obligatoires)

Ces modules DOIVENT avoir des tests contrats :

| Module | Raison |
|--------|--------|
| `apps/characters/services.py` | Logique Claim/Adopt/Fork |
| `apps/activitypub/handlers.py` | Reception activites federation |
| `apps/activitypub/serializers.py` | Serialisation ActivityPub |
| `apps/users/federation.py` | Gestion users federes |
