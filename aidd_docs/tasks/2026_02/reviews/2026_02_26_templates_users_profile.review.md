# Code Review for templates-users-profile

Ajout des templates `users/profile.html` et `users/profile_edit.html`, plus un fix mineur dans `core/tasks.py`.

- **Status**: ✅ Prêt — 2 corrections mineures suggérées
- **Confidence**: 9.0/10

## Main Expected Changes

- [x] `templates/users/profile.html` — profil public
- [x] `templates/users/profile_edit.html` — formulaire d'édition
- [x] Fix `core/tasks.py:87` — `object_id` vs `target_id` (GenericFK)

## Scoring

### Potentially Unnecessary Elements

- [🟢] Aucun code mort ni import inutile

### Standards Compliance

- [🟢] **Extends base.html** : les deux templates héritent correctement
- [🟢] **Classes Tailwind** : `container-app`, `card`, `card-body`, `btn-primary`, `btn-ghost`, `avatar-md`, `avatar-placeholder` — conformes aux conventions
- [🟢] **Icônes Lucide** : `i-lucide-edit-2`, `i-lucide-globe`, `i-lucide-save`, etc.
- [🟢] **Pas de logique métier** dans les templates

### Architecture

- [🟢] **Séparation** : templates purement présentationnels
- [🟢] **URLs nommées** : `{% url 'users:profile_edit' %}`, `{% url 'users:profile' %}` — pas d'URL en dur

### Code Health

- [🟡] **Bio sans filtre** `templates/users/profile.html:42` — `{{ profile_user.bio }}` sans `|linebreaksbr` : les sauts de ligne saisis par l'utilisateur sont ignorés, la bio s'affiche en bloc unique (ajouter `|linebreaksbr`)
- [🟡] **Widget JSONField sans classe CSS** `templates/users/profile_edit.html:138` — `{{ form.preferred_languages }}` délègue au widget Django (Textarea) sans `form-input`. Le champ sera stylé différemment de tous les autres (ajouter une classe via `form.preferred_languages.as_widget(attrs={'class': 'form-input'})`)
- [🟢] **tasks.py** : commentaire explique le POURQUOI du changement `object_id` (GenericFK) — conforme règle commentaires

### Security

- [🟢] **XSS** : `{{ profile_user.bio }}` est auto-escapé par Django
- [🟢] **actor_url** : construit par l'application depuis le domaine, pas user input direct
- [🟢] **help_text|safe** : les `help_text` sont définis par les développeurs, pas user input
- [🟢] **CSRF** : `{% csrf_token %}` présent dans le formulaire

### Frontend specific

#### State Management

- [🟢] **Empty state** : section "Parties récentes" avec état vide explicite
- [🟢] **Erreurs formulaire** : chaque champ affiche ses erreurs individuellement
- [🟢] **Avatar conditionnel** : `{% if profile_user.avatar %}` avec placeholder

#### UI/UX

- [🟢] **Responsive** : `flex-col sm:flex-row` sur le header profil
- [🟢] **Sémantique HTML** : `<section>`, `<h1>`, `<label for>` corrects
- [🟢] **Edit button** : visible uniquement si `user == profile_user`
- [🟢] **enctype multipart/form-data** : présent pour l'upload avatar

## Final Review

- **Score**: 9.0/10
- **Blocking issues**: 0
- **Minor fixes**: 2 — `|linebreaksbr` sur bio, classe CSS sur widget JSONField
- **Follow-up**: préférence languages UI à améliorer quand le modèle aura des choices définies
