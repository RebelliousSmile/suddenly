# Audit de conception — Suddenly

**Date** : 2026-04-05
**Statut** : Findings documentes, **4 decisions validees**

---

## 1. Deal breakers

### DB-1 : Double API (DRF JSON vs HTMX HTML) — BLOQUANT

Le projet a deux patterns de vues incompatibles :

| Module | Pattern | Retourne |
|--------|---------|----------|
| `users/views.py` | Django ClassViews | HTML |
| `characters/views.py` | DRF ViewSets | JSON |
| `games/views.py` | DRF ViewSets | JSON |

Les wireframes et les 16 composants template supposent des **partials HTML via HTMX**.
Les ViewSets DRF retournent du **JSON**. Personne ne sert de partials HTML
depuis `characters/` ou `games/`.

**Decision DA-1 : HTMX-first** — VALIDEE le 2026-04-05

Vues Django classiques pour le front (partials HTML via HTMX).
DRF conserve uniquement pour l'API publique (AP, OpenAPI, clients externes).
Les ViewSets DRF existants ne sont pas supprimes mais ne servent pas le front.

### DB-2 : God module characters/models.py — HAUTE

8 modeles, 4 domaines metier, 1 fichier, 1 migration geante.

**Decision DA-2 : Split en 4 fichiers** — VALIDEE le 2026-04-05

Splitter en 4 fichiers dans `characters/models/` :
- `character.py` : Character, CharacterAppearance
- `quote.py` : Quote, QuoteVisibility
- `link.py` : LinkRequest, CharacterLink, SharedSequence, LinkType, LinkRequestStatus
- `social.py` : Follow

Avec un `__init__.py` qui re-exporte tout (pas de breaking change sur les imports).
Ne pas deplacer vers des apps separees maintenant — trop de risque sur les migrations.

### DB-3 : Cles privees AP en clair en base — HAUTE

`Character.private_key` et autres `TextField` contiennent des cles RSA PEM en clair.

**Recommandation** : Utiliser `django-fernet-fields` ou chiffrer manuellement
avec une cle derivee de `SECRET_KEY`. Alternatif : stocker les cles dans des
fichiers (comme la cle d'instance, ADR-018) mais ca ne scale pas avec N acteurs.

### DB-4 : Pas de modele Notification — HAUTE

9 types de notifications dans les wireframes, 0 modele en base.

**Recommandation** : Creer un modele `Notification` dans `core/` ou un nouveau `notifications/` :
```
Notification(BaseModel):
    recipient: FK(User)
    type: CharField (link_request, link_accepted, link_rejected, new_report,
                     recommendation, mention, invitation, new_follower,
                     shared_sequence, revocation)
    actor: FK(User, null)  # qui a declenche
    target_content_type: FK(ContentType)  # quoi
    target_object_id: UUIDField
    message: TextField
    is_read: BooleanField(default=False)
    created_at: DateTimeField
```

### DB-5 : SharedSequence trop simple pour l'editeur collaboratif — HAUTE

Le modele a juste `title`, `content`, `status`. Pour US-18/19, il manque :
- Historique des modifications (ou integration CRDT)
- Dernier editeur par section
- Workflow de validation (proposer publication, accepter/refuser, commentaire)

**Recommandation** : Pour le MVP, ne PAS implementer d'editeur collaboratif temps reel.
Utiliser un **editeur asynchrone** (chacun son tour, comme un Google Doc sans curseur live) :
- Ajouter `last_edited_by: FK(User)` + `last_edited_at: DateTimeField`
- Ajouter `publication_proposed_by: FK(User, null)` + `publication_proposed_at`
- Le polling de presence (`Alpine.data('presence')`) suffit pour voir qui est "en ligne"
- Le verrouillage pessimiste (pas d'edition simultanee) evite les conflits

Un editeur CRDT (Yjs) est une feature post-MVP.

---

## 2. Problemes d'architecture

### AR-1 : GenericForeignKey sur Follow

Pas de contrainte FK en base, pas de `select_related`, N+1 garanti sur le feed.

**Recommandation** : Remplacer par 3 FK nullables avec contrainte CHECK.
Ou accepter et documenter le trade-off (simplicite du code vs performance).

### AR-2 : Champs AP dupliques sur chaque modele

6 champs AP (remote, ap_id, inbox_url, outbox_url, public_key, private_key) x 4 modeles.

**Recommandation** : Creer un mixin `ActivityPubActorMixin` (abstract) dans `core/mixins.py`.
Les modeles Character, User (via composition), Game heritent du mixin.
Quote et Report n'ont besoin que de `remote` + `ap_id` -> un mixin plus leger `ActivityPubObjectMixin`.

### AR-3 : 9 TODO non traces dans le code

| Fichier | Ligne | TODO |
|---------|-------|------|
| `characters/services.py` | 132-133 | Send notification + AP Offer |
| `characters/services.py` | 210-211 | Send AP Accept + notify |
| `characters/services.py` | 228-229 | Send AP Reject + notify |
| `characters/views.py` | 187 | Send AP Offer(Claim) |
| `characters/views.py` | 215 | Send AP Offer(Adopt) |
| `characters/views.py` | 247 | Send AP Offer(Fork) |
| `characters/views.py` | 344 | Send AP Accept(Offer) |
| `characters/views.py` | 374 | Send AP Reject(Offer) |
| `games/views.py` | 164 | Send AP Create(Note) |

Tous concernent l'envoi d'activites AP. Couverts par la tache 25 du master plan.

### AR-4 : Celery configure mais jamais appele

`settings/base.py` configure Celery Beat (2 taches). `activitypub/tasks.py` existe.
Mais les vues n'appellent jamais `deliver_activity.delay()`.

### AR-5 : Namespace AP `suddenly:` non documente

Les serializers AP utilisent un namespace custom non documente.
Les autres instances Suddenly doivent le connaitre pour interoperer.

**Recommandation** : Creer un ADR-022 documentant le namespace + publier une spec.

---

## 3. Problemes de securite

### SE-1 : SECRET_KEY a une valeur par defaut

Connu, dans le master plan (tache 5). A corriger en priorite.

### SE-2 : Pas de rate limiting sur les vues front

L'inbox AP a du rate limiting. Les vues login, signup, API REST n'en ont pas.

**Recommandation** : Ajouter `django-ratelimit` sur :
- Login : 10/min
- Signup : 5/min
- API : 1000/h par user
- Follow/Unfollow : 30/min

### SE-3 : Actor URL non validee contre le domaine d'origine

Un acteur `https://evil.com/users/alice` pourrait pretendre venir de `trusted.social`
si la signature est valide (cle volee). La validation domaine (tache 5) n'est pas faite.

### SE-4 : Pas de dedup inbox (ProcessedActivity)

Mentionne dans l'audit secu mais pas implemente. Un replay d'activite AP
est traite 2 fois.

---

## 4. Problemes de coherence donnees

### CD-1 : Character n'herite pas de BaseModel — CONNU

Tache 2 du master plan. Game et Report non plus.

### CD-2 : ReportCast -> CharacterAppearance non teste

La conversion a la publication (creation de PNJ a la volee, creation d'apparitions)
n'a pas de tests. Un echec silencieux est possible.

### CD-3 : LinkRequest n'a pas de statut QUEUED

Les wireframes et l'US-15 decrivent une file d'attente avec statut QUEUED.
Le modele n'a que PENDING/ACCEPTED/REJECTED/CANCELLED. Il manque QUEUED et EXPIRED.

**Recommandation** : Ajouter les statuts au TextChoices :
```python
QUEUED = 'queued', 'En file d'attente'
EXPIRED = 'expired', 'Expiree'
```

### CD-4 : Pas de champs CW et visibility sur Report

US-29, US-30 dans le master plan (tache 7) mais pas encore dans le schema.

### CD-5 : ADR-011 (lien pending jusqu'a SharedSequence publiee) pas implemente

L'ADR dit que le Character reste NPC jusqu'a publication de la SharedSequence.
Le code dans `LinkService.accept_request()` change le statut immediatement
a l'acceptation. **Le code contredit l'ADR.**

**Recommandation** : Soit modifier le code pour suivre l'ADR, soit mettre a jour
l'ADR pour reflettre le comportement actuel. A discuter avec le product owner.

---

## 5. Estimations du master plan challengees

| Tache | Estimation MP | Estimation reelle | Raison |
|-------|--------------|-------------------|--------|
| T7 (CW + visibility) | 2h | **4h** | Impact sur serializers AP, filtres feed, tests |
| T9 (profil) | 3h | **5h** | Followers/following listes, champs custom, migration badge = 3 vues supplementaires |
| T16 (links flow guide) | 5h | **8h** | Flow 2 etapes en modal, QUEUED, revocation avec grace period, renonciation |
| T17 (SharedSequence) | 4h | **2h** si asynchrone, **20h+** si collaboratif temps reel | Decision architecturale DB-5 critique |
| T18 (feed 3 onglets) | 5h | **8h** | 3 querysets distincts, recommandation, invitation, CW repliable |
| T25 (AP sortant) | 4h | **6h** | Announce, CW/visibility, Move activity |

---

## 6. Actions recommandees — par ordre

| Priorite | Action | Effort | Bloque |
|----------|--------|--------|--------|
| **1** | **Decider DRF vs HTMX** (DB-1) — recommande : HTMX-first + DRF API publique | Decision | Toutes les taches P2 |
| **2** | **Ajouter QUEUED + EXPIRED** a LinkRequestStatus (CD-3) | 15 min | T16 (links) |
| **3** | **Resoudre ADR-011 vs code** (CD-5) — confirmer le comportement voulu | Decision | T16, T17 |
| **4** | **Decider SharedSequence sync vs async** (DB-5) | Decision | T17 |
| **5** | **Documenter namespace AP** (AR-5) — ADR-022 | 1h | T25 |
| **6** | **Creer modele Notification** (DB-4) | 2h | T22 |
| **7** | **Splitter characters/models.py** (DB-2) | 2h | Rien (refactoring) |
| **8** | **Chiffrer cles privees** (DB-3) | 2h | Rien (securite) |
