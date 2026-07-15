---
kind: brainstorm-validated-spec
feature: Ordre de fiction des Report (chaînage inter-scènes + flashbacks)
status: validated
created_at: 2026-07-15
app: app/ (Django `suddenly`, module `games`)
---

# Spec validée — Ordre de fiction des `Report`

> Sortie du brainstorm (aidd-refine:01), validée par l'utilisateur. Sert d'entrée au planner.
> N'implémente rien : décrit le quoi et les invariants, pas le découpage en milestones.

## Problème

L'ordre de publication d'un `Report` (`published_at`) n'est pas l'ordre de la fiction.
On veut un **ordre de fiction explicite**, indépendant de `published_at` / `created_at` /
`session_date`, matérialisé par un chaînage entre scènes, plus la capacité de marquer des
**flashbacks** (scènes antérieures dans la chronologie interne).

## Décisions figées

- **Ordre de fiction = FK auto-référentiel** `previous_report` sur `Report` (source de vérité
  unique). La relation inverse `next_reports` donne les suites → **bifurcations gratuites**
  (arbre/forêt). L'ordre de publication n'y touche jamais.
- **Bifurcations conservées** (plusieurs suites par report). Aucune contrainte DB en plus ;
  UI branches optionnelle (rendre la mainline d'abord).
- **Flashback = étiquette in-chain** : une scène flashback reste dans la chaîne de lecture
  (elle a un `previous_report`), simplement marquée « antérieure ». `temporal_anchor` optionnel.
- **Fédération** : le lien voyage en **IRI mou** sous le namespace `suddenly:`. Aucun FK dur
  ne traverse la fédération. Bifurcations et flashbacks fédèrent sans logique dédiée.
- **`on_delete` du prédécesseur = `SET_NULL`** (la descendance devient racine ; pas de cascade).
- Aucune logique métier dans le modèle → services (règle projet `03-django-models.md`).

## Modèle (cible)

```python
class ReportTemporalKind(models.TextChoices):
    NORMAL = "normal", _("Normal")
    FLASHBACK = "flashback", _("Flashback")            # antérieur à l'ancre
    FLASHFORWARD = "flashforward", _("Flashforward")   # postérieur (anticipation)

class Report(BaseModel):
    # Axe lecture
    previous_report = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="next_reports",
    )
    previous_report_iri = models.URLField(max_length=500, null=True, blank=True)
    branch_order = models.PositiveIntegerField(default=0)
    # Axe chronologie
    temporal_kind = models.CharField(
        max_length=20, choices=ReportTemporalKind.choices,
        default=ReportTemporalKind.NORMAL,
    )
    temporal_anchor = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="temporal_referrers",
    )
    temporal_anchor_iri = models.URLField(max_length=500, null=True, blank=True)
    temporal_label = models.CharField(max_length=120, blank=True)

    class Meta:
        # ordering existant CONSERVÉ (admin/listes) — l'ordre de fiction passe par le service
        ordering = [
            models.F("session_date").asc(nulls_last=True),
            models.F("published_at").desc(nulls_last=True),
            "-created_at",
        ]
        constraints = [
            models.CheckConstraint(
                name="report_previous_local_xor_remote",
                check=~models.Q(previous_report__isnull=False, previous_report_iri__gt=""),
            ),
            models.CheckConstraint(
                name="report_anchor_local_xor_remote",
                check=~models.Q(temporal_anchor__isnull=False, temporal_anchor_iri__gt=""),
            ),
        ]
        indexes = [
            models.Index(fields=["game", "published_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["previous_report"]),
        ]
```

## Invariants (validés dans un service / `clean`, testables)

- `previous_report != self` et `temporal_anchor != self` (pas d'auto-référence).
- **Pas de cycle** dans la chaîne `previous_report` (remontée `O(profondeur)`).
- `previous_report.game_id == self.game_id` (idem `temporal_anchor`) — même partie.
- `temporal_kind == NORMAL` ⟹ `temporal_anchor` + `temporal_label` vides ;
  une ancre/label exige `temporal_kind != NORMAL`.
- XOR local/remote sur `previous_*` et `temporal_anchor_*` (déjà en CheckConstraint).

## Service de lecture

- `fiction_thread(game) -> list[Report]` : DFS **mainline-first**
  (tri des enfants par `branch_order`, `session_date`, `created_at`).
- Racine = `previous_report` **et** `previous_report_iri` nuls.
- Flashbacks inclus **à leur place** dans la chaîne, badgés `temporal_kind` + `temporal_label`.
- `select_related("author")` + `prefetch_related("next_reports")`.
- `set_previous(report, new_previous)` : insertion/déplacement en réécrivant au plus 2 arêtes,
  après validation des invariants.

## Fédération

### Émission

- Dans **`serialize_report()`** (chemin actif), sous namespace `suddenly:` déjà présent au `@context` :
  - `suddenly:previousReport` = `prev.ap_id` ou URL locale, sinon `previous_report_iri`.
  - `suddenly:temporalKind` (si ≠ normal) + `suddenly:temporalAnchor` (IRI) + `suddenly:temporalLabel`.

### Réception — CÂBLÉE (périmètre étendu)

- Aujourd'hui `inbox.handle_create` (inbox.py:315) ne route que `Character` ; les `Article`/Report
  entrants sont loggés puis ignorés. **On câble l'ingestion des reports distants.**
- Ajouter le routage `obj_type == "Article"` → `_handle_create_report(activity, obj)`, calqué sur
  `_handle_create_character` (tolérant, idempotent) :
  - Skip si `Report.objects.filter(ap_id=...).exists()` (idempotence, cf. `ProcessedActivity`).
  - Résoudre l'auteur distant via `attributedTo` (`get_or_create_remote_user`) et la partie via
    `context` (Game distant `get_or_create`, motif `_handle_create_character`).
  - Persister `remote=True`, `ap_id`, `content`, `title`, `published_at`, visibilité.
- **Résolution IRI→FK (dans le périmètre)** : lire `suddenly:previousReport` / `suddenly:temporalAnchor` :
  - Écrire l'IRI dans `previous_report_iri` / `temporal_anchor_iri`.
  - Si l'IRI correspond à un `Report` (local ou distant) déjà connu par `ap_id`, **relier aussi le FK**
    (`previous_report` / `temporal_anchor`) ; sinon laisser l'IRI seul (résolution différée possible
    quand la scène ancre arrive plus tard).
  - Tolérant : bloc absent = no-op ; malformé = ignoré. Respecter le XOR local/remote.
- Idempotence : ré-ingestion d'un `ap_id` connu = no-op (pas de doublon, pas d'écrasement destructif).

## Suppression du legacy (périmètre étendu)

- `build_note()` (activities.py:78) et `build_create_activity()` (activities.py:118) sont du **code
  mort** — `build_create_activity()` n'est référencé nulle part (ni code, ni tests). Les **supprimer
  tous les deux**, avec leurs imports/exports éventuels.
- Vérifier qu'aucun test ne les importe (grep : aucun aujourd'hui) ; retirer d'un éventuel `__all__`.
- Après suppression : `ruff check` + `mypy` propres, suite de tests activitypub verte.

## Poids fonctionnel des posts ouverture / clôture (UI)

- Ouverture (marker `RapportMarker` `START`) → `« ← Précédemment : {previous_report.title} »`
  + badge flashback éventuel.
- Clôture (`RapportKind.CLOSURE`) → `« Suite → »` : mainline puis branches (`next_reports`).
- La donnée reste sur `Report` ; les posts ne stockent aucun id, ils *rendent* le lien.

## Migration

- Additive, champs nullables, **aucun backfill obligatoire**.
- Backfill optionnel : chaîner les scènes existantes de chaque partie par `session_date`
  croissant (ordre de fiction initial = chronologique).

## Points d'attention pour le plan

- Champs AP posés uniquement sur le chemin actif `serialize_report()`. `build_note()` /
  `build_create_activity()` sont supprimés (voir section « Suppression du legacy »), pas contournés.
- L'ingestion des reports distants est désormais **dans le périmètre** (M réception câblé), pas un
  helper dormant. Réutiliser strictement le patron `_handle_create_character` (idempotence par
  `ap_id`, `get_or_create_remote_user`, Game distant `get_or_create`).
- Règles projet à respecter : `03-django-models.md`, `08-activitypub.md`,
  `ap-pivots-django-activitypub.md` (idempotence inbox, signature avant traitement, IRI mou),
  tests `assertNumQueries`.
