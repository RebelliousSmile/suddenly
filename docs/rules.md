# Rules — Suddenly

Principes, philosophie et règles de coding qui guident toutes les décisions du projet.

---

## Philosophie du Fédiverse

### Décentralisation avant tout

Aucune instance ne doit dépendre d'une autre pour fonctionner.

- [ ] L'application démarre et fonctionne sans connexion à une autre instance
- [ ] Aucune logique métier n'appelle une API externe obligatoire au fonctionnement de base
- [ ] La modération est locale — aucune décision ne vient d'un serveur central
- [ ] Une instance peut bloquer/débloquer d'autres instances indépendamment

### Interopérabilité

Suddenly doit parler à tout acteur ActivityPub conforme (Mastodon, Pleroma, Misskey…).

- [ ] Les activités envoyées respectent le standard ActivityPub sans extensions obligatoires
- [ ] Les extensions custom ont un fallback standard si l'instance distante ne les comprend pas
- [ ] Une activité entrante inconnue est ignorée silencieusement, jamais rejetée avec erreur
- [ ] Permissif en lecture (accepter des formats légèrement non conformes), strict en écriture (Postel's Law)

### Souveraineté des utilisateurs

Les utilisateurs possèdent leurs données.

- [ ] Export des données possible à tout moment (profil, personnages, CRs, citations)
- [ ] Contenu fédéré jamais supprimé définitivement — soft delete obligatoire
- [ ] La migration de compte vers une autre instance ne casse pas les liens existants
- [ ] Le contenu est privé par défaut jusqu'à publication explicite

### Open Source & Contributions

Le code doit être accessible à un développeur Python moyen.

- [ ] Un nouveau contributeur peut comprendre un fichier sans lire tout le codebase
- [ ] La barrière à l'entrée est minimale — pas de stack complexe obligatoire pour contribuer
- [ ] Chaque décision non évidente est documentée (le POURQUOI, pas le QUOI)
- [ ] Pas de dépendance à des outils propriétaires ou payants dans le workflow de base

---

## Principes de Développement

### KISS — Keep It Simple, Stupid

La solution la plus simple qui répond au besoin est la bonne.

- [ ] La solution peut être expliquée en une phrase à un développeur junior
- [ ] Aucun design pattern utilisé sans que le problème qu'il résout soit identifié
- [ ] Si le code a besoin d'un commentaire pour être compris, le réécrire
- [ ] Préférer 100 lignes lisibles à 30 lignes ingénieuses

### YAGNI — You Aren't Gonna Need It

Ne pas implémenter ce qui n'est pas encore requis.

- [ ] Chaque ligne de code répond à un besoin exprimé, pas hypothétique
- [ ] Pas d'abstraction créée pour un seul usage
- [ ] Le code mort est supprimé immédiatement, pas commenté
- [ ] Les fonctionnalités "pour plus tard" sont des issues GitHub, pas du code

### DRY — Don't Repeat Yourself

Une logique n'existe qu'à un seul endroit.

- [ ] La même logique n'est pas copiée-collée — extraire à la troisième occurrence
- [ ] Une modification métier ne nécessite qu'un seul changement dans le code
- [ ] DRY s'applique à la logique, pas aux templates ni aux configurations qui peuvent légitimement se ressembler

### Fail Fast

Valider tôt, rejeter explicitement.

- [ ] Les entrées invalides sont rejetées à la frontière du système, pas au fond de la logique
- [ ] Une erreur de configuration empêche le démarrage de l'application
- [ ] Chaque exception lève un type explicite avec un message clair
- [ ] `except: pass` et `except Exception` génériques sont interdits

---

## Règles de Coding

### Clarté des noms

- [ ] Le nom révèle l'intention sans commentaire supplémentaire
- [ ] Pas de noms génériques : `data`, `info`, `tmp`, `obj`, `result`, `thing` sont interdits
- [ ] Les booléens sont préfixés : `is_`, `has_`, `can_`, `should_`
- [ ] Les fonctions sont nommées avec un verbe : `get_`, `create_`, `send_`, `validate_`

### Limites de taille

- [ ] Fonction : maximum **50 lignes** (idéalement < 20) — si plus, découper
- [ ] Fichier : maximum **500 lignes** — si plus, extraire un module
- [ ] Paramètres : maximum **5** par fonction — si plus, utiliser un dataclass
- [ ] Indentation : maximum **3 niveaux** — si plus, extraire une fonction

### Commentaires

- [ ] Le commentaire explique le POURQUOI, jamais le QUOI
- [ ] Pas de commentaire qui paraphrase le code (`# increment i` sur `i += 1`)
- [ ] Les TODO en code sont convertis en issues GitHub avant merge
- [ ] Les blocs commentés (`# old code`) sont supprimés, pas conservés

### Gestion d'erreurs

- [ ] Chaque exception est spécifique au domaine (`CharacterNotFoundError`, non `Exception`)
- [ ] L'erreur est gérée au niveau qui a le contexte pour la traiter
- [ ] Les erreurs inattendues sont loggées avec suffisamment de contexte pour déboguer
- [ ] Les erreurs attendues (validation, permission) retournent un message utilisateur lisible

### Sécurité

- [ ] Toute donnée externe (instance distante, input utilisateur) est validée avant usage
- [ ] Aucun secret dans le code — uniquement via variables d'environnement
- [ ] Les HTTP Signatures sont vérifiées avant tout traitement d'activité AP
- [ ] Les requêtes SQL passent uniquement par l'ORM — pas de `.raw()` sans review

---

## Règles de Fédération

### Confiance entre instances

Une instance distante est toujours considérée potentiellement compromise.

- [ ] HTTP Signatures vérifiées sur toutes les activités entrantes, sans exception
- [ ] Le domaine de l'acteur est validé contre le domaine de l'expéditeur HTTP
- [ ] Les activités sont dédupliquées par `ap_id` — recevoir deux fois = même résultat
- [ ] Les clés publiques sont mises en cache localement pour éviter le refetch systématique

### Traitement des activités

- [ ] Chaque handler d'activité est idempotent
- [ ] Les activités inconnues sont ignorées sans erreur (forward compatibility)
- [ ] La délivrance d'activités sortantes est toujours asynchrone (jamais en request/response)
- [ ] Toute activité entrante est loggée pour audit

### Respect des autres instances

- [ ] Rate limiting sur les envois pour ne pas spammer les inboxes distantes
- [ ] Utiliser `sharedInbox` quand disponible pour réduire la charge réseau
- [ ] Un `Reject` de l'instance distante est respecté sans retry automatique
- [ ] Une instance qui bloque la nôtre n'est pas contournée

---

## Règles de Tests

### Priorités (70/20/10)

- [ ] **70%** — Analyse statique : `mypy --strict`, `ruff check`, `black --check` passent
- [ ] **20%** — Tests contrats sur Claim/Adopt/Fork, signatures HTTP, transitions de statut Character
- [ ] **10%** — Tests E2E sur publication CR et flux Adopt complet uniquement

### Ce qu'on teste

- [ ] Toute logique métier qui peut être incorrecte (services, validators)
- [ ] Les cas limites et erreurs attendues (NPC déjà claimed, signature expirée...)
- [ ] Les transitions d'état : NPC → CLAIMED / ADOPTED / FORKED
- [ ] Les signatures cryptographiques : valide, invalide, expirée, header manquant

### Ce qu'on ne teste pas

- [ ] Le framework Django (ORM, auth, admin)
- [ ] Les vues CRUD sans logique propre
- [ ] Le rendu des templates
- [ ] Les migrations

### Règles

- [ ] Jamais de mock sur un composant fonctionnel — tester le vrai comportement
- [ ] Écrire le test qui reproduit le bug avant de le corriger
- [ ] Chaque test est isolé (`@pytest.mark.django_db`, rollback automatique)
- [ ] Vérifier qu'un test peut échouer — un test qui passe toujours ne teste rien

---

## Règles Git & Contribution

### Commits

Format : `type(scope): description courte en impératif`

- [ ] Un commit = une intention cohérente, pas un dump de travail accumulé
- [ ] Le message décrit ce que le commit accomplit, pas ce qu'il modifie
- [ ] Pas de commit `WIP`, `fix`, `update` sans description sur `main`
- [ ] Les tests passent avant chaque commit
- [ ] Pas de nom d'auteur, de copyright, de signature ni de `Co-authored-by` dans le message de commit
- [ ] Maximum 5 points dans le corps du message — si plus, regrouper et synthétiser

### Pull Requests

- [ ] Une PR = une fonctionnalité ou un correctif cohérent
- [ ] La PR est compréhensible sans contexte oral (description suffisante)
- [ ] Toute PR modifiant l'API ActivityPub documente l'impact sur la compatibilité Mastodon
- [ ] Les tests passent et l'analyse statique est propre avant de demander une review
