# Contributing Translations

Suddenly's interface is built on Django's standard i18n system. English is the source language (msgid); French ships as the primary translation. Adding a new language requires no code changes — only a `.po` file.

## Prerequisites

Install `gettext` (provides `msgfmt`, `msginit`, `msgmerge`):

```bash
# Debian / Ubuntu
sudo apt install gettext

# macOS
brew install gettext

# Windows (Chocolatey)
choco install gettext
```

Verify: `which msgfmt` (or `msgfmt --version` on Windows).

## Adding a new language (example: Spanish)

```bash
# 1. Create the .po file for your language
python manage.py makemessages -l es --no-wrap \
    --ignore=venv --ignore=node_modules --ignore=staticfiles

# 2. Translate strings
#    Use locale/fr/LC_MESSAGES/django.po as a reference for context.
#    Open locale/es/LC_MESSAGES/django.po in your editor or Poedit.

# 3. Compile
python manage.py compilemessages -l es

# 4. Test locally
LANGUAGE_CODE=es python manage.py runserver
# Switch language via the nav switcher or set Accept-Language: es in your browser.
```

## Declaring the language in settings

Add your language code to `config/settings/base.py`:

```python
LANGUAGES = [
    ("en", "English"),
    ("fr", "Français"),
    ("es", "Español"),   # ← add your language here
]
```

This makes it available in the nav switcher and the profile language selector.

## Translation guidelines

| Rule | Detail |
|---|---|
| UI strings only | Never translate user-generated content (game titles, bios, character names) |
| Keep msgid stable | Never edit English source strings in a PR that only translates — open a separate PR for source changes |
| Plural forms | Declare `Plural-Forms` correctly for your language in the `.po` header |
| No fuzzy entries | Review all `#, fuzzy` entries and either confirm or remove the flag before submitting |
| No empty msgstr | Every msgid must have a non-empty msgstr (or be intentionally left empty for en.po only) |

## Recommended tool: Poedit

[Poedit](https://poedit.net/) provides a GUI for `.po` files with spell-check and plural form helpers.

## PR checklist

```
[ ] locale/<lang>/LC_MESSAGES/django.po updated and complete
[ ] No #, fuzzy entries remaining
[ ] No empty msgstr (except en.po which uses msgid as-is)
[ ] Plural-Forms header correct for the target language
[ ] LANGUAGES updated in config/settings/base.py
[ ] Tested locally: interface renders in the new language
[ ] python manage.py compilemessages -l <lang> runs without errors
```

## Keeping catalogs up to date

When new UI strings are added to the codebase, all `.po` files go out of date. Run:

```bash
python manage.py makemessages -l <lang> --no-wrap \
    --ignore=venv --ignore=node_modules --ignore=staticfiles
```

Then translate the new `msgid` entries (they appear without a `msgstr`). The CI guardrail (`make i18n-check`) will catch any `.po` files that are out of sync.
