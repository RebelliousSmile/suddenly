# 03 — Authentification

## Login (`/accounts/login/`)

```
+------------------------------------------------------------------+
|                         HEADER (visiteur)                        |
+------------------------------------------------------------------+
|                                                                  |
|                  +----------------------------+                  |
|                  |                            |                  |
|                  |       Connexion            |                  |
|                  |                            |                  |
|                  |  Identifiant               |                  |
|                  |  {________________________}|                  |
|                  |                            |                  |
|                  |  Mot de passe              |                  |
|                  |  {________________________}|                  |
|                  |                            |                  |
|                  |  [ ] Se souvenir de moi    |                  |
|                  |                            |                  |
|                  |  [    Se connecter     ]   |                  |
|                  |                            |                  |
|                  |  Pas de compte ?           |                  |
|                  |  S'inscrire                |                  |
|                  |                            |                  |
|                  |  Mot de passe oublie ?     |                  |
|                  |                            |                  |
|                  +----------------------------+                  |
|                                                                  |
+------------------------------------------------------------------+
```

## Signup (`/accounts/signup/`) — US-01

```
+------------------------------------------------------------------+
|                         HEADER (visiteur)                        |
+------------------------------------------------------------------+
|                                                                  |
|                  +----------------------------+                  |
|                  |                            |                  |
|                  |  Rejoindre {{ SITE_NAME }} |                  |
|                  |  {{ SITE_DESCRIPTION }}     |                  |
|                  |                            |                  |
|                  |  Nom d'utilisateur         |                  |
|                  |  {________________________}|                  |
|                  |  Vous serez                |                  |
|                  |  @username@{{ DOMAIN }}    |                  |
|                  |                            |                  |
|                  |  Adresse e-mail            |                  |
|                  |  {________________________}|                  |
|                  |                            |                  |
|                  |  Mot de passe              |                  |
|                  |  {________________________}|                  |
|                  |  @password_strength        |                  |
|                  |                            |                  |
|                  |  Confirmer le mot de passe |                  |
|                  |  {________________________}|                  |
|                  |                            |                  |
|                  |  Regles de l'instance :    |                  |
|                  |  1. Respectez les autres   |                  |
|                  |  2. Utilisez les CW pour   |                  |
|                  |     le contenu sensible    |                  |
|                  |  3. Pas de spam            |                  |
|                  |  Voir toutes les regles -> |                  |
|                  |                            |                  |
|                  |  [x] J'accepte les regles  |                  |
|                  |      de cette instance     |                  |
|                  |                            |                  |
|                  |  [     S'inscrire      ]   |                  |
|                  |                            |                  |
|                  |  Deja un compte ?          |                  |
|                  |  Se connecter              |                  |
|                  |                            |                  |
|                  +----------------------------+                  |
|                                                                  |
+------------------------------------------------------------------+
```

## Logout (`/accounts/logout/`)

```
+----------------------------+
|                            |
|  Etes-vous sur de vouloir  |
|  vous deconnecter ?        |
|                            |
|  [Se deconnecter]          |
|                            |
+----------------------------+
```
