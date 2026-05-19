# Guideline — rédiger un CLAUDE.md

## Ce que c'est

Un fichier CLAUDE.md est une instruction opérationnelle destinée à Claude. Son rôle est de décrire **comment travailler** sur ce projet, pas **ce qu'est** le projet.

## Lire la mémoire en premier

Tout CLAUDE.md doit commencer par une directive explicite de lecture de la mémoire avant de commencer à travailler :

```markdown
Lis `aidd_docs/memory/` (root) avant de commencer. En cas de doute sur une décision technique, consulte `aidd_docs/memory/internal/` et `aidd_docs/memory/external/`.
```

## Ce qu'un CLAUDE.md doit contenir

- La directive de lecture de la mémoire (voir ci-dessus)
- Les règles comportementales : conventions de commit, workflow Git, outils imposés (`pnpm` pas `npm`, etc.)
- Les interdits explicites (`Never X`, `Do not Y`)
- Les décisions non déductibles du code (ex. : "toujours passer par l'API interne, jamais directement en base")
- Des pointeurs vers des sections de mémoire ou règles pertinentes si le projet est complexe

## Ce qu'un CLAUDE.md ne doit PAS contenir

- Des informations techniques déjà dans la mémoire (stack, architecture, décisions documentées) — c'est le rôle de `aidd_docs/memory/`
- Des chemins de fichiers, commandes d'installation, procédures de déploiement — c'est le rôle du README
- Des explications narratives sur le fonctionnement du projet — CLAUDE.md est lu par Claude, pas par des humains
- Des tâches en cours ou du contexte de session — utiliser les plans et tâches pour ça

## Principe directeur

> Si l'information peut être déduite en lisant le code ou la mémoire, elle n't a pas sa place dans CLAUDE.md.

CLAUDE.md = règles comportementales. Pas une encyclopédie projet.

Un CLAUDE.md surchargé dilue les règles importantes. Avant d'y ajouter quelque chose, poser la question : "Est-ce une règle de comportement, ou une information ?" Si c'est une information → mémoire ou README.
