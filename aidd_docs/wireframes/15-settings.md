# 15 — Parametres utilisateur

## Page de parametres (`/settings/`)

Navigation par onglets lateraux.

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Parametres                                                      |
|                                                                  |
|  +----------------+  +--------------------------------------+   |
|  |                |  |                                      |   |
|  | > Profil       |  |  (contenu de l'onglet actif)         |   |
|  |   Compte       |  |                                      |   |
|  |   Securite     |  |                                      |   |
|  |   Langues      |  |                                      |   |
|  |   Notifications|  |                                      |   |
|  |   Federation   |  |                                      |   |
|  |   Donnees      |  |                                      |   |
|  |                |  |                                      |   |
|  +----------------+  +--------------------------------------+   |
|                                                                  |
+------------------------------------------------------------------+
```

### Onglet Profil (redirection vers `/users/{username}/edit/`)

Identique au wireframe `04-profile.md` (edition profil).

### Onglet Compte

```
+--------------------------------------+
|  Compte                              |
|                                      |
|  Nom d'utilisateur                   |
|  {_alice________________________}    |
|  (info) Visible comme @alice         |
|                                      |
|  Adresse e-mail                      |
|  {_alice@example.com____________}    |
|                                      |
|  [Enregistrer]                       |
|                                      |
|  ──────────────────────────────────  |
|                                      |
|  Zone dangereuse                     |
|                                      |
|  [Desactiver mon compte]             |
|  Votre compte sera masque et vos     |
|  followers distants seront notifies  |
|  (Delete activity). Vous pourrez le  |
|  reactiver sous 30 jours.            |
|                                      |
|  [Supprimer definitivement]          |
|  (red) Irreversible. Toutes vos     |
|  donnees seront effacees apres       |
|  un delai de grace de 30 jours.      |
|                                      |
+--------------------------------------+
```

### Onglet Securite

```
+--------------------------------------+
|  Securite                            |
|                                      |
|  Changer le mot de passe             |
|                                      |
|  Mot de passe actuel                 |
|  {______________________________}    |
|                                      |
|  Nouveau mot de passe                |
|  {______________________________}    |
|                                      |
|  Confirmer le nouveau                |
|  {______________________________}    |
|                                      |
|  [Changer le mot de passe]           |
|                                      |
|  ──────────────────────────────────  |
|                                      |
|  Sessions actives                    |
|                                      |
|  (monitor) Firefox, Linux            |
|    Connecte depuis 2h  (session      |
|    actuelle)                         |
|                                      |
|  (smartphone) Safari, iOS            |
|    Derniere activite il y a 3j       |
|    [Revoquer]                        |
|                                      |
+--------------------------------------+
```

### Onglet Langues

```
+--------------------------------------+
|  Langues                             |
|                                      |
|  Langue de mes publications          |
|  {_fr (Francais)______________}      |
|  Les CRs et citations que vous       |
|  publiez seront etiquetes avec       |
|  cette langue.                        |
|                                      |
|  Langues que je veux voir            |
|  [x] Francais                        |
|  [x] English                         |
|  [ ] Deutsch                         |
|  [ ] Espanol                         |
|  [+ Ajouter une langue]              |
|                                      |
|  [ ] Afficher le contenu sans        |
|      langue definie                   |
|  (info) Si decoche, le contenu sans  |
|  etiquette de langue sera masque     |
|  de votre fil.                        |
|                                      |
|  [Enregistrer]                       |
|                                      |
+--------------------------------------+
```

### Onglet Notifications

Identique au wireframe `11-notifications.md` (section parametres).

### Onglet Federation

```
+--------------------------------------+
|  Federation                          |
|                                      |
|  Votre identifiant ActivityPub       |
|  @alice@suddenly.social              |
|  (copy) Copier                       |
|                                      |
|  Cle publique (PEM)                  |
|  +--------------------------------+  |
|  | -----BEGIN PUBLIC KEY-----     |  |
|  | MIIBIjANBgkqhkiG9w0BAQEFAA... |  |
|  | -----END PUBLIC KEY-----       |  |
|  +--------------------------------+  |
|  (info) Utilisee pour verifier vos   |
|  activites sur les instances         |
|  distantes.                          |
|                                      |
|  ──────────────────────────────────  |
|                                      |
|  Instances suivies                   |
|                                      |
|  suddenly.games — 3 acteurs suivis   |
|  mastodon.social — 1 acteur suivi   |
|                                      |
|  ──────────────────────────────────  |
|                                      |
|  Comptes bloques                     |
|                                      |
|  {Bloquer un utilisateur...______}   |
|  (info) Vous ne verrez plus son      |
|  contenu et il ne pourra plus        |
|  interagir avec vous.                |
|                                      |
|  @troll123 — bloque le 5 mars       |
|    [Debloquer]                       |
|                                      |
|  ──────────────────────────────────  |
|                                      |
|  Comptes masques (mute)              |
|                                      |
|  {Masquer un utilisateur...______}   |
|  (info) Son contenu sera masque      |
|  de vos fils mais il pourra encore   |
|  interagir.                          |
|                                      |
|  ──────────────────────────────────  |
|                                      |
|  Instances bloquees (personnel)      |
|                                      |
|  {Ajouter une instance a bloquer}    |
|  (info) Vous ne verrez plus le       |
|  contenu de cette instance.          |
|                                      |
+--------------------------------------+
```

### Onglet Donnees

```
+--------------------------------------+
|  Mes donnees                         |
|                                      |
|  Import / Export d'abonnements       |
|                                      |
|  [Exporter mes follows (CSV)]        |
|  (info) Format CSV compatible        |
|  Mastodon. Contient vos abonnements  |
|  joueurs, parties, personnages.      |
|                                      |
|  [Importer des follows (CSV)]        |
|  (info) Importez un fichier CSV      |
|  Mastodon ou Suddenly. Les comptes   |
|  seront suivis automatiquement.      |
|                                      |
|  ──────────────────────────────────  |
|                                      |
|  Exporter mes donnees completes      |
|                                      |
|  [Telecharger une archive]           |
|  (info) Archive ZIP contenant :      |
|  profil, parties, CRs, citations,    |
|  personnages, liens, abonnements.    |
|  Format : ActivityPub JSON-LD.       |
|  Generation sous 24h.                |
|                                      |
|  ──────────────────────────────────  |
|                                      |
|  Importer des donnees                |
|                                      |
|  [Importer depuis une archive]       |
|  (info) Importez une archive         |
|  Suddenly ou compatible ActivityPub.  |
|  Les doublons seront detectes.       |
|                                      |
|  ──────────────────────────────────  |
|                                      |
|  Alias de compte (migration entrante)|
|                                      |
|  {_@alice@ancien.instance________}   |
|  [Ajouter un alias]                  |
|  (info) Permet a votre ancien        |
|  compte de migrer vers celui-ci.     |
|                                      |
|  ──────────────────────────────────  |
|                                      |
|  Migrer vers une autre instance      |
|                                      |
|  Instance de destination             |
|  {_suddenly.games________________}   |
|                                      |
|  [Initier la migration]              |
|  (alert) Votre profil sera redirige  |
|  vers la nouvelle instance. Vos      |
|  followers seront notifies via       |
|  Move activity. Processus            |
|  irreversible.                       |
|                                      |
+--------------------------------------+
```
