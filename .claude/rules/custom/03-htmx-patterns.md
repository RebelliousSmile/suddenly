# HTMX — Patterns dans les FBVs Django

## Détection HTMX (mypy constraint)

- Toujours utiliser `getattr(request, "htmx", False)` — jamais `request.htmx`
- django-htmx ne fournit pas de stubs mypy ; `request.htmx` provoque `"HttpRequest" has no attribute "htmx" [attr-defined]`
- Pattern correct :
  ```python
  if getattr(request, "htmx", False):
      return render(request, "components/_fragment.html", context)
  ```

## Pattern 3 templates pour actions inline

Pour toute action HTMX qui modifie l'état d'un item dans une liste :

| Template | Rôle | Déclencheur |
|----------|------|-------------|
| `_X_form.html` | Formulaire inline (remplace la carte) | `hx-get` sur le bouton d'action |
| `_X_resolved.html` | Fragment post-action (état final) | `hx-post` confirm + succès |
| `_X_card_fragment.html` | Wrapper restauration carte | `hx-get` sur "Annuler" |

- `hx-target="#item-{{ id }}"` + `hx-swap="outerHTML"` sur chaque déclencheur
- Le bouton "Annuler" du formulaire inline appelle l'endpoint `card_partial` (GET) qui restitue la carte d'origine

## URLs dans les templates

- Toujours préfixer avec le namespace de l'app : `{% url 'characters:link_request_accept' pk=... %}`
- Ne jamais utiliser un nom court non qualifié — `NoReverseMatch` garanti si l'app a un `app_name`
