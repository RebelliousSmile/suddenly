---
paths:
  - "templates/**/*.html"
  - "suddenly/**/*.py"
---

# Vocabulaire d'affichage — modèle vs UI

Le nom de code d'un modèle et son libellé UI divergent. Toujours utiliser le libellé UI dans les chaînes visibles (`{% trans %}`, `gettext`, labels, titres).

| Modèle (code) | UI EN | UI FR |
| ------------- | ----- | ----- |
| `Report`      | scene | scène |
| `Rapport`     | post  | post  |

- `Report` = une **scène** (jamais « report » en UI) ; `Rapport` = un **post** dans une scène
- Homographe piège : `Report` (modèle EN) ≠ `Rapport` (modèle FR = post) — ne pas traduire `Report`→« rapport »
- Renommer les identifiants de code n'est **pas** requis ; seul l'affichage suit ce mapping
