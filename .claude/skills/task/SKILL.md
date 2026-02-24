---
name: task
description: Use when user invokes /task command to execute a complete development task. Orchestrates the full workflow from analysis to commit including plan review with agents, implementation, testing, and code review.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, TodoWrite, EnterPlanMode, ExitPlanMode, AskUserQuestion
---

# Task Workflow Skill

Skill pour orchestrer le workflow complet de developpement selon la methode Suddenly.

## Workflow

```
Tache -> Plan -> Review Plan -> Implementation -> Tests -> Review Code -> Commit
          ^         |                              ^         |
          +-- Fix --+                              +-- Fix --+
```

**Principe** : Valider le plan AVANT d'implementer, corriger en boucle jusqu'a approbation.

---

## Etape 1 : Analyse Tache

**Input** : Description de la tache fournie par l'utilisateur via `/task "description"`

**Actions** :
1. Creer une todo list avec TodoWrite pour tracker le workflow
2. Lire `documentation/memory-bank/03-task-workflow.md` pour la configuration complete
3. Identifier le scope (apps concernees, fichiers existants)
4. Rechercher le code existant pertinent avec Grep/Glob
5. Determiner le type d'implementation :
   - **DIRECT** : < 3 fichiers, complexite faible
   - **STEP-BY-STEP** : >= 3 fichiers, complexite moyenne/haute

**Output** : Synthese de l'analyse avec type d'implementation choisi

---

## Etape 2 : Redaction Plan

**IMPORTANT : Activer le mode plan avec `EnterPlanMode`**

Rediger un plan structure selon ce template :

```markdown
# Plan : [Titre Tache]

## Contexte
- **Tache** : [description originale]
- **Type** : [DIRECT | STEP-BY-STEP]
- **Fichiers estimes** : [nombre]
- **Complexite** : [Faible | Moyenne | Haute]

## Objectif
[Ce que la tache doit accomplir en 2-3 phrases]

## Fichiers a modifier/creer

| Fichier | Action | Description |
|---------|--------|-------------|
| `path/to/file1.py` | Modifier | [changement] |
| `path/to/file2.py` | Creer | [description] |

## Jalons (si STEP-BY-STEP)

### Jalon 1 : [Nom]
- [ ] Action 1
- [ ] Action 2
- Fichiers : `file1.py`, `file2.py`

### Jalon 2 : [Nom]
- [ ] Action 1
- Fichiers : `file3.py`

## Tests requis
- [ ] Validation statique : mypy, ruff, black
- [ ] Tests contrat : [lister si logique metier]
- [ ] Tests E2E : [si parcours critique]

## Risques et Mitigations
| Risque | Mitigation |
|--------|------------|
| [risque] | [mitigation] |

## Commit prevu
`type(scope): description`
```

---

## Etape 3 : Review Plan

**Lancer les reviews en PARALLELE avec l'outil Task**

Invoquer les deux agents simultanement dans UN SEUL message :

```
Task 1 - subagent_type: technical-architect
prompt: |
  MODE: REVIEW_PLAN

  Revois ce plan du point de vue architecture, performance et securite.
  Reponds avec APPROUVE ou CORRECTIONS_REQUISES avec details.

  [Coller le plan complet]

Task 2 - subagent_type: documentation-architect
prompt: |
  MODE: REVIEW_PLAN

  Verifie la coherence de ce plan avec les specs et la documentation existante.
  Reponds avec APPROUVE ou CORRECTIONS_REQUISES avec details.

  [Coller le plan complet]
```

**Attendre les retours des deux agents**

### Si APPROUVE par les deux agents :
- Passer a l'etape 4 (Implementation)
- Utiliser ExitPlanMode

### Si CORRECTIONS demandees :
1. Lister les corrections requises
2. Modifier le plan selon les retours
3. Re-soumettre pour review
4. Boucler jusqu'a approbation

---

## Etape 4 : Implementation

### Mode DIRECT (< 3 fichiers)

Implementer tous les changements en une sequence :
1. Creer/modifier chaque fichier selon le plan
2. Un seul commit a la fin du workflow

### Mode STEP-BY-STEP (>= 3 fichiers)

Implementer jalon par jalon :
1. Executer le jalon N
2. Verifier que le code compile/fonctionne
3. Checkpoint avec l'utilisateur si necessaire (AskUserQuestion)
4. Commit intermediaire si le jalon est autonome
5. Passer au jalon N+1

**Conventions obligatoires** :
- PEP 8 + type hints obligatoires
- Docstrings pour fonctions/classes publiques
- `select_related`/`prefetch_related` pour queries Django

---

## Etape 5 : Tests

**Executer dans l'ordre et corriger jusqu'a succes**

### 1. Validation Statique (70% de la valeur)

```bash
mypy apps/ --strict && ruff check apps/ && black --check apps/
```

### 2. Tests Contrat (20% de la valeur)

```bash
pytest tests/contracts/ -v
```

### 3. Tests E2E Critiques (10% - si applicable)

```bash
pytest tests/e2e/ -m critical
```

### Boucle de Correction

**Si echec** :
1. Identifier l'erreur dans l'output
2. Corriger le code concerne
3. Re-executer le test qui a echoue
4. Repeter jusqu'a succes de tous les tests

---

## Etape 6 : Review Code

**Lancer la review code avec agents**

```
Task - subagent_type: technical-architect
prompt: |
  MODE: REVIEW_CODE

  Revois ce code du point de vue qualite, performance et conventions.
  Reponds avec APPROUVE ou CORRECTIONS_REQUISES avec details.

  [Resume des changements effectues]
  [Fichiers modifies avec extraits pertinents]
```

### Si Configuration Claude Code Modifiee (.claude/)

Ajouter un second agent en parallele :

```
Task - subagent_type: claude-code-optimizer
prompt: |
  Valide que les modifications de configuration Claude Code suivent les best practices.
  [Fichiers .claude/ modifies]
```

### Traitement des Retours

**Si APPROUVE** : Passer au commit

**Si CORRECTIONS demandees** :
1. Appliquer les modifications
2. Re-executer les tests (etape 5)
3. Re-soumettre pour review
4. Boucler jusqu'a approbation

---

## Etape 7 : Commit

### Format du Message

```
type(scope): description courte
```

### Types et Scopes

| Type | Usage |
|------|-------|
| `feat` | Nouvelle fonctionnalite |
| `fix` | Correction de bug |
| `refactor` | Refactoring sans changement fonctionnel |
| `docs` | Documentation |
| `test` | Ajout/modification tests |
| `chore` | Maintenance, config |

| Scope | Module |
|-------|--------|
| `users` | apps/users/ |
| `games` | apps/games/ |
| `characters` | apps/characters/ |
| `quotes` | apps/quotes/ |
| `activitypub` | apps/federation/ |
| `api` | Endpoints API |

---

## Configuration Reference

### Seuils DIRECT vs STEP-BY-STEP

```yaml
DIRECT:
  fichiers: "< 3"
  complexite: "Faible"
  exemples:
    - "Ajouter champ au modele"
    - "Fix bug validation"

STEP-BY-STEP:
  fichiers: ">= 3"
  complexite: "Moyenne ou Haute"
  exemples:
    - "Implementer systeme Claim/Adopt/Fork"
    - "Ajouter federation ActivityPub"
```

### Modules Critiques (Tests Obligatoires)

| Module | Raison |
|--------|--------|
| `apps/characters/services.py` | Logique Claim/Adopt/Fork |
| `apps/activitypub/handlers.py` | Reception activites federation |
| `apps/activitypub/serializers.py` | Serialisation ActivityPub |
| `apps/users/federation.py` | Gestion users federes |

---

## Voir Aussi

- `documentation/memory-bank/03-task-workflow.md` : Configuration complete
- `documentation/memory-bank/02-development-standards.md` : Standards dev
