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

## Activation de langue par requête (middleware)

- Tout middleware qui appelle `translation.activate(lang)` doit `translation.deactivate()` dans un `finally`
  **Why:** la langue est un thread-local ; les workers Gunicorn/threads sont réutilisés → sans reset, la langue d'une requête fuit sur la requête suivante servie par le même thread
- Pattern : `translation.activate(lang)` puis `try: response = get_response(request) finally: translation.deactivate()`

## Catalogue `locale/fr` — convention msgid mixtes

- Les chaînes sources sont **mixtes FR/EN** — le msgid n'est pas garanti anglais
- msgid déjà français → **traduction identité** (`msgstr` = `msgid`), jamais laissé vide
- msgid anglais → traduction française réelle
- Terminologie établie à respecter : *follower* → abonné · *following* → abonnement · *Follow/Unfollow* → Suivre / Se désabonner
- Patcher un `.po` par **index d'entrée**, jamais en retapant un msgid — accents, `…` et `—` se corrompent silencieusement

## Entrées fuzzy — piège de rendu

- gettext **exclut les entrées `fuzzy` du `.mo`** → la chaîne s'affiche en **msgid brut**
- Un msgid anglais resté fuzzy s'affiche donc en anglais malgré un `msgstr` français présent
- Conséquence : lever un `fuzzy` **change le rendu** — vérifier les tests qui assertent sur ce texte
- `msgattrib --clear-previous` après avoir levé des flags — sinon les `#| msgid` orphelins subsistent

## Tests et chaînes traduites

- Ne jamais asserter sur un libellé traduit rendu — asserter sur le **contexte de vue**
  **Why:** l'assertion casse à tout changement de formulation ou de locale, et une assertion négative (`not in content`) devient silencieusement vacuement vraie dès que la chaîne est traduite

## Vérification du catalogue

- `make i18n-check` relance `makemessages` avant de tester → le catalogue doit être **idempotent sous régénération**
- Gate complète : `msgfmt -c` propre **et** 0 fuzzy **et** 0 msgstr vide
- Un `.mo` versionné peut dériver de son `.po` (compilé depuis un état antérieur) — comparer via `msgunfmt` avant de conclure à une perte de traduction

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
