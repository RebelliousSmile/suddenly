# ManyToManyField dans les vues d'édition

## Vue (Python)

- Ne jamais inclure un champ M2M dans `update_fields` de `.save()` — Django lève `ValueError`
- Appeler `.set(tag_objects)` **après** `.save()` — la PK doit exister avant toute opération M2M
- Utiliser `get_or_create` pour résoudre les noms en objets :
  ```python
  tags_raw = request.POST.get("tags", "").strip()
  tag_objects = [Tag.objects.get_or_create(name=t)[0] for t in tags_raw.split(",") if t.strip()]
  obj.save(update_fields=[...])  # sans "tags"
  obj.tags.set(tag_objects)
  ```

## Template

- Garder le champ texte CSV — pas de widget M2M natif
- Guarded display pour éviter ValueError sur instance sans PK :
  ```html
  value="{% if form_data.tags %}{{ form_data.tags }}{% else %}{% if obj.pk %}{{ obj.tags.all|join:', ' }}{% endif %}{% endif %}"
  ```
- Bloquer la soumission du formulaire à l'appui d'Entrée dans le champ :
  ```html
  @keydown.enter.prevent
  ```

## Migration JSONField → M2M

Séquence obligatoire en 3 migrations :
1. Ajouter le champ M2M (nom temporaire, ex. `tags_new`) — JSONField intact
2. `RunPython` : lire JSONField, peupler M2M via `get_or_create`
3. Supprimer JSONField, renommer M2M → nom final via `makemigrations` (répondre `y` au prompt de renommage)
