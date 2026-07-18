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

## Endpoints HTMX state-mutating

- Toujours décorer avec `@require_POST` (avant `@login_required`) les vues qui mutent l'état : create, delete, update
- Un GET ne doit jamais supprimer ou modifier des données — un `<img>` ou un prefetch navigateur peut déclencher le GET
- Les vues HTMX front (`front_views.py`) retournent du HTML (partials), jamais du JSON — pour les typeahead aussi

## Injection de valeurs dans un contexte JS

- Ne jamais interpoler `{{ var }}` directement dans un attribut `onclick` ou une string JS — XSS garanti
- Pattern correct : data attributes + handler Alpine/JS :
  ```html
  data-slug="{{ char.slug|escapejs }}" data-name="{{ char.name|escapejs }}"
  @click="document.getElementById('field').value = $el.dataset.slug"
  ```
- Utiliser `|escapejs` sur toute valeur injectée dans un attribut `data-*` utilisé par JS

## Infinite scroll — pattern sentinel

- Sentinel `<div>` en fin de partial avec `hx-swap="outerHTML"` — le sentinel se remplace lui-même par (nouvelles entrées + nouveau sentinel)
- Ne jamais utiliser `hx-swap="afterend"` + `hx-target="this"` sur le dernier item — l'élément reste et re-déclenche à chaque scroll
- Le sentinel est absent si `has_next=False` — le scroll s'arrête naturellement
- Pattern :
  ```html
  {% if has_next %}
  <div hx-get="?page={{ next_page }}"
       hx-trigger="revealed"
       hx-swap="outerHTML"></div>
  {% endif %}
  ```

## Switch de mode HTMX + cohérence URL

- `hx-push-url="true"` sur les boutons de switch pousse `?mode=group` dans l'URL
- La vue doit lire `?mode` sur le GET complet (refresh, bookmark) — ne pas hardcoder le mode par défaut sans lire les params
- Valider `mode` par whitelist avant injection dans le contexte :
  ```python
  mode = request.GET.get("mode") if request.GET.get("mode") in ("flux", "group") else "flux"
  ```

## URLs dans les templates

- Toujours préfixer avec le namespace de l'app : `{% url 'characters:link_request_accept' pk=... %}`
- Ne jamais utiliser un nom court non qualifié — `NoReverseMatch` garanti si l'app a un `app_name`
