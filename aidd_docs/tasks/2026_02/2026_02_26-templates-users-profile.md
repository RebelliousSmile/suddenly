# Plan : Templates profil utilisateur

**Date** : 2026-02-26
**Feature** : templates-users-profile
**Statut** : En attente d'implémentation

---

## Périmètre

Seuls les deux templates manquants sont à créer. Tout le reste (`base.html`, composants, `core/home.html`) existe déjà.

---

## Phase unique : Créer les deux templates

### Tâche 1 — `templates/users/profile.html`

**Vue** : `ProfileView` (DetailView)
**Contexte** : `profile_user` (instance User), `user` (utilisateur connecté)

Contenu :
- En-tête : avatar + display_name + `@username` + bio
- Lien "Modifier le profil" si `user == profile_user`
- Lien ActivityPub (`profile_user.actor_url`) pour suivre depuis le Fediverse
- Section placeholder "Parties récentes" (vide pour l'instant)

### Tâche 2 — `templates/users/profile_edit.html`

**Vue** : `ProfileEditView` (UpdateView)
**Contexte** : `form` (ProfileForm), `object` (User)

Contenu :
- Formulaire avec tous les champs ProfileForm via `{% include "components/form_fields.html" %}`
- Bouton submit + lien annuler → retour profil
- Titre : "Modifier mon profil"

---

## Conventions à respecter

- `{% extends "base.html" %}`
- Classes Tailwind existantes : `container-app`, `card`, `card-body`, `btn-primary`, `btn-ghost`, `avatar-md`, `avatar-placeholder`
- Icônes Lucide : `i-lucide-*`
- Pas de logique métier dans les templates

---

## Validation

- [ ] `ProfileView` affiche le profil sans erreur 500
- [ ] Lien "Modifier" visible uniquement pour le propriétaire
- [ ] `ProfileEditView` soumet le formulaire et redirige vers le profil
- [ ] Les erreurs de formulaire s'affichent correctement

---

## Confiance

**9.5/10**

✅ Context variables clairs (profile_user, form, object)
✅ Composants existants réutilisables (form_fields, base)
✅ Conventions CSS déjà établies dans home.html
❌ `preferred_languages` est un JSONField — affichage du widget à vérifier à l'exécution
