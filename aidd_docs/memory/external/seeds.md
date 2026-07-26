# Seeds — peupler la base locale

Guide de la commande `seed_demo`, qui remplit l'instance de développement avec un jeu de contenu bilingue, images comprises.

**Difficulté** : Débutant
**Temps estimé** : 2-3 minutes (dont ~1 min de génération d'images)
**Prérequis** : instance locale démarrée (`make docker-up`), migrations appliquées

---

## À quoi ça sert

Une base vide ne dit rien de l'application : ni la pagination, ni l'infinite scroll, ni les filtres de langue, ni le cœur du produit (un PNJ qui devient le PJ d'un autre joueur) ne sont visibles tant qu'il n'y a pas de volume. `seed_demo` produit ce volume, avec des états variés et cohérents plutôt qu'une soupe de `lorem ipsum`.

Le seed est **réservé au développement local**. Il refuse de s'exécuter si `DEBUG=False`.

---

## Utilisation

```bash
make docker-seed          # peuple la base
make docker-seed-flush    # supprime tout le contenu de démo
```

Ou directement, pour passer des options :

```bash
docker compose -f docker-compose.dev.yml exec web \
  python manage.py seed_demo --users 60 --games 40 --reports 800
```

### Options

| Option | Défaut | Effet |
|--------|--------|-------|
| `--users` | 30 | Nombre de joueurs |
| `--games` | 20 | Nombre de parties |
| `--reports` | 400 | Nombre total de comptes-rendus (répartis sur les parties) |
| `--characters-per-game` | 10 | Personnages par partie (⅓ de PJ, ⅔ de PNJ) |
| `--seed` | 20260714 | Graine du générateur aléatoire — même graine, même jeu de données |
| `--no-images` | — | Saute avatars, couvertures et images de rapports (nettement plus rapide) |
| `--flush` | — | Supprime les données de démo, puis s'arrête |
| `--force` | — | Autorise l'exécution avec `DEBUG=False` |

---

## Se connecter avec les comptes générés

Le formulaire de connexion est servi par allauth : **<http://localhost:8000/accounts/login/>**.

| | |
|---|---|
| Identifiant | `demo_fr_000`, `demo_en_001`, `demo_fr_002`… |
| Mot de passe | `demo1234` (identique pour tous) |
| E-mail | `demo_fr_000@example.test` — accepté aussi comme identifiant |

`ACCOUNT_LOGIN_METHODS = {"username", "email"}` : le nom d'utilisateur **ou** l'e-mail fonctionnent. La vérification d'e-mail est en `optional`, donc aucune confirmation n'est requise malgré des adresses `@example.test` qui ne reçoivent rien.

**L'index est global, pas par langue.** Les indices pairs sont français, les impairs anglais : `demo_fr_000`, `demo_en_001`, `demo_fr_002`, `demo_en_003`… Il n'existe donc **pas** de `demo_fr_001`. Avec `--users 30`, les identifiants vont de `demo_fr_000` à `demo_en_029`.

**Aucun compte de démo n'est administrateur.** Ils sont créés sans `is_staff` ni `is_superuser` : ni `/admin/` (Django) ni `/gmh/` (panneau d'instance) ne leur sont accessibles. Pour cela, créez votre propre compte :

```bash
make docker-createsuperuser
```

### Choisir un compte selon ce qu'on veut voir

Les utilisateurs ne sont pas interchangeables — leurs préférences sont dérivées de leur index, précisément pour couvrir les cas de repli :

| Cas à exercer | Utilisateurs concernés |
|---|---|
| Repli sur les initiales (pas d'avatar) | index multiple de 5 : `demo_fr_000`, `demo_en_005`, `demo_fr_010`… |
| Repli sur la langue d'interface de l'instance (`interface_language` vide) | index multiple de 4 : `demo_fr_000`, `demo_fr_004`, `demo_en_009`… |
| Deux langues préférées (`["fr", "en"]`) | index multiple de 3 |
| Contenu non étiqueté masqué (`show_unlabeled_content = False`) | index multiple de 5 |
| Image de fond de personnage par défaut | index multiple de 7 |

`demo_fr_000` cumule les cas de repli (pas d'avatar, pas de langue d'interface, contenu non étiqueté masqué) — utile pour vérifier qu'aucun d'eux ne casse l'affichage.

---

## Ce qui est généré

Avec les valeurs par défaut :

| Entité | Volume | Détail |
|--------|--------|--------|
| Utilisateurs | 30 | Moitié `fr`, moitié `en` ; certains sans avatar, certains sans `interface_language` (pour tester le repli sur la langue de l'instance) |
| Parties | 20 | Systèmes variés, publiques et privées, avec ou sans couverture |
| Personnages | ~210 | PJ possédés et PNJ libres, plus les forks créés par les liens |
| Comptes-rendus | 400 | 200 `fr` / 200 `en`, brouillons et publiés, visibilités `public`/`unlisted`/`followers`, une partie `released` |
| Rapports | ~2800 | Fils narratifs enchaînés par `RapportLink`, tous types confondus |
| Images | ~430 | Avatars, couvertures, images de rapports |
| Abonnements | 240 | Vers des personnages et des parties |
| Liens | ~38 | Claims, adoptions et forks : certains en attente, d'autres acceptés, d'autres avec séquence partagée publiée |

### La langue

La langue est portée par **la campagne** : une partie est française ou anglaise, et ses comptes-rendus héritent de sa langue via `Report.language` (BCP-47). Le résultat est exactement équilibré, ce qui rend les filtres de langue et le `contentMap` ActivityPub testables sur des données réelles.

Les textes ne sont pas générés au hasard : narration, actions, dialogues et textes alternatifs des images existent dans les deux langues.

### Les images

Elles sont **générées procéduralement** (dégradé + initiales, en JPEG) plutôt que téléchargées : aucune dépendance réseau, aucun binaire versionné dans le dépôt. Elles pèsent ~4,7 Mo au total et atterrissent dans `MEDIA_ROOT` (`app/media/`).

Le rendu est **déterministe** : à graine égale, un personnage donné obtient toujours le même avatar. Les captures et les comparaisons visuelles restent donc stables d'un reseed à l'autre.

Toutes les entités n'ont pas d'image, volontairement — le repli sur les initiales doit être exercé lui aussi.

---

## Nettoyage

```bash
make docker-seed-flush
```

Le flush cible les utilisateurs `demo_*` et supprime leur contenu par cascade (parties, personnages, comptes-rendus, liens), ainsi que les tags devenus orphelins.

Il **supprime aussi les fichiers images sur le disque**. C'est nécessaire : Django met en cascade les lignes de la base, jamais les fichiers d'un `ImageField`. Sans ce nettoyage explicite, `MEDIA_ROOT` se remplirait d'orphelins à chaque reseed. Le ciblage passe par les relations aux utilisateurs `demo_*`, donc les médias que vous avez vous-même téléversés ne sont pas touchés.

---

## Points d'attention pour qui modifie la commande

**Le seed passe par les services, pas par l'ORM directement.** Les liens entre personnages sont créés via `LinkService` (`create_request` / `accept_request`) et les publications via `publish_report`. C'est la règle du domaine, et c'est aussi ce qui garantit que les états produits sont ceux que l'application sait réellement atteindre — statuts de personnages, `CharacterAppearance`, séquences partagées inclus. Ne pas court-circuiter en écrivant les statuts à la main.

**Les noms de personnages doivent être uniques.** `Character.save()` résout les collisions de slug en attrapant `IntegrityError` dans une boucle de réessai. Sous PostgreSQL, une `IntegrityError` avorte la transaction englobante : ce mécanisme ne peut donc pas fonctionner à l'intérieur du `transaction.atomic()` du seed. La commande garantit l'unicité en amont (`_unique_character_name`) au lieu de s'appuyer dessus.

**`clean()` n'est pas appelé par `.create()`.** Les invariants de `Rapport` (une narration ne prend jamais d'acteur ; une action ou un dialogue en exige un), de `RapportMarker` (les marqueurs de personnage exigent un personnage) et de `RapportMedia` (une image, sur un rapport `description` uniquement) doivent être respectés explicitement par le générateur. Après modification, il est prudent de les revérifier en base.

**Un second seed sans flush est refusé.** Les noms d'utilisateurs sont uniques ; la commande s'arrête avec un message clair plutôt que de planter au milieu d'une transaction.
