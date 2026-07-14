# Design System

Le langage visuel de Suddenly vit dans un **contrat en trois couches**, versionné avec le code. Cette page explique ce qu'il contient et comment le consommer. Elle ne recopie aucune valeur : c'est précisément la duplication des valeurs qui avait rendu la version précédente de ce document fausse (elle décrivait encore un mode sombre noir, alors que le produit est passé au sépia).

---

## Où vit le contrat

| Couche | Fichier | Contenu | Qui l'écrit |
|---|---|---|---|
| 1 | `design/tokens.json` | Les valeurs : couleurs, typographie, espacement, rayons, ombres, mouvement | `design:adjust` |
| 2 | `design/components.json` | Le vocabulaire fermé : composants, variantes, règles d'usage des tokens | `design:adjust` |
| 3 | `design/design-system.md` | La charte : intentions, fondations, accessibilité, questions ouvertes | `design:adjust` |

Les fichiers de `design/adapters/` (`tokens.css`, `uno-tokens.mjs`) sont **générés** depuis `tokens.json`. Ne jamais les éditer à la main : la prochaine régénération écraserait la modification.

Format : W3C Design Tokens (DTCG). Le mode sombre est un **overlay** (`themes.dark`) : il ne redéfinit que les chemins qui changent, jamais l'arbre entier.

---

## Les trois principes qui ne se négocient pas

### 1. La couleur porte du sens métier

Le groupe `color.domain.*` n'est pas décoratif : il encode l'état narratif d'un personnage. Un PJ, un PNJ, un PNJ adoptable, un personnage venu d'une instance fédérée, un fork — chacun a sa couleur, et ces couleurs ne sont pas interchangeables. Réutiliser `color.domain.remote` parce que « ce violet est joli » casse la lecture du produit.

Corollaire figé : **un statut n'est jamais porté par la seule couleur.** Il s'accompagne toujours d'un libellé ou d'une icône, et les anneaux d'avatar ajoutent un style de trait distinct. Sans cela, l'information la plus importante du produit est invisible pour un utilisateur daltonien.

### 2. La serif appartient à la fiction

Deux familles, deux registres. L'interface — navigation, boutons, badges, formulaires — est en Inter. Le corps de fiction — récit, descriptions, dialogues — est en serif, et **son italique porte du sens** : elle marque la description narrative, elle ne sert pas à mettre un mot en valeur.

Jamais de serif dans le chrome, jamais d'Inter dans la narration.

### 3. La mise en page réagit au conteneur, pas à la fenêtre

La responsivité passe par `@container`, pas par `@media`. Un composant doit rendre pareil qu'il soit testé seul dans une fenêtre de 375 px ou placé dans une colonne de 375 px. Les tailles de texte fluides sont exprimées en `cqi` — hors d'un conteneur nommé, elles ne se résolvent pas.

---

## Accessibilité — ce qui est vérifié

- Focus visible sur tout élément focusable, en indigo (pas en crimson : la couleur d'action et la couleur de focus ne doivent pas se confondre)
- Cibles tactiles d'au moins 44 px
- `prefers-reduced-motion` annule toutes les durées, au niveau des tokens et non composant par composant
- Le vert vif de disponibilité ne porte jamais de texte : son contraste sur fond clair est de 1,6:1. Un vert assombri lui est substitué pour tout glyphe
- Aucun emoji comme icône, puce ou pastille d'état

Trois contrastes restent sous le seuil AA et sont **assumés et documentés** dans la charte, pas ignorés : le gris atténué, le crimson en texte, et le blanc sur crimson.

---

## État actuel

Le contrat est en version 1.0.0, mais **n'est pas encore figé** : le code consomme des noms d'utilitaires (`text-muted`, `bg-crimson`) antérieurs au contrat, qui ne correspondent à aucun de ses groupes. Tant que cette divergence existe, un linter tournerait sans rien vérifier.

La migration est planifiée : `aidd_docs/tasks/2026_07/2026_07_14-design-contract-namespace-migration.md`. Avant qu'elle n'ait eu lieu, écrire `text-semantic-muted` dans un template ne produit aucun style — se référer à la table de correspondance de `aidd_docs/memory/internal/DESIGN.md`.

Restent ouverts, et arbitrés nulle part : le choix de la fonte serif (Fraunces, cible de la maquette, contre Fraunces, déjà self-hostée), le nombre de jeux d'icônes, et le passage effectif aux requêtes de conteneur.
