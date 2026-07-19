---
name: plan
description: Épique F (#136) — signalement d'utilisateurs & modération admin. Un utilisateur en signale un autre (motif + contexte optionnel scène/personnage/MP) ; l'admin d'instance voit une file de modération et bloque/ignore ; un utilisateur bloqué ne peut plus interagir (MP, réponses aux Offers, follows) — via un helper de blocage central `is_blocked(user)` consommé par les surfaces d'interaction ; le signalé n'est PAS notifié. Complément de D (auto-follow verrouillé → signalement = seule voie de recours).
objective: "Un utilisateur peut signaler un autre avec un motif (critère 1) ; l'admin voit la file des signalements en attente et peut bloquer/ignorer (critère 2) ; un utilisateur bloqué ne peut plus interagir — MP, Offers, follows — avec l'instance, local comme distant, via un helper de blocage central (critère 3) ; le signalé n'est PAS notifié du signalement (critère 4). `make check` passe."
success_condition: "make check && python -m pytest tests/core/test_moderation.py tests/activitypub/test_block_gating.py --create-db --no-cov -p no:cacheprovider -q"
iteration: 0
created_at: "2026-07-19T00:00:00Z"
plan_kind: simple
confidence: 8
---

<!-- AI INSTRUCTIONS ONLY — ne pas produire ce bloc. Amendements préfixés 🤖. Log append-only. -->

# Instruction : Signalement d'utilisateurs & modération admin — Épique F (#136)

## Feature

- **Summary** : Sur Suddenly, l'éjection d'une partie n'a **aucune force** (concept assumé) ; la seule voie de recours est le **signalement à l'admin d'instance**, qui peut **bloquer** l'utilisateur signalé. L'Épique F livre trois surfaces : (1) un utilisateur **signale** un autre (motif obligatoire + contexte optionnel : scène, personnage, MP) ; (2) l'admin voit une **file de modération** des signalements en attente et **bloque ou ignore** ; (3) le **blocage coupe les interactions** de l'utilisateur bloqué (MP, réponses aux Offers, follows) — via un **helper de blocage central** `is_blocked(user)`. L'admin est **notifié** (`core.Notification`) à chaque signalement ; le **signalé n'est jamais notifié**. Complément de l'Épique D (auto-follow verrouillé → le signalement devient la seule voie de recours).
- **Stack** : `Django 5.x (Python 3.12)`, `PostgreSQL`, `HTMX`, `Alpine.js`, `pytest-django`, `ruff`, `mypy`, `gettext`/`{% trans %}`.
- **Branch name** : `epic-f/reporting-moderation` (worktree `.claude/worktrees/epic-f` — l'implémenteur committe ici, jamais dans la copie de travail principale).
- **Parent Plan** : `none`
- **Sequence** : `standalone`
- Confidence : 8/10
- Time to implement : ~1,5 jour

## Hypothèses de dépendance (NE PAS re-planifier)

- **Épique C (#133) follow-federation = mergée sur main** (base du worktree, HEAD `77f21a9`). `characters.models.Follow` (polymorphe User/Character/Game, GFK), `follow_views.follow_toggle` (local) et `activitypub/inbox.py::handle_follow` (inbound fédéré) **existent** → ce sont les **seuls seams d'interaction câblables MAINTENANT**.
- **Épique B (#132, Offers) et Épique E (#135, MP) NON mergées.** Leurs surfaces (réponse à une Offer, envoi de MP) **n'existent pas dans ce worktree**. F **ne doit PAS** créer de code dans des modules inexistants ni se coupler à leur implémentation. F **fournit le contrat** `is_blocked(user)` que B et E **consommeront quand elles atterriront**. Voir DEC-F3 (isolation).
- **`core.Notification` + signaux** (`core/notification_signals.py`) : pattern maison de notification via post_save, réutilisé pour notifier l'admin (DEC-F5). Ne pas re-planifier l'infra Notification.

## Décision de découpage (plan simple, pas master)

- Frontière migration unique (Phase 1 : `UserReport` + champs `User` de blocage + `NotificationType`). Ensuite, service (Phase 2), UI (Phase 3), gating (Phase 4) sont livrables incrémentalement ; Phase 5 (tests batchés) valide les 4 critères.
- **Décidé : plan simple.** Le périmètre est cohésif (modèle ↔ service ↔ admin ↔ gating) et tient dans une frontière migration ; des child plans ajouteraient du couplage sans bénéfice. Le code compile à chaque frontière.

## Convention tests batchés + isolation DB (documenter pour l'implémenteur)

- **Phases 1-4 = CODE SEUL** : aucun test écrit. Chaque phase code se clôt par un run **ciblé des tests EXISTANTS** du périmètre (`python -m pytest <scope> --create-db --no-cov -p no:cacheprovider -q`) — jamais d'écriture de test. **Phase 5** écrit toute la couverture des 4 critères d'un coup, puis `make check`.
- **`--create-db` obligatoire sur tout pytest** : la DB de test est partagée entre worktrees, son schéma dérive (`--reuse-db` en retard sur une migration récente casse des tests hors périmètre).
- **Base dédiée `suddenly_epicf`, un run à la fois** : l'implémenteur exécute pytest avec `DATABASE_URL` inline pointant une base isolée, jamais via `make check` (qui, lui, tourne au moment du ship en Phase 5). Exemple :
  ```bash
  DATABASE_URL=postgres://suddenly:suddenly@localhost:5432/suddenly_epicf \
    python -m pytest <scope> --create-db --no-cov -p no:cacheprovider -q
  ```
- **i18n** : le wrapping `{% trans %}` / `gettext` **inline** est du **code** (fait dans les phases code). La traduction `.po` + `compilemessages` est **différée en Phase 5**.

## Existant confirmé (NE PAS re-planifier — déjà câblé)

Vérifié contre le code du worktree :

- **`core.models` porte déjà des modèles de modération partiels** : `ContentReport` (signalement de **contenu** générique via GFK, US-27 — **non câblé au front**, seulement enregistré dans Django admin), `UserBlock`/`UserMute` (blocage/mute **pair-à-pair**, US-33), `ReportCategory` (spam/harcèlement/inapproprié/autre), `Notification`/`NotificationType`. Ces modèles couvrent des concepts **différents** de #136 (cf. DEC-F1/F2 : ne pas les surcharger).
- **`User` (`users/models.py`)** : `is_admin` (BooleanField) ; `remote`/`ap_id`/`inbox_url` ; **aucun champ de ban instance** (`is_blocked` inexistant). `AbstractUser.is_active` existe mais gate le **login** (voir ligne suivante).
- **Suspension admin déjà présente (US-25)** : `admin_views.admin_user_suspend` pose `target.is_active = False` (ban login complet). C'est un **levier orthogonal** au blocage-interactions de #136 (DEC-F2). Un `is_active=False` ne gate PAS les interactions **fédérées** d'un compte distant (qui ne se logue jamais).
- **Infra admin custom `gmh:` (PAS Django admin)** : `core/admin_views.py` + `core/admin_urls.py` (`app_name="gmh"`), décorateur `@admin_required` (`core/decorators.py`, check `is_admin`), rendu HTMX `htmx_render`, templates `templates/gmh/*.html`. Contient déjà `admin_dashboard`, `admin_users`, `admin_user_suspend`, `admin_instances`/`admin_instance_block`. **C'est ici que vit la file de modération** (DEC-F4), cohérent avec le flux de suspension existant.
- **Seams d'interaction câblables MAINTENANT (C mergée)** :
  - **Follow local** : `characters/follow_views.follow_toggle` (`@require_POST @login_required`, HTMX).
  - **Follow inbound fédéré** : `activitypub/inbox.handle_follow` (l.215) — `get_or_create_remote_user(follower_id)` puis `Follow.objects.get_or_create(...)`. Point de gate pour un **compte distant bloqué**.
- **Notifications** : `core/notification_signals.py` — receivers post_save (`notify_on_link_request`, `notify_on_follow`, `notify_on_report_published`). Patron réutilisé pour notifier l'admin à la création d'un `UserReport` (DEC-F5). **Attention collision de libellé** : `NotificationType.NEW_REPORT` signifie « **nouveau compte-rendu** » (une scène publiée), **pas** un signalement → un **nouveau type** est requis.
- **Aucun `Flag` AP** : ni émission ni réception dans `activitypub/inbox.py`/`serializers.py`/`tasks.py` (grep `Flag`/`handle_flag` = vide). Base de DEC-F7.

## Manques identifiés (le périmètre réel de #136)

1. **Aucun modèle « signaler un utilisateur »** : `ContentReport` cible du contenu générique et n'a pas de notion « utilisateur signalé + contexte optionnel + file de traitement admin ». (→ DEC-F1, Phase 1)
2. **Aucun mécanisme de ban instance ni helper central** : rien pour marquer un utilisateur « bloqué » (distinct de `is_active`/`UserBlock`), rien qu'une surface d'interaction puisse interroger en O(1). (→ DEC-F2/F3, Phase 1/2)
3. **Aucune file de modération admin** : `gmh:` n'expose pas les signalements en attente ni les actions bloquer/ignorer. (→ DEC-F4, Phase 3)
4. **Aucune notification admin au signalement** ni type dédié ; risque de notifier le signalé. (→ DEC-F5/F6, Phase 2)
5. **Aucun gating d'interaction au blocage** : `follow_toggle`/`handle_follow` ne consultent aucun état de blocage. (→ DEC-F3, Phase 4)
6. **Compte distant signalé → AP `Flag`** : non tranché, aucune infra Flag. (→ DEC-F7, tranché : hors v1)

## Décisions de conception (DEC-Fx — prises, conservatrices)

### DEC-F1 — Modèle de signalement : nouveau `UserReport` (ne pas surcharger `ContentReport`)
- **Nouveau modèle `UserReport(BaseModel)` dans `suddenly.core`** :
  - `reporter` FK User (`related_name="user_reports_made"`).
  - `reported_user` FK User (`related_name="user_reports_received"`).
  - `category` CharField (réutiliser `ReportCategory` existant : spam/harcèlement/inapproprié/autre) — **motif obligatoire** (critère 1).
  - `comment` TextField `blank=True` — contexte libre.
  - **Contexte optionnel polymorphe** via GFK : `context_content_type` + `context_object_id` (`null=True, blank=True`) + `context` GenericForeignKey — pointe une scène (`games.Report`), un personnage (`characters.Character`) ou un MP (épique E, résolu au runtime — le GFK ne couple pas au code E). Optionnel : un signalement sans contexte reste valide.
  - `status` CharField TextChoices `pending`/`resolved`/`dismissed` (défaut `pending`) — pilote la file (critère 2).
  - `handled_by` FK User `null=True SET_NULL related_name="+"` ; `handled_at` DateTimeField `null=True`.
  - `Meta.indexes` : `(status, -created_at)` (file), `(reported_user, status)` (agrégation par cible). **Pas de `unique_together`** : re-signalement autorisé.
- **Justification** : `ContentReport` modélise « signaler une **pièce de contenu** » (US-27) via un GFK-cible unique ; #136 modélise « signaler une **personne** à l'admin, avec un **contexte** distinct de la cible ». Surcharger le GFK unique de `ContentReport` (cible = user, mais où mettre le contexte ?) est ambigu. Modèle dédié = sémantique nette, file de modération propre, aucune régression de l'usage `ContentReport` existant. **Alternative écartée** : réutiliser `ContentReport` (cible=User + second GFK contexte) — plus de couplage, sémantique confuse « content report » pour un signalement de personne. Aucune logique métier dans le modèle (règle `django-models`).

### DEC-F2 — Mécanisme de blocage central : flag `User.is_blocked` (distinct de `is_active` et de `UserBlock`)
- **Ajouter sur `User`** : `is_blocked` BooleanField (`default=False`, `db_index=True`), `blocked_at` DateTimeField (`null=True, blank=True`), `blocked_by` FK User (`null=True, blank=True, SET_NULL, related_name="+"`). C'est le **ban instance** de #136.
- **Trois leviers de modération orthogonaux, ne pas confondre** :
  - `UserReport` → signalement (données).
  - `User.is_active=False` → **suspension login** (US-25, `admin_user_suspend` **existant, inchangé**).
  - `User.is_blocked=True` → **ban interactions** (#136, nouveau). N'affecte **pas** `is_active` : un bloqué peut encore se connecter/consulter mais **ne peut plus interagir**. Fonctionne pour **local ET distant** (un compte distant a `is_active=True` et ne se logue jamais → seul `is_blocked` peut gater ses interactions fédérées).
- **Justification** : le helper `is_blocked(user)` gate des **chemins chauds** (chaque follow/MP/réponse à Offer) → un **flag dénormalisé O(1)** évite une jointure par interaction ; un modèle `Block` séparé imposerait une requête par appel. `blocked_at`/`blocked_by` donnent l'audit minimal sans table dédiée. **Nommage** : `is_blocked` (pas un modèle `Block`) pour **éviter la collision** avec le `UserBlock` pair-à-pair existant. **Alternative écartée** : réutiliser `is_active` pour le blocage — conflate login-ban et interaction-ban, et **ne gate pas** le distant fédéré.

### DEC-F3 — Helper central + isolation stricte de B/E non mergées **(décision structurante)**
- **Helper dans `suddenly.core`** (module `core/moderation.py` ou fonctions dans `core/services.py`), importable **sans** B/E :
  - `is_blocked(user) -> bool` : lit `getattr(user, "is_blocked", False)` (tolère un User distant miroir). **Contrat unique** consommé par toutes les surfaces d'interaction.
  - `block_user(user, *, by, report=None) -> None` : `is_blocked=True`, `blocked_at=now()`, `blocked_by=by` ; marque le `report` `resolved` si fourni. Idempotent.
  - `unblock_user(user) -> None` : `is_blocked=False`, reset audit.
  - `create_user_report(reporter, reported_user, category, comment="", context=None) -> UserReport`.
- **Câblage MAINTENANT (seams existants, C mergée)** — Phase 4 :
  - `characters/follow_views.follow_toggle` : refuser si `is_blocked(request.user)` **ou** cible bloquée (403 HTMX).
  - `activitypub/inbox.handle_follow` : après résolution du follower distant, **ne pas créer le Follow** si `is_blocked(follower)` (return early, best-effort log). Gate le **compte distant bloqué** (critère 3, volet fédéré).
- **Câblage DIFFÉRÉ (B/E non mergées) — NE PAS coder maintenant** :
  - **MP (épique E, #135)** : au point d'envoi d'un MP, appeler `is_blocked(sender)`/`is_blocked(recipient)`. **F n'écrit AUCUN code MP** (le module n'existe pas). F documente le seam ; E ajoutera la garde en consommant le helper.
  - **Réponse à une Offer (épique B, #132)** : au point de réponse/acceptation, appeler `is_blocked(responder)`. Idem — F ne touche pas au code Offers.
  - **Règle d'implémentation** : n'ajouter une garde qu'aux seams **présents dans ce worktree**. Un seam absent → laisser une **note d'intégration** (docstring du helper + ce plan), pas de code mort.
- **Justification** : F livre le **contrat** de blocage et son **application aux seams existants** (follows local + fédéré), tout en restant **découplée** de B/E. Le critère 3 est **prouvable en v1** sur les follows (local + inbound) ; MP/Offers seront couverts par B/E quand ils consommeront le helper.

### DEC-F4 — File de modération = surface admin custom `gmh:` (pas Django admin comme primaire)
- **Étendre `core/admin_views.py` + `core/admin_urls.py` (`gmh:`)**, cohérent avec `admin_users`/`admin_user_suspend` (`@admin_required`, HTMX, templates `gmh/`) :
  - `gmh:reports` — liste des `UserReport` `status=pending` (file), tri `-created_at`, `select_related("reporter","reported_user")`.
  - `gmh:report_dismiss` (`@require_POST`) — passe un signalement à `dismissed` (« ignorer », critère 2).
  - `gmh:user_block` (`@require_POST`) — `block_user(reported_user, by=admin, report=...)` (critère 2 + 3).
  - `gmh:user_unblock` (`@require_POST`) — `unblock_user(...)` (réversibilité).
  - Templates `templates/gmh/reports.html` (+ partials HTMX pour résolution inline si utile).
- **Django admin** : enregistrer `UserReport` dans `core/admin.py` (comme `ContentReport` déjà enregistré) — **surface secondaire** de consultation, cheap. Le flux **primaire** de #136 reste `gmh:`.
- **Justification** : le projet possède déjà une **UX de modération front** (`gmh:`) où vivent suspension et blocage d'instances ; y ajouter la file est cohérent et HTMX-natif. Django admin seul n'intègre pas le flux front `gmh:` ni l'action `block_user`. **Alternative écartée** : file uniquement dans Django admin — casse la cohérence UX et duplique la logique de blocage hors service.

### DEC-F5 — Notification admin au signalement (type dédié, éviter `NEW_REPORT`)
- **Ajouter `NotificationType.MODERATION_REPORT`** (« Nouveau signalement à traiter ») — **distinct de `NEW_REPORT`** (= nouveau compte-rendu/scène). Migration `core` `AlterField(Notification.type choices)` (additif, CharField sans check-constraint → sûr).
- **Signal** : receiver post_save `sender="core.UserReport"` dans `core/notification_signals.py` — à la création, `Notification(type=MODERATION_REPORT, recipient=<chaque admin local>, actor=reporter, target=<UserReport>)` pour tous les `User.objects.filter(is_admin=True, remote=False)`. GFK `target` → le `UserReport`.
- **Justification** : réutilise le patron post_save existant ; type dédié évite la confusion sémantique ; ciblage admins-locaux uniquement.

### DEC-F6 — Gating « le signalé n'est PAS notifié » (critère 4)
- **Invariant** : à la création d'un `UserReport` et au blocage, **aucune** `Notification` n'est émise vers `reported_user`. Le signal DEC-F5 cible **exclusivement** les admins. Le blocage ne notifie pas le bloqué (il constatera fonctionnellement l'impossibilité d'interagir, sans message « vous avez été signalé/bloqué »).
- **Justification** : critère 4 explicite. Prouvé en Phase 5 par un test asserttant `Notification.objects.filter(recipient=reported_user).count() == 0` après signalement + blocage.

### DEC-F7 — Fédération AP `Flag` : **hors v1** (décision critique tranchée)
- **v1 = modération locale uniquement. AUCUNE émission ni réception d'AP `Flag`.**
  - Les **4 critères d'acceptation sont tous locaux** (signaler, file admin, blocage coupe interactions, signalé non notifié). Aucun ne requiert `Flag`.
  - **Aucune infra Flag** n'existe (inbox/serializers/tasks). L'ajouter (Flag sortant vers l'instance d'origine d'un compte distant + réception/routage Flag entrant) est un chantier AP significatif hors périmètre des critères.
- **Ce que v1 couvre POUR le distant, sans `Flag`** : un compte **distant** est **signalable** (GFK `reported_user` accepte un User miroir `remote=True`) et **blocable localement** ; ses interactions **fédérées entrantes** (Follow via `handle_follow` maintenant ; MP/Offers quand E/B atterrissent) sont **refusées** par le même helper `is_blocked` au **niveau inbox** → satisfait « un utilisateur bloqué ne peut plus interagir avec l'instance », y compris distant.
- **Différé (épique/itération ultérieure, documenté)** : émission d'un AP `Flag` vers l'instance d'origine lors du signalement d'un compte distant, et réception/routage d'un `Flag` entrant. À trancher/planifier séparément.
- **Justification** : découpe conservatrice pilotée par les critères ; pas de sur-ingénierie AP ; le volet distant reste couvert par le gating inbox. **Point à confirmer par l'humain** si `Flag` sortant doit entrer en v1 → replan ciblé (ajout serializer `serialize_flag` + task d'émission + garde Suddenly-only) sans toucher le reste.

## Architecture projection

### Files to create
- `suddenly/core/moderation.py` — helper central : `is_blocked`, `block_user`, `unblock_user`, `create_user_report` (DEC-F3). (Ou fonctions ajoutées à `core/services.py` ; module dédié préféré pour la clarté du contrat.)
- `templates/gmh/reports.html` (+ partials HTMX de résolution) — file de modération (DEC-F4).
- Templates de signalement côté utilisateur : `templates/core/report_user_form.html` (+ partial de confirmation HTMX) — formulaire « signaler cet utilisateur » (DEC-F1, Phase 3).
- `tests/core/test_moderation.py` — critères 1, 2, 4 (signalement crée un `UserReport` avec motif ; file admin liste les `pending`, bloquer/ignorer ; helper `is_blocked`/`block_user`/`unblock_user` ; notification admin ; **signalé non notifié**).
- `tests/activitypub/test_block_gating.py` — critère 3 volet fédéré (inbound `handle_follow` refusé pour un follower distant `is_blocked`).

### Files to modify
- `suddenly/core/models.py` — `UserReport` (DEC-F1) ; `NotificationType.MODERATION_REPORT` (DEC-F5).
- `suddenly/users/models.py` — `User.is_blocked` + `blocked_at` + `blocked_by` (DEC-F2).
- `suddenly/core/migrations/` — `UserReport` + `AlterField(Notification.type)` (`makemigrations core`).
- `suddenly/users/migrations/` — champs de blocage `User` (`makemigrations users`).
- `suddenly/core/admin.py` — enregistrer `UserReport` (surface secondaire, DEC-F4).
- `suddenly/core/notification_signals.py` — receiver post_save `core.UserReport` → notifier les admins locaux (DEC-F5/F6).
- `suddenly/core/admin_views.py` — `admin_reports`, `admin_report_dismiss`, `admin_user_block`, `admin_user_unblock` (`@admin_required`, `@require_POST` sur mutations) (DEC-F4).
- `suddenly/core/admin_urls.py` — routes `gmh:reports` / `report_dismiss` / `user_block` / `user_unblock`.
- `suddenly/core/views.py` (ou `core/front_urls.py`) + `suddenly/core/urls.py` — vue de signalement utilisateur (`@login_required @require_POST` pour la soumission ; GET formulaire) + point d'entrée UI (bouton « Signaler » sur le profil, `templates/users/profile.html` ou composant dédié).
- `suddenly/characters/follow_views.py` — `follow_toggle` : garde `is_blocked` (émetteur + cible) (DEC-F3, Phase 4).
- `suddenly/activitypub/inbox.py` — `handle_follow` : refuser le Follow d'un follower distant `is_blocked` (DEC-F3, Phase 4).

### Non modifié (isolation B/E — DEC-F3)
- **Aucun fichier MP (épique E) ni Offers (épique B)** : modules absents du worktree. F fournit le helper ; le câblage MP/Offers est **différé** à B/E. Ne PAS créer de garde dans un module inexistant.
- **`admin_user_suspend`/`is_active`** : levier de suspension US-25 **inchangé** (orthogonal au blocage, DEC-F2).
- **`ContentReport`/`UserBlock`/`UserMute`** : concepts distincts, **non touchés** (DEC-F1/F2).

### Files to delete
- Aucun.

## Applicable rules

| Tool | Name | Path | Why it applies |
| ---- | ---- | ---- | -------------- |
| claude | 03-django-models | `.claude/rules/03-frameworks-and-libraries/03-django-models.md` | `UserReport` via migration, GFK contexte + `on_delete`, `Meta.indexes`, aucune logique métier en modèle ; champs `User` additifs |
| claude | 03-django-services | `.claude/rules/03-frameworks-and-libraries/03-django-services.md` | `moderation.py` : `block_user`/`unblock_user`/`create_user_report` en service, jamais inline dans une vue ; helper `is_blocked` unique point de vérité |
| claude | 03-htmx-patterns | `.claude/rules/03-frameworks-and-libraries/03-htmx-patterns.md` | `@require_POST` sur mutations (signaler, bloquer, ignorer) avant `@login_required`/`@admin_required` ; `getattr(request,"htmx",False)` ; `{% url %}` namespacé (`gmh:`, `users:`) ; `|escapejs` si injection JS |
| claude | 08-activitypub | `.claude/rules/08-domain/08-activitypub.md` | Gate inbound `handle_follow` sans casser la signature/idempotence ; DEC-F7 (pas de `Flag` v1) reste conforme ; `fetch_ap_json` unique point d'entrée si résolution actor |
| claude | ap-pivots-django-activitypub | `.claude/rules/07-quality/ap-pivots-django-activitypub.md` | Refus de Follow bloqué = return early best-effort, jamais 500 ; idempotence inbox préservée |
| claude | data-pivots-django-orm | `.claude/rules/07-quality/data-pivots-django-orm.md` | `select_related` sur la file (`reporter`/`reported_user`) ; `is_blocked` O(1) (flag indexé, pas de N+1) ; migrations reviewées via `sqlmigrate` |
| claude | i18n-patterns | `.claude/rules/08-domain/08-i18n-patterns.md` | Chaînes UI FR via `{% trans %}`/`gettext` ; `.po`/`.mo` recompilés en Phase 5 |
| claude | display-vocabulary | `.claude/rules/08-domain/08-display-vocabulary.md` | Vocabulaire cohérent (« signalement », « bloquer », « signalé ») ; ne pas confondre « compte-rendu » (`NEW_REPORT`) et « signalement » (`MODERATION_REPORT`) |
| claude | dry-refactor | `.claude/rules/07-quality/dry-refactor.md` | Le gating passe par l'unique helper `is_blocked` réutilisé à chaque seam (règle de trois) ; pas de check ad hoc dupliqué |
| claude | file-language-and-style | `.claude/rules/01-standards/file-language-and-style.md` | Ce plan (`aidd_docs/tasks/**`) human-consumed → français ; symboles/chemins verbatim |

## User Journey

```mermaid
flowchart TD
    A["Utilisateur A ouvre le profil de B"] --> B["Formulaire 'Signaler' (motif + contexte optionnel)"]
    B --> C["create_user_report -> UserReport status=pending"]
    C --> D["Signal post_save -> Notification MODERATION_REPORT a chaque admin local"]
    C --> E["AUCUNE notification vers B (critere 4)"]
    D --> F["Admin ouvre gmh:reports (file des pending)"]
    F --> G{"Decision admin"}
    G -->|Ignorer| H["report_dismiss -> status=dismissed"]
    G -->|Bloquer| I["user_block -> block_user(B): is_blocked=True + report resolved"]
    I --> J["B (local) ne peut plus follow: follow_toggle refuse (is_blocked)"]
    I --> K["B (distant) ne peut plus follow: handle_follow refuse au niveau inbox"]
    I --> L["Seams MP (E) / Offers (B) consommeront is_blocked quand mergees"]
    C --> Z1["Critere 1 couvert"]
    G --> Z2["Critere 2 couvert"]
    J --> Z3["Critere 3 couvert (local)"]
    K --> Z3b["Critere 3 couvert (federe)"]
    E --> Z4["Critere 4 couvert"]
```

## Risk register

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Confusion `NEW_REPORT` (compte-rendu) vs signalement | Notification/UI ambiguë | Type dédié `MODERATION_REPORT` (DEC-F5) ; libellés `display-vocabulary` ; test sur le type émis |
| Blocage conflaté avec `is_active` (suspension US-25) | Régression login / distant non gaté | `is_blocked` **distinct** de `is_active` (DEC-F2) ; `admin_user_suspend` inchangé ; test gating distinct |
| Couplage accidentel à B/E non mergées | Import cassé / code mort | F n'écrit AUCUN code MP/Offers ; helper dans `core` sans dépendance B/E ; garde ajoutée **uniquement** aux seams présents (DEC-F3) |
| Signalé notifié par erreur | Critère 4 violé | Signal cible exclusivement `is_admin=True, remote=False` ; test `Notification.filter(recipient=reported_user).count()==0` (DEC-F6) |
| `handle_follow` gaté maladroitement (500 / boucle) | Fédération cassée | Return early best-effort avant `Follow.get_or_create` ; idempotence préservée ; test inbound bloqué |
| `is_blocked` en jointure sur chemin chaud | N+1 / lenteur | Flag dénormalisé indexé sur `User`, lu en O(1) (DEC-F2) ; pas de requête par interaction |
| Surcharge de `ContentReport` | Sémantique confuse, régression US-27 | Modèle dédié `UserReport` (DEC-F1) ; `ContentReport` intact |
| `Flag` AP attendu en v1 par l'humain | Périmètre mal cadré | DEC-F7 tranché (hors v1) + point à confirmer ; volet distant couvert par gating inbox ; replan ciblé possible sans toucher le reste |
| Migration `User` (champs blocage) casse une autre migration en attente | `makemigrations --check` rouge | Champs additifs `null`/`default` ; `makemigrations --check --dry-run` en critère Phase 1 ; `--create-db` sur base `suddenly_epicf` |
| Couverture < 80 % après ajout de code | `make check` rouge | Tests appariés aux 4 critères (Phase 5) ; scénarios local + fédéré + non-notifié |

## Implementation phases

> **Rappel batched tests** : Phases 1-4 = CODE SEUL (aucun test écrit). Chaque phase se clôt par un run **ciblé des tests EXISTANTS** du périmètre (`python -m pytest <scope> --create-db --no-cov -p no:cacheprovider -q`, base `suddenly_epicf` inline). Phase 5 écrit toute la couverture. `{% trans %}` inline = code (phases 1-4) ; `.po`/`compilemessages` = Phase 5.

### Phase 1 : Modèles + migrations + enregistrement admin (CODE SEUL)

> Poser le socle : `UserReport`, champs de blocage `User`, type de notification. Frontière migration.

#### Tasks
1. `core/models.py` : `UserReport` (DEC-F1) — `reporter`/`reported_user` FK User, `category` (`ReportCategory`), `comment`, GFK contexte optionnel, `status` (`pending`/`resolved`/`dismissed`), `handled_by`/`handled_at`, `Meta.indexes`. Aucune logique métier.
2. `users/models.py` : `User.is_blocked` (`BooleanField default=False db_index=True`), `blocked_at` (`null=True`), `blocked_by` (FK User `null=True SET_NULL related_name="+"`) (DEC-F2).
3. `core/models.py` : `NotificationType.MODERATION_REPORT` (DEC-F5).
4. `core/admin.py` : enregistrer `UserReport` (list_display/list_filter/search sur `status`/`reported_user`/`reporter`).
5. `python manage.py makemigrations core users` → `migrate` ; revoir le SQL via `sqlmigrate`.

#### Acceptance criteria
- [ ] `python manage.py makemigrations --check --dry-run` : aucune migration manquante (core : `UserReport` + `AlterField(Notification.type)` ; users : champs blocage).
- [ ] `python manage.py check` passe ; `UserReport` enregistré dans Django admin.
- [ ] Run ciblé tests existants : `python -m pytest tests/core tests/users --create-db --no-cov -p no:cacheprovider -q` (vert, aucune régression).

### Phase 2 : Service de modération central + notification admin (CODE SEUL)

> Le contrat de blocage + la notification admin (et le non-notif du signalé).

#### Tasks
1. `core/moderation.py` : `is_blocked(user)`, `block_user(user, *, by, report=None)`, `unblock_user(user)`, `create_user_report(reporter, reported_user, category, comment="", context=None)` (DEC-F3). Idempotence sur block/unblock.
2. `core/notification_signals.py` : receiver post_save `sender="core.UserReport"` → à la création, `Notification(type=MODERATION_REPORT)` pour chaque `User.objects.filter(is_admin=True, remote=False)`, `actor=reporter`, `target=<UserReport>` (DEC-F5). **Ne jamais notifier `reported_user`** (DEC-F6).

#### Acceptance criteria
- [ ] `create_user_report(...)` crée un `UserReport` `pending` avec motif ; le signal notifie les admins locaux, jamais le signalé.
- [ ] `block_user`/`unblock_user` basculent `is_blocked` (+ audit `blocked_at`/`blocked_by`) idempotemment ; `is_blocked(user)` reflète l'état.
- [ ] Run ciblé : `python -m pytest tests/core --create-db --no-cov -p no:cacheprovider -q` (vert).

### Phase 3 : UI signalement (utilisateur) + file de modération (admin `gmh:`) (CODE SEUL)

> Rendre le signalement soumettable et la file traitable.

#### Tasks
1. Vue + template de signalement : formulaire « Signaler cet utilisateur » (motif obligatoire + contexte optionnel), soumission `@login_required @require_POST` → `create_user_report`. Point d'entrée UI sur le profil (`templates/users/profile.html` ou composant). Empêcher l'auto-signalement.
2. `core/admin_views.py` + `core/admin_urls.py` (`gmh:`) : `admin_reports` (liste `pending`, `select_related`), `admin_report_dismiss` (`@require_POST`), `admin_user_block`/`admin_user_unblock` (`@require_POST`, appellent `block_user`/`unblock_user`). `@admin_required`, HTMX, patron 3-templates si résolution inline.
3. Templates `templates/gmh/reports.html` (+ partials) ; `{% trans %}` inline, `{% url 'gmh:…' %}` namespacé, `|escapejs` sur toute valeur injectée en JS.

#### Acceptance criteria
- [ ] Un utilisateur soumet un signalement (POST) → `UserReport` `pending` créé ; auto-signalement refusé.
- [ ] L'admin voit la file `gmh:reports` et peut **ignorer** (`dismissed`) ou **bloquer** (`is_blocked=True` + report `resolved`) via POST.
- [ ] Run ciblé : `python -m pytest tests/core tests/users --create-db --no-cov -p no:cacheprovider -q` (vert ; aucun test écrit ici).

### Phase 4 : Gating des interactions aux seams existants (CODE SEUL)

> Faire mordre le blocage sur les follows (local + fédéré). Documenter les seams différés MP/Offers.

#### Tasks
1. `characters/follow_views.follow_toggle` : refuser (403/HTMX) si `is_blocked(request.user)` **ou** cible bloquée (DEC-F3).
2. `activitypub/inbox.handle_follow` : après résolution du follower distant, **return early best-effort** si `is_blocked(follower)` (pas de création de Follow, pas de 500) (DEC-F3).
3. **Documenter (docstring `moderation.is_blocked` + Amendments)** les seams **différés** : envoi de MP (épique E) et réponse à une Offer (épique B) appelleront `is_blocked` quand ces modules atterriront. **Ne PAS créer de code dans des modules inexistants.**

#### Acceptance criteria
- [ ] Un utilisateur bloqué ne peut plus follow (local) ; un follower distant bloqué ne crée plus de Follow (inbound).
- [ ] Aucun fichier MP/Offers créé ni modifié ; le contrat `is_blocked` est documenté pour B/E.
- [ ] Run ciblé : `python -m pytest tests/characters tests/activitypub --create-db --no-cov -p no:cacheprovider -q` (vert, non-régression follow).

### Phase 5 : Tests batchés (4 critères) + i18n + `make check`

> Écrire toute la couverture d'un coup ; prouver les 4 critères et la santé CI.

#### Tasks
1. `tests/core/test_moderation.py` : critère 1 (signalement avec motif → `UserReport`) ; critère 2 (file `pending` visible admin, bloquer/ignorer) ; critère 4 (aucune notification vers `reported_user` après signalement + blocage) ; helper `is_blocked`/`block_user`/`unblock_user` ; notification admin `MODERATION_REPORT`.
2. `tests/activitypub/test_block_gating.py` : critère 3 volet fédéré (inbound `handle_follow` refusé pour follower distant `is_blocked`) ; + critère 3 volet local (`follow_toggle` refusé pour utilisateur/cible bloqué·e) si testé ici ou dans `tests/characters`.
3. i18n : `makemessages` + `compilemessages` pour les nouvelles chaînes FR/EN ; committer `.mo`.
4. `make check` (ruff + mypy strict + pytest/coverage ≥ 80 + i18n-check) ; corriger jusqu'au vert.
5. Vérifier le `success_condition` de bout en bout.

#### Acceptance criteria
- [ ] `make check` passe (lint + typecheck + test/coverage ≥ 80 + i18n).
- [ ] `python -m pytest tests/core/test_moderation.py tests/activitypub/test_block_gating.py --create-db --no-cov -p no:cacheprovider -q` sort en 0.
- [ ] Les 4 critères #136 sont couverts par au moins un test nommé.

## Amendments

<!-- 🤖 entrées pendant l'implémentation -->
<!-- Seams de gating DIFFÉRÉS (B/E non mergées) : ajouter `is_blocked(...)` au point d'envoi d'un MP (épique E, #135) et au point de réponse/acceptation d'une Offer (épique B, #132) quand ces modules seront présents. F ne les code pas. -->

## Log

<!-- APPEND ONLY -->

## Validation flow demonstration

1. `python manage.py migrate` puis `python manage.py check` — `UserReport` + champs blocage `User` en place, aucune migration manquante.
2. A signale B (motif + contexte optionnel) → `UserReport` `pending` créé ; chaque admin local reçoit une `Notification(MODERATION_REPORT)` ; **B ne reçoit rien**.
3. L'admin ouvre `gmh:reports`, voit le signalement `pending`, **bloque** B → `B.is_blocked=True`, report `resolved`.
4. B (local) tente de follow → `follow_toggle` refuse ; un follower distant B' bloqué → `handle_follow` ne crée pas de Follow.
5. L'admin **ignore** un autre signalement → `dismissed`. L'admin **débloque** B → interactions rétablies.
6. `make check && python -m pytest tests/core/test_moderation.py tests/activitypub/test_block_gating.py --create-db --no-cov -p no:cacheprovider -q` → sort en 0.

## Évaluation de confiance : 8/10

Raisons (✓)
- Existant vérifié ligne à ligne : modèles de modération partiels déjà présents (`ContentReport`/`UserBlock`/`ReportCategory`), `User.is_admin`, suspension `admin_user_suspend`/`is_active`, surface admin custom `gmh:`, signaux de notification, seams Follow (local `follow_toggle` + inbound `handle_follow`), absence totale d'infra `Flag`.
- Décisions conservatrices et découplées : modèle `UserReport` dédié (n'écrase pas `ContentReport`), `is_blocked` distinct de `is_active`/`UserBlock`, file dans `gmh:` cohérente avec l'existant, type de notification dédié.
- **Isolation B/E nette** (DEC-F3) : F livre le contrat `is_blocked` + l'applique aux seams présents (follows local + fédéré) sans coder dans MP/Offers absents ; critère 3 prouvable en v1 sur les follows.
- **Décision critique DEC-F7 tranchée** : AP `Flag` hors v1 (critères tous locaux, aucune infra Flag), volet distant couvert par gating inbox.

Risques (✗)
- Point à confirmer par l'humain : `Flag` sortant en v1 ou non (DEC-F7). Si oui → replan ciblé additif (serializer + task + garde Suddenly-only), sans toucher le reste.
- Placement exact du point d'entrée UI « Signaler » (profil vs contextes scène/personnage/MP) : conservateur = bouton profil + contexte optionnel ; ajustable en Phase 3 sans impact modèle.
- Câblage MP/Offers différé à B/E : dépendance de séquencement explicite ; le critère 3 complet (MP/Offers) ne sera vert qu'une fois B/E mergées et consommant le helper.
