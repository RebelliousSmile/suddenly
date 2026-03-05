# Pull Request — Template

## Format

```markdown
# [Titre — résumé court et descriptif]

## ✅ Type de PR

- [ ] Refactor
- [ ] Feature
- [ ] Bug Fix
- [ ] Optimization
- [ ] Documentation Update

## 🗒️ Description

[Description concise des changements fonctionnels, pas techniques]

## 🚶‍➡️ Comportement

- [Changements visibles par l'utilisateur]
- [Focus sur l'expérience utilisateur]
- [Précis, pas vague]

## 🧪 Étapes de test

- [ ] [Étape 1]
- [ ] [Étape 2]
- [ ] [Étape 3]
```

## Règles

- Titre court, descriptif, capture l'essentiel du changement
- Description : ce qui change fonctionnellement, pas l'implémentation
- Toute PR modifiant l'API ActivityPub documente l'impact Mastodon
- Les tests passent et l'analyse statique est propre avant review
- Mettre en évidence les breaking changes
