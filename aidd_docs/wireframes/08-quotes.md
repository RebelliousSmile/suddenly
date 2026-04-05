# 08 — Citations (Quotes)

## Section citations sur fiche personnage — US-08

Integree dans `/characters/{slug}/` (voir 07-characters.md).

```
+------------------------------------------------------------------+
|                                                                  |
|  Citations (2)                  [+ Ajouter une citation]         |
|                                                                  |
|  id="quote-form-container"                                       |
|  (vide par defaut, rempli par HTMX)                             |
|                                                                  |
|  id="quote-list"                                                 |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |  |  "Les mythes ne meurent pas, ils changent                |  |
|  |  |   simplement de visage."                                 |  |
|  |  |                                                          |  |
|  |  |  Dans le bar des Reflets, face a l'Oracle.               |  |
|  |  |                                                          |  |
|  |  |  — Viktor, ajoutee par @alice                            |  |
|  |  |    depuis Session 12 : L'Oracle brise                    |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |  |  "Je reviendrai. Les gens comme moi                      |  |
|  |  |   reviennent toujours."                                  |  |
|  |  |                                                          |  |
|  |  |  — Viktor, ajoutee par @bob                              |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
```

## Formulaire d'ajout (partial HTMX)

Clic sur `[+ Ajouter]` :
`hx-get="/characters/{slug}/quotes/add/"` -> `#quote-form-container`

```
+------------------------------------------------------------+
|                                                            |
|  Nouvelle citation pour Viktor                             |
|                                                            |
|  La replique                                               |
|  {________________________________________________________}|
|  {________________________________________________________}|
|  {________________________________________________________}|
|                                                            |
|  Contexte (optionnel)                                      |
|  {________________________________________________________}|
|  {________________________________________________________}|
|                                                            |
|  Visibilite            Langue                              |
|  [Publique v]          {_fr___}                            |
|                                                            |
|  [Enregistrer]  Annuler                                    |
|                                                            |
+------------------------------------------------------------+
```

### Comportement HTMX

1. `[+ Ajouter]` fait `hx-get` -> formulaire injecte dans `#quote-form-container`
2. `[Enregistrer]` fait `hx-post` -> nouvelle `@quote_card` injectee en `afterbegin` dans `#quote-list`
3. `Annuler` fait `hx-get` (liste) -> vide `#quote-form-container`
4. Erreur 422 -> formulaire avec erreurs re-injecte dans `#quote-form-container`

### Visibilite

- **Publique** : visible par tous, federee via ActivityPub
- **Privee** : visible uniquement par l'auteur (badge cadenas)
- **Ephemere** : non persistee au-dela de la session, non listee (badge horloge)
