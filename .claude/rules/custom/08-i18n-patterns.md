---
paths:
  - "config/settings/**/*.py"
  - "suddenly/**/*.py"
  - "templates/**/*.html"
---

# i18n — règles de traduction

## Chaînes dans les settings Python

- Ne jamais mettre de chaîne UI dans une langue spécifique dans `base.py` ou `production.py`
- Utiliser `None` comme valeur par défaut ; laisser le context processor gérer le fallback lazy
- **Mauvais** : `SITE_DESCRIPTION = "Réseau fédéré de fiction partagée"`
- **Bon** : `SITE_DESCRIPTION = None  # Translated at runtime via context processor`

## Context processors

- Toujours utiliser `gettext_lazy` (jamais `gettext` ni `str(_(...))`) pour les traductions de contexte
- `str(_(...))` évalue à l'import du module — la langue de la requête n'est pas encore connue
- Pattern correct : `getattr(settings, "X", None) or _("Default string")`
- Le type de retour doit être `dict[str, object]` si des `_StrPromise` sont incluses

## Fichiers .mo

- Les `.mo` sont versionnés dans git (pas dans `.gitignore`)
- Après toute modification d'un `.po`, recompiler via babel et committer les `.mo` :
  ```python
  from babel.messages.mofile import write_mo
  from babel.messages.pofile import read_po
  with open("locale/fr/LC_MESSAGES/django.po", "rb") as f:
      catalog = read_po(f)
  with open("locale/fr/LC_MESSAGES/django.mo", "wb") as f:
      write_mo(f, catalog)
  ```
- Sur une machine avec `gettext` : `python manage.py compilemessages -l fr -l en`
