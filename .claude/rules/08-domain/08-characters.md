---
paths:
  - "suddenly/characters/**"
---

# Characters domain rules

- Character statuses: NPC, PC, CLAIMED, ADOPTED (no `FORKED` — a fork leaves the original NPC)
- Link types: Claim (retcon, NPC replaced), Adopt (NPC becomes my PC), Fork (new PC linked)
- Claim requires narrative coherence (the PC could have been there at that moment)
- Adopt forbidden if NPC already claimed or adopted
- All link operations go through `LinkService` — never modify character links directly
- `CharacterLink` has two statuses: `ACTIVE` and `REVOKED` — soft-delete when SharedSequence is published, hard-delete otherwise
- To identify the player who initiated a link, use `link.link_request.requester` (not `link.source.owner` — None for ADOPT where source == target)
- A character can have multiple appearances across games (`CharacterAppearance`)
- SharedSequence tracks shared narrative arcs between linked characters
- Follow model enables cross-instance character subscriptions via AP

## Link lifecycle (DEC-035 — transition at acceptance)

- `LinkService.accept_request` is the single transition point, all atomic: creates the `CharacterLink` (status `ACTIVE`), transitions the target character (NPC → CLAIMED/ADOPTED, ownership transferred on ADOPT), creates a `SharedSequence` draft
- FORK creates a new PC (`source.parent = target`); the original stays NPC, untouched
- Accepting a CLAIM/ADOPT cancels all remaining `QUEUED` requests on that character
- One `PENDING` request at a time; a second is `QUEUED`. Reject/cancel of the `PENDING` promotes the oldest `QUEUED` — always via `LinkService`, never inline in a view
- `SharedSequence` publication goes through `LinkService.publish_sequence`: it flips the sequence to `PUBLISHED` and notifies both parties — it does NOT change character status (already done at acceptance)
  **Why:** transition-at-acceptance is the tested, canonical behavior (`tests/characters/test_link_service.py`); publication is a content milestone, not a status trigger. The rule was corrected to match the code (2026-07-15), not the reverse.

## Character creation (`characters:create`)

- `character_create.html` is the sole creation template — `character_form.html` is edit-only (`character_edit` never passes `character=None`)
- One atomic POST via `services.create_character_with_sheet()` — no nested Django formset
- Nested rows (TraitSet/Trait/Action) reference each other by index before any PK exists → client serializes to a hidden `payload` JSON field, server parses and validates bounds before calling the service
- `Action.character` FK is required; `Action.trait_set` is nullable — an action can span traits across multiple TraitSets ("action transverse")
- Actions without a `trait_set` are "actions transverses" — shown via `character.actions.filter(trait_set__isnull=True)` (`templates/characters/partials/transverse_actions.html`, included in `detail.html` and `traits_editor.html`)

## Report form

- Use single template `games/report_form.html` for both create and edit views
- Distinguish modes via `report` context: `report=None` → create, `report=<instance>` → edit
- Show Cast section only on create (`{% if not report %}`)
- Action buttons depend on `report.status`: draft → "Publish" + "Save draft", published → "Save"

## Character ↔ Game — three distinct relations, never conflate

- `origin_game` (FK, **non-null**) = birth + **AP federation home** — do NOT make nullable
- `GameCast` (`castings`) = **incarnable pool** — who may post/speak in a game
- `CharacterAppearance` = **played presence** in a Report (a posteriori)
- `game.characters` (reverse `origin_game`) and `GameCast` are **different populations** — NOT interchangeable
  - `characters:create` (`create_character_with_sheet`) sets `origin_game` but **no** `GameCast`
  - `GameCast` only from composer-NPC create, posting (`add_to_cast`), cross-cast
- Actor/incarnation surfaces (who may speak) → filter on `GameCast` (`castings__game=game`), never `origin_game` — see `build_actor_pool`
- Game roster display ("characters of this game") → `origin_game` reverse is correct — swapping to `castings` hides standalone-created PCs (regression)
- CLAIM/ADOPT/FORK create **no** `GameCast` and **no** `CharacterAppearance` — only `origin_game` provenance moves

## NPC creation — game master only

- Creating a **brand-new** NPC is reserved to the game master (`is_game_master`, i.e. `game.owner`)
- Gated at both write paths: `cast_add` (HTMX) and the `report-cast` DRF action — the `new_character_name` branch
- Adding an **existing** character to a report cast stays open to the scene author
- The composer "+ Nouveau PNJ" (`create_npc_in_cast`) is already GM-only
- Players never create NPCs — they CLAIM / ADOPT / FORK existing ones
  **Why:** the NPC pool is the GM's authorial surface; players interact with it through link requests, not creation.

## Scene markers → CharacterAppearance

- `RapportMarker` kinds `CHARACTER_APPEARS` / `CHARACTER_LEAVES` require a linked character (`CHARACTER_MARKER_KINDS`)
- `CHARACTER_APPEARS` records a durable `CharacterAppearance` via `record_appearance_from_marker` (`games/services.py`), called from `marker_create`
- Idempotent (`get_or_create` on unique `(character, report)`); role defaults to `SUPPORTING`, an existing role (e.g. `MAIN`) is preserved
- `CHARACTER_LEAVES` records **no** appearance — presence is durable; present/gone display comes from `_scene_departures`, never from deleting the appearance
- Markers are posted per-Rapport from `rapport_item.html` ("+ Marqueur", gated on scene author + not released); form loads via `hx-get marker_create`
- `marker_create` / `marker_delete` gate on the scene **author** (not GM) — an existing character entering/leaving is authorial narration

## `origin_game` is load-bearing for ActivityPub — keep non-null

- `attributedTo` of the Character actor = `character.origin_game.actor_url` (`activitypub/serializers.py`)
- Delivery/signing actor for the character's Create/Update activities = `origin_game` (`activitypub/tasks.py`, `actor_type="Game"`)
- Federated as `suddenly:originGame`; inbound remote characters always get one synthesized (`inbox.py`)
- Nullable `origin_game` breaks AP actor serialization + outbound delivery — never do it

## FORK appears in the parent game's roster — by design, not a bug

- FORK inherits `origin_game` from parent (its AP home) → shows in that game's `game.characters` roster
- This is a product consequence of `origin_game` inheritance, not a listing defect; lineage carried by `parent`
- To hide forks from the parent roster, filter the display (e.g. exclude `parent__isnull=False`) — never swap `game.characters` → `castings`

## Doc/code divergences (aidd_docs/memory/external/claim-adopt-fork.md)

- No `FORKED` status — the enum value was removed (commit `8b092de`); FORK leaves the original `NPC` untouched, lineage carried by `source.parent`
- Claim doc says "PNJ remplacé/Remplacé" — code keeps both characters (target → `CLAIMED`, no deletion/merge)
- Doc "SharedSequence visible dans les deux parties" — `SharedSequence` has **no game FK** (linked only to `CharacterLink`)
