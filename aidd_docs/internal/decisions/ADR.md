# Architecture Decision Records

| ID | Decision | Feature | Status | Date |
| --- | --- | --- | --- | --- |
| DEC-001 | Auth via django-allauth | Authentification | Accepted | 2026-03-05 |
| DEC-002 | Suppression de compte modèle Mastodon | Compte & Profil | Accepted | 2026-03-05 |
| DEC-003 | Migration de compte complète | Compte & Profil | Accepted | 2026-03-05 |
| DEC-004 | Parties publiques ou privées | Parties | Accepted | 2026-03-05 |
| DEC-005 | Fils d'actualité personnel + local au MVP | Découverte | Accepted | 2026-03-05 |
| DEC-006 | Citations éphémères à durée fixe 24h | Citations | Accepted | 2026-03-05 |
| DEC-007 | Statut QUEUED pour LinkRequest | Liens | Accepted | 2026-03-05 |
| DEC-008 | Statut REVOKED pour CharacterLink | Liens | Accepted | 2026-03-05 |
| DEC-009 | Fork en chaîne sans limite de profondeur | Liens | Accepted | 2026-03-05 |
| DEC-010 | SharedSequence en discussion asynchrone libre | SharedSequence | Accepted | 2026-03-05 |
| DEC-011 | Lien en suspens tant que SS non publiée | SharedSequence | Accepted | 2026-03-05 |
| DEC-012 | Fédération MVP basique read-only | Fédération | Accepted | 2026-03-05 |
| DEC-013 | Détection d'instances Suddenly via NodeInfo | Fédération | Accepted | 2026-03-05 |
| DEC-014 | Timeout des demandes cross-instance à 30 jours | Fédération | Accepted | 2026-03-05 |
| DEC-015 | Compatibilité Mastodon read-only | Fédération | Accepted | 2026-03-05 |
| DEC-016 | Soft delete pour le contenu modéré | Modération | Accepted | 2026-03-05 |
| DEC-017 | Transfert de signalement cross-instance post-MVP | Modération | Accepted | 2026-03-05 |
| DEC-018 | Alignement crypto standards Fediverse | ActivityPub | Accepted | 2026-03-06 |
| DEC-019 | factory-boy pour génération de données de test | Testing | Accepted | 2026-03-06 |
| DEC-020 | Cache clés publiques AP via table DB | ActivityPub | Accepted | 2026-03-06 |
| DEC-021 | Rate limiting inbox par instance | ActivityPub | Accepted | 2026-03-06 |
| DEC-022 | Namespace AP propre à Suddenly | ActivityPub | Accepted | 2026-04-05 |
| DEC-023 | Fichiers .mo versionnés, compilation via babel | i18n | Accepted | 2026-04-28 |
| DEC-024 | Pas de chaînes UI en dur dans les settings Django | i18n | Accepted | 2026-04-28 |
| DEC-025 | Rôle is_admin distinct de is_staff | GMH admin panel | Accepted | 2026-04-29 |
| DEC-026 | InstanceSettings singleton pour config d'instance | GMH admin panel | Accepted | 2026-04-29 |
| DEC-027 | Tags en ManyToManyField vers core.Tag, pas JSONField | Tags | Accepted | 2026-04-29 |
| DEC-028 | build_*_queryset en services publics, pas helpers privés | Explorer | Accepted | 2026-04-29 |
| DEC-029 | Explorer et Jouer hors du bloc auth dans la nav | Explorer | Accepted | 2026-04-29 |
| DEC-030 | EasyMDE comme éditeur Markdown dans les reports | Report editor | Accepted | 2026-04-29 |
| DEC-031 | static/dist/ versionné dans git (déploiement sans Node) | Déploiement | Accepted | 2026-04-29 |
| DEC-032 | Template unifié report_form.html pour create + edit | Report editor | Accepted | 2026-04-29 |
