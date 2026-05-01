# Instruction: US-14 — Arbitrer les demandes de lien sur ses PNJ

## Feature

- **Summary**: Rendre le dashboard GM interactif — le GM peut accepter ou refuser les demandes de lien (Claim/Adopt/Fork) inline via HTMX, une par une dans l'ordre chronologique. La logique métier (`LinkService`) est déjà en place ; il manque la couche UI/HTMX.
- **Stack**: `Django 5.0`, `Python 3.12`, `HTMX`, `django-htmx`, `UnoCSS`
- **Branch name**: `feat/us-14-arbitrate-link-requests`
- **Parent Plan**: `none`
- **Sequence**: `standalone` (dépend de LinkService et gm_dashboard existants)
- **Confidence**: 9/10
- **Time to implement**: 1-2h

## Existing files to modify

- `@templates/components/link_request_card.html` — corriger URLs sans namespace (`accept_request` → `characters:link_request_accept`, idem reject/cancel) + `request.queue_position` → `queue_position`
- `@suddenly/characters/link_views.py` — rendre `link_request_accept` et `link_request_reject` HTMX-aware + ajouter `link_request_card_partial`
- `@suddenly/characters/front_urls.py` — ajouter URL `link_request_card_partial`
- `@templates/characters/gm_dashboard.html` — remplacer boucle interne par `{% include link_request_card %}` avec `queue_position=forloop.counter0`

### New files to create

- `templates/characters/_accept_form.html` — formulaire inline message narratif (GET HTMX)
- `templates/characters/_request_resolved.html` — fragment post-action (accept ou reject)
- `templates/characters/_link_request_card_fragment.html` — wrapper restauration carte (cancel)

## Architecture

**Flux Accepter :**
```
[Clic Accepter]
  → GET HTMX → link_request_accept → _accept_form.html (formulaire inline)
  → POST HTMX (avec message optionnel) → LinkService.accept_request() → _request_resolved.html + lien SharedSequence
```

**Flux Refuser :**
```
[Clic Refuser]
  → POST HTMX → link_request_reject → LinkService.reject_request() → _request_resolved.html
  (LinkService promeut automatiquement le prochain QUEUED en PENDING)
```

**Flux Annuler formulaire :**
```
[Clic Annuler dans formulaire]
  → GET HTMX → link_request_card_partial → _link_request_card_fragment.html (carte restaurée)
```

## Key decisions

- `accept_request()` retourne `CharacterLink` (confirmé `services.py` l.140) → `character_link.shared_sequence` passé explicitement en contexte, pas de traversal template
- `queue_position=forloop.counter0` : PENDING en index 0 (pas affiché), QUEUED à #1, #2…
- `link_request_card_partial` documenté comme endpoint générique (cancel GM + rechargements futurs)
- Aucun alias URL — correction dans le template uniquement

## Acceptance criteria (Gherkin)

```gherkin
Scenario: Plusieurs demandes en file d'attente
  Given mon PNJ a reçu 3 demandes (Claim, Adopt, Fork)
  When je consulte le dashboard
  Then elles sont affichées par ordre chronologique
  And la première est PENDING (traitable), les suivantes sont QUEUED (#1, #2)

Scenario: Acceptation avec réponse narrative
  Given je reçois une demande d'Adopt
  When je clique "Accepter"
  Then un formulaire inline apparaît sans rechargement
  When j'ajoute un message et confirme
  Then la carte passe à "accepted" et un lien vers la SharedSequence est affiché

Scenario: Refus sans bloquer les suivantes
  Given je refuse la première demande de la file
  When la demande est rejetée
  Then le demandeur est notifié
  And la demande suivante dans la file devient PENDING (traitable)
```

## Verification

```bash
make check   # lint + typecheck + tests
```

Tester manuellement :
1. `/characters/dashboard/` — PNJ avec PENDING + QUEUED
2. Clic Accepter → formulaire inline → Annuler → carte restaurée
3. Clic Accepter → message → Confirmer → fragment accepted + lien séquence
4. Clic Refuser → fragment rejected, QUEUED suivante promue
5. `/notifications/` — vérifier notification au demandeur
