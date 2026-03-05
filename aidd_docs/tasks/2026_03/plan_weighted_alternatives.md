# Plan — Principe d'alternatives pondérées dans l'audit agentique

Date: 2026-03-05
Status: draft

## Objectif

Enrichir le workflow d'audit agentique avec un principe d'alternatives pondérées :
pour chaque composant architectural, l'agent propose 3 alternatives classées par couverture LLM,
les pondère avec la supervision humaine inférée, vérifie la cohérence globale, et soumet une
recommandation motivée à validation humaine.

---

## Fichiers à modifier

### 1. `aidd_docs/templates/custom/agentic_readiness_framework.md`

Ajouter une section **"Tech selection — weighted alternatives principle"** après le tableau
"Language and framework" existant. Contenu :

- Les deux axes de scoring : **LLM coverage** (1–3) × **human supervision** (inferred, 1–3)
- La règle de pondération : score combiné = LLM × 0.6 + supervision × 0.4
- La règle plancher : si l'alternative choisie a un score LLM inférieur de ≥ 1 point à la meilleure
  option disponible, l'agent signale la déviation explicitement et la documente
- Le principe d'inférence de la supervision humaine :
  - stack déjà en place dans le code = maîtrisée (3)
  - mentionnée dans CLAUDE.md sans être utilisée = notions (2)
  - absente du contexte = inconnue (1)
- La passe de cohérence globale : après toutes les recommandations, vérifier l'absence de
  frictions inter-composants et la cohérence avec les besoins fonctionnels identifiés

### 2. `aidd_docs/templates/custom/audit_score.md`

Enrichir avec quatre nouvelles sections, toutes incluses dans `audit_result.md` (pas de nouveau fichier) :

**Section "Project needs analysis"** (avant les axes de scoring) :
- Contraintes fonctionnelles et techniques extraites du projet (CLAUDE.md, code, docs)
- Si projet greenfield (pas de code existant) : l'agent pose la question à l'humain sur ses
  préférences de stack avant de générer les alternatives, et documente les réponses ici

**Section "Human supervision inference"** (avant Stack alternatives) :
- Tableau explicite de la supervision inférée par composant, que l'humain peut contester à la validation :
```
| Component | Inference source | Supervision score (1–3) |
```
Exemple : `| Framework | Used in existing code | 3 |`

**Section "Stack alternatives"** (après Human supervision inference) :
```
| Component | Option A | LLM | Sup | Combined | Option B | … | Option C | … | Recommended |
```
- LLM = score couverture LLM (1–3)
- Sup = score supervision inférée (1–3, repris depuis la section précédente)
- Combined = LLM × 0.6 + Sup × 0.4 (arrondi à 1 décimale)
- Recommended = option avec le Combined le plus élevé (sauf déviation justifiée)

**Section "Deviations"** (section de premier niveau, après Stack alternatives) :
- Liste des composants où l'option recommandée a un score LLM inférieur de ≥ 1 point
  à la meilleure alternative disponible
- Pour chaque déviation : composant, écart LLM, justification, impact estimé

### 3. `.claude/commands/custom/01/agentic_architecture.md`

Le déroulé des steps reste identique (Steps 1–4 inchangés). Seule la description du Step 1
est enrichie pour mentionner explicitement :
- Analyse des besoins avant le scoring
- Génération des 3 alternatives par composant
- Vérification de cohérence globale
Le résultat continue d'être écrit dans `audit_result.md`.

---

## Ordre d'implémentation

1. Mettre à jour `agentic_readiness_framework.md` — source de vérité
2. Mettre à jour `audit_score.md` — ajouter les 3 nouvelles sections
3. Mettre à jour la description du Step 1 dans `agentic_architecture.md` (commande)

---

## Décisions fixes (avant implémentation)

- **Ratio de pondération** : LLM × 0.6 + supervision × 0.4 — validé
- **Plancher LLM** : écart de ≥ 1 point sur l'échelle 1–3 entre l'option choisie et la meilleure
  disponible déclenche un signal de déviation — validé
- **Greenfield** : si aucun code existant, l'agent demande les préférences de stack à l'humain
  avant de générer les alternatives, et documente les réponses dans "Project needs analysis"
