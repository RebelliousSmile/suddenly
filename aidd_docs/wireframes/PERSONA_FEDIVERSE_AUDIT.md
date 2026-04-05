# Audit persona — Utilisatrice du Fediverse

## La persona

**Mia** — 32 ans, developpeuse web, joueuse de Blades in the Dark.

- Sur Mastodon depuis 2019 (instance `social.coop`)
- Utilise aussi BookWyrm et Lemmy
- A deja migre son compte Mastodon 2 fois
- Suit ~200 comptes sur le Fediverse, dont 30 joueurs de JDR
- Ses reflexes : timeline Local pour decouvrir, Home pour son fil, CW systematique sur le contenu NSFW, hashtags pour chercher du contenu
- Ses attentes : **une app federee qui se comporte comme une app federee**

---

## Audit wireframe par wireframe

### 01-layout.md — Header

> Mia : "Ou est le lien vers la timeline locale ? Sur Mastodon, j'ai
> Home/Local/Federated en permanence dans la sidebar. Ici je ne vois que
> 'Accueil' et 'Explorer'. Si 'Accueil' c'est ma Home, ou est ma Local ?
> Il faut que je clique sur 'Explorer' a chaque fois ?"

**Verdict** : Le header ne rend pas la navigation entre portees evidente.
Les onglets sont dans le feed mais pas dans la nav principale.

**Proposition** : Remplacer "Accueil" par des sous-liens ou un mega-menu :

```
| Fil [v]  Explorer  Mes parties  Mes persos  ...
|  |
|  +-- Abonnements
|  +-- Mon instance
|  +-- Fediverse
```

Ou plus simple : l'item "Fil" dans le header mene a `/feed/` qui a deja
les 3 onglets. Mais le header doit indiquer quelle portee est active.

---

### 02-home.md — Page d'accueil

> Mia : "La home pour les visiteurs ne mentionne pas que c'est federe
> avant la toute derniere section 'Federation ActivityPub'. C'est une
> feature majeure, ca devrait etre dans le hero. Et ou est l'adresse
> de l'instance ? Sur Mastodon, la landing page affiche le nom de
> l'instance, sa description, et un apercu de la timeline locale."

**Verdict** : L'identite d'instance est absente de la home.

**Proposition** : Le hero visiteur devrait inclure :
- Le nom de l'instance (pas seulement "Suddenly")
- Sa description personnalisee par l'admin
- Un apercu de la timeline locale (pas juste "activite recente")
- Un lien "A propos de cette instance"

---

### 03-auth.md — Signup

> Mia : "Quand je m'inscris sur une instance Mastodon, je vois les
> regles de l'instance et je dois les accepter. Ici, rien. Pas de
> regles, pas de mention des conditions d'utilisation, pas de lien
> vers la politique de moderation. Je ne sais pas sur quelle instance
> je suis ni ce qu'on attend de moi."

**Verdict** : Le signup ne contextualise pas l'instance.

**Proposition** : Ajouter au formulaire d'inscription :
- Nom de l'instance + description en en-tete
- Regles de l'instance (obligatoire, checkbox d'acceptation)
- Lien vers politique de moderation

---

### 04-profile.md — Profil

> Mia : "Ou sont mes compteurs followers/following ? Sur Mastodon c'est
> la premiere chose que je regarde. Et mes champs personnalises (pronoms,
> site web, liens verifies) ? L'adresse ActivityPub est la mais elle
> devrait etre copiable en un clic. Et si quelqu'un a migre son compte,
> ou est l'indication ?"

**Verdict** : Le profil est incomplet pour le Fediverse.

**Propositions** :
- Ajouter compteurs followers / following (cliquables -> listes)
- Ajouter champs personnalises (4 champs libres label/valeur, comme Mastodon)
- Bouton "Copier l'adresse" a cote de `@alice@suddenly.social`
- Badge "Compte migre vers @alice@new.instance" si applicable
- Date d'inscription

---

### 06-reports.md — Comptes-rendus

> Mia : "Pas de Content Warning ? Les CR de JDR peuvent contenir de la
> violence, du contenu mature, des themes sensibles. Sur Mastodon,
> je mets toujours un CW. Ici le CR est publie sans aucun avertissement.
> Et il n'y a pas de choix de visibilite : est-ce que mon CR est public,
> visible seulement par mes followers, ou unlisted ?"

**Verdict** : Les CRs n'ont ni CW ni scoping de visibilite.

**Propositions** : Ajouter a l'editeur de CR :
- Champ "Avertissement de contenu" (optionnel, texte libre)
  Si rempli, le CR est masque derriere un bouton "Afficher" dans le feed
- Selecteur de visibilite :

```
(globe) Public       — visible par tous, federe, dans les timelines
(unlock) Non-liste   — visible par lien direct, pas dans les timelines
(lock) Abonnes       — visible uniquement par mes followers
```

---

### 07-characters.md — Personnages

> Mia : "Les onglets Instance/Fediverse sur la liste c'est bien. Mais
> quand je suis sur la fiche d'un personnage distant, le message
> 'Les interactions passent par ActivityPub' est anxiogene. Dites-moi
> plutot ce que JE PEUX faire : suivre, lier, voir ses CRs. Et si
> je veux copier son adresse ActivityPub pour le partager sur Mastodon ?"

**Verdict** : Le message pour les acteurs distants est technique au lieu
d'etre actionable.

**Proposition** : Remplacer le status_banner distant par :

```
+------------------------------------------------------------------+
|  (globe) Personnage sur suddenly.games                           |
|  Vous pouvez le suivre, envoyer une demande de lien,            |
|  et voir ses comptes-rendus publics.                              |
|  [Copier l'adresse AP]                                           |
+------------------------------------------------------------------+
```

---

### 08-quotes.md — Citations

> Mia : "La visibilite Publique/Privee/Ephemere c'est bien mais
> c'est pas le meme vocabulaire que le reste du Fediverse. Sur
> Mastodon c'est Public/Unlisted/Followers-only/Direct.
> Et les citations publiques sont federees comme des Notes —
> est-ce qu'il y a un CW possible dessus aussi ?"

**Verdict** : La visibilite des citations utilise un vocabulaire specifique
a Suddenly (Ephemere) qui n'a pas d'equivalent Fediverse direct. C'est OK
car c'est un concept propre au produit. Mais il manque le CW.

**Proposition** : Ajouter un champ CW optionnel sur les citations publiques.

---

### 10-feed.md — Fil d'actualite

> Mia : "Les 3 onglets Abonnements/Instance/Fediverse, enfin ! C'est
> exactement ce qu'il faut. Mais il manque les boosts. Si @alice boost
> le CR de @bob, je veux le voir dans mon fil avec '@alice a partage'.
> Sans ca, la decouverte de contenu est cassee — c'est LE mecanisme
> de viralite du Fediverse."

**Verdict** : L'absence de boost/reblog est un **deal breaker federation**.

**Proposition** : Ajouter l'action "Partager" comme un boost ActivityPub :
- Bouton (repeat) sur chaque CR dans le feed
- Le CR booste apparait dans le fil des followers avec
  "@alice a partage" au-dessus
- Activite AP : Announce(Article)

```
+------------------------------------------------------------+
|  (repeat) @alice a partage                    il y a 30min |
|  +------------------------------------------------------+  |
|  | @bob dans Ironsworn · Jour 47 : La forge silencieuse  |  |
|  | ...                                                    |  |
|  +------------------------------------------------------+  |
+------------------------------------------------------------+
```

---

### 11-notifications.md — Notifications

> Mia : "Il manque 'X a partage votre CR' (boost) et 'X vous a
> mentionne dans un CR' (@mention cross-instance). Ce sont les
> deux notifications les plus frequentes sur Mastodon apres les
> follows et les likes."

**Proposition** : Ajouter 2 types de notifications :

| Type | Icone | Declencheur |
|------|-------|-------------|
| Partage (boost) | `i-lucide-repeat` | Quelqu'un a partage votre CR |
| Mention | `i-lucide-at-sign` | Quelqu'un vous a mentionne dans un CR |

---

### 14-federation.md — Federation

> Mia : "La page de recherche federee est bien. Mais la resolution
> WebFinger devrait aussi fonctionner quand je colle une URL de profil
> Mastodon, pas seulement le format @user@instance. Et les resultats
> Mastodon devraient clairement indiquer que c'est un compte Mastodon,
> pas un compte Suddenly — on ne peut pas lier de personnages avec."

**Proposition** : Indiquer le type de logiciel de l'instance dans les
resultats federes :

```
| @alice@suddenly.games  (dice) Suddenly  · [Suivre] [Lier possible] |
| @frank@mastodon.social (mastodon) Mastodon · [Suivre]              |
                                                ^^^^^^ pas de "Lier"
```

---

### 15-settings.md — Parametres

> Mia : "La section Federation est bien mais il manque :
> - Export de ma liste de followers/following (CSV, comme Mastodon)
> - Import de follows depuis une autre instance
> - Mes comptes bloques (pas seulement instances, mais utilisateurs)
> - Alias de compte pour la migration entrante
> Ca, c'est le minimum pour migrer. Je ne m'inscrirai pas sur une
> instance ou je ne peux pas partir facilement."

**Propositions** :
- Export/import CSV de followers (Mastodon-compatible)
- Liste de comptes bloques/mutes (distinct des instances)
- Alias de compte pour migration entrante
- Historique des migrations

---

### 16-misc.md — Onboarding

> Mia : "L'etape 2 me propose de suivre des joueurs locaux. C'est bien.
> Mais proposez-moi aussi d'importer mes follows si je migre depuis
> une autre instance. Et montrez-moi la timeline locale tout de suite
> — c'est comme ca que je decouvre une communaute."

**Proposition** : Ajouter a l'etape 2 :
- "Vous migrez d'une autre instance ? [Importer vos follows]"
- Apercu de la timeline locale integre

---

## Synthese — Deal breakers identifies par Mia

| # | Manque | Severite | Impact |
|---|--------|----------|--------|
| 1 | **Pas de boost/reblog** | **CRITIQUE** | La decouverte de contenu est cassee. Sans boost, le contenu ne se propage pas entre instances. |
| 2 | **Pas de visibilite sur les CRs** (public/unlisted/followers-only) | **CRITIQUE** | Les joueurs ne peuvent pas controler qui voit leur contenu. Incompatible avec les attentes Fediverse. |
| 3 | **Pas de Content Warning** | **HAUTE** | Le contenu JDR peut etre sensible. Sans CW, pas de consentement eclaire. |
| 4 | **Pas de compteurs followers/following** sur les profils | **HAUTE** | Signal social de base absent. |
| 5 | **Pas d'import/export de follows** | **HAUTE** | Bloque la migration, qui est un droit fondamental du Fediverse. |
| 6 | **Pas de page "A propos" de l'instance** | **MOYENNE** | L'identite d'instance n'est pas communiquee aux visiteurs. |
| 7 | **Pas de regles d'instance au signup** | **MOYENNE** | Pas de contrat social a l'inscription. |
| 8 | **Pas de hashtags** | **MOYENNE** | Mecanisme de decouverte cross-instance absent. |
| 9 | **Pas d'indication de type de logiciel** dans les resultats federes | **BASSE** | Confusion entre instances Suddenly et Mastodon. |
| 10 | **Pas de comptes bloques/mutes utilisateur** | **MOYENNE** | Seulement instance-level dans les settings. |

---

## Wireframes a creer ou modifier

| Action | Wireframe | Contenu |
|--------|-----------|---------|
| **CREER** | `17-instance-about.md` | Page /about : description, regles, stats, admin, logiciel, federation |
| **MODIFIER** | `03-auth.md` | Signup : ajouter regles d'instance + checkbox acceptation |
| **MODIFIER** | `04-profile.md` | Ajouter followers/following, champs custom, badge migration, copier AP |
| **MODIFIER** | `06-reports.md` | Editeur : ajouter CW + selecteur visibilite (public/unlisted/followers) |
| **MODIFIER** | `08-quotes.md` | Ajouter CW optionnel sur citations publiques |
| **MODIFIER** | `10-feed.md` | Ajouter boost/partage dans les feed items + notification boost |
| **MODIFIER** | `11-notifications.md` | Ajouter types boost et mention |
| **MODIFIER** | `14-federation.md` | Indiquer type logiciel dans resultats, accepter URLs en plus de @user@instance |
| **MODIFIER** | `15-settings.md` | Import/export follows CSV, comptes bloques, alias migration |
| **MODIFIER** | `16-misc.md` | Onboarding : option import follows + apercu timeline locale |
