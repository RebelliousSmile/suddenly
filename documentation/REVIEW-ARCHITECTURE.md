# Revue Architecture - Incohérences et Optimisations

**Date** : 2026-01-02
**Analysé par** : technical-architect agent

---

## Résumé

| Catégorie | Critique | Important | Mineur | Corrigé |
|-----------|----------|-----------|--------|---------|
| Incohérences | ~~1~~ 0 | ~~2~~ 1 | ~~1~~ 0 | 3 |
| Optimisations | 0 | ~~2~~ 1 | ~~2~~ 0 | 3 |

**Mise à jour 2026-01-02** : 6 problèmes corrigés sur 8. Reste 2 actions en attente.

---

## Incohérences Détectées

### 1. ✅ CORRIGÉ - Référence SQLite obsolète

**Fichier** : `ARCHITECTURE.md:159-160`
**Statut** : Corrigé

La référence au mode SQLite a été supprimée.

---

### 2. ✅ CORRIGÉ - Game : Acteur ou Objet ?

**Fichiers concernés** :
- `conception-jdr-activitypub.md:188-201` → Game = **Acteur** (inbox/outbox)
- `api/activitypub.md:139-141` → Game = **Acteur Group** ✅

**Décision** : Game = **Acteur** (type `Group`)

**Justification** :
- Les utilisateurs peuvent suivre une partie directement
- Les nouveaux Reports sont publiés via l'outbox de la partie
- Séparation claire : suivre Alice ≠ suivre sa campagne

**Mise à jour effectuée** :
- `api/activitypub.md` : Game converti en acteur avec inbox/outbox/publicKey
- `models/README.md` : Modèle Game mis à jour avec champs ActivityPub

---

### 3. ⚠️ IMPORTANT - Champ `remote` vs `local` inversés

**Fichiers concernés** :
- `conception-jdr-activitypub.md` → utilise `remote: boolean` (true = fédéré)
- `models/README.md` → utilise `local: boolean` (true = local)

**Problème** : Sémantique inversée

```
conception:  remote = true  → entité fédérée
models:      local = true   → entité locale (remote = false)
```

**Impact** : Confusion lors de l'implémentation, bugs potentiels

**Recommandation** : Utiliser `local: boolean` partout (comme BookWyrm)
- `local = True` → créé sur cette instance
- `local = False` → importé d'une autre instance

**Action requise** : Mettre à jour `conception-jdr-activitypub.md` pour utiliser `local` au lieu de `remote`

---

### 4. 📝 MINEUR - Champs manquants dans conception

**Fichier** : `conception-jdr-activitypub.md`

**Champs manquants pour User** :
- `public_key` / `private_key` (signatures HTTP)
- `followers_url` (collection followers)
- `shared_inbox` (inbox partagé)
- `federated_server_id` (FK vers instance)

**Champs manquants pour Character** :
- `public_key` / `private_key`
- `followers_url`
- `inbox` / `outbox` (si acteur)

**Action requise** : Le fichier `models/README.md` est plus complet, il fait référence.

---

## Optimisations Proposées

### 1. ✅ CORRIGÉ - Modèle SharedSequence

**Problème** :
`conception-jdr-activitypub.md:345-358` définit `SharedSequence` (séquence de jeu partagée après un lien accepté).

Ce modèle n'était **pas présent** dans `models/README.md`.

**Décision** : **Inclus dans MVP** (obligatoire)

**Justification** :
> "Ça n'a pas d'intérêt de proposer une interaction dans une autre partie si on n'a pas de proposition narrative à faire."

**Mise à jour effectuée** :
- `models/README.md` : Modèle `SharedSequence` ajouté avec documentation complète
- Un Claim/Adopt/Fork sans proposition narrative est rejeté

---

### 2. ⚠️ IMPORTANT - Fédération sans Celery

**Problème** :
L'architecture permet Celery optionnel, mais la doc ne précise pas comment la fédération fonctionne sans.

**Questions non résolues** :
- Comment envoyer les activités AP de manière synchrone ?
- Quel impact sur les temps de réponse ?
- Quelle stratégie de retry ?

**Recommandation** : Documenter le fallback synchrone

```python
# Proposition de pattern
def deliver_activity(activity, recipients):
    if settings.CELERY_ENABLED:
        deliver_activity_async.delay(activity, recipients)
    else:
        # Synchrone avec timeout court
        deliver_activity_sync(activity, recipients, timeout=5)
```

---

### 3. 📝 MINEUR - Configuration FTS PostgreSQL

**Fichier** : `models/README.md`

**Problème** : Les index FTS utilisent `'french'` mais la configuration PostgreSQL n'est pas documentée.

**Action** : Ajouter dans la doc de déploiement :

```sql
-- Configuration FTS français
CREATE TEXT SEARCH CONFIGURATION french_unaccent (COPY = french);
ALTER TEXT SEARCH CONFIGURATION french_unaccent
  ALTER MAPPING FOR hword, hword_part, word WITH unaccent, french_stem;
```

---

### 4. ✅ CORRIGÉ - Visibilité EPHEMERAL des Quotes

**Fichier** : `conception-jdr-activitypub.md:246`

**Problème** : "EPHEMERAL — visible uniquement pendant la session, disparaît après"

**Décision** : Garder EPHEMERAL avec clarification

**Définition** :
> "Dialogues passe-partout, inintéressants. Ce sont des contenus qui ne sont pas inclus dans la fédération, ni publique ni privée."

**Mise à jour effectuée** :
- `models/README.md` : Documentation de `QuoteVisibility` clarifiée
- EPHEMERAL = dialogues génériques, non fédérés (ex: "Bonjour", "Au revoir")

---

## Actions Prioritaires

### Immédiat (bloquant)

1. [x] ~~Trancher : Game = Acteur ou Objet ?~~ → **Acteur (Group)**
2. [ ] Harmoniser `remote` → `local` dans conception

### Avant implémentation

3. [ ] Documenter fallback fédération sans Celery
4. [x] ~~Décider du sort de SharedSequence~~ → **MVP obligatoire**
5. [x] ~~Clarifier visibilité EPHEMERAL~~ → **Dialogues passe-partout, non fédérés**

### Nice to have

6. [ ] Ajouter config FTS dans guide déploiement

---

## Cohérence Globale

| Document | Cohérent avec CLAUDE.md | Notes |
|----------|-------------------------|-------|
| `ARCHITECTURE.md` | ✅ Oui | Après correction SQLite |
| `api/activitypub.md` | ✅ Oui | Référence pour AP |
| `models/README.md` | ✅ Oui | Plus détaillé que conception |
| `conception-jdr-activitypub.md` | ⚠️ Partiellement | Nécessite mise à jour |
| `memory-bank/*` | ✅ Oui | À jour |

---

## Recommandation Finale

**Mettre à jour `conception-jdr-activitypub.md`** pour :
1. Aligner Game comme objet (pas acteur)
2. Utiliser `local` au lieu de `remote`
3. Marquer SharedSequence comme "post-MVP"
4. Clarifier ou supprimer EPHEMERAL

Les autres documents (`ARCHITECTURE.md`, `api/activitypub.md`, `models/README.md`) sont cohérents et peuvent servir de référence.
