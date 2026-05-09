# LLM thoughts — memory governance intentions

Captured 2026-05-08 during the rework of `.claude/skills/reconcile-normative/SKILL.md` and the migration purge of DEC-025/026/027/028/031.

## Load probability = weight

- `aidd_docs/memory/*.md` (root) is auto-loaded into every conversation
- `aidd_docs/memory/internal/*`, `aidd_docs/memory/external/*` load only on explicit request
- `.claude/rules/*` load when a touched file matches `paths:` glob
- `aidd_docs/internal/decisions/*` (ADRs) are never auto-loaded
- An ADR's normative weight on code being written **now** is near zero
- Therefore: a decision must land in a rule or in root memory to bind future code

## Memory bloat is a silent risk

- The LLM may skip content unpredictably as memory grows
- We do not know in advance what it will skip
- Conclusion: the bar for adding to memory is **"without this, the LLM makes a wrong decision"** — not "this is interesting context"

## Binary triage on every decision

- Important enough → migrate to root memory or to a rule
- Otherwise → full deletion (git history is the revert path)
- Never: "keep as archive just in case"

## Archive cost asymmetry

- Revert from archive: ~1 % of cases
- Memory load tax: 100 % of reads
- Stub < archive < pure deletion + git history
- This generalizes: any "lightweight reference" still costs at every load

## Rule vs memory split

- Path-scopable + verifiable at write-time → `.claude/rules/<cat>/<n>-<topic>.md`
- Transverse, conceptual, or natural glob too broad (`**/*.vue` alone) → `aidd_docs/memory/`

## Bullet shaping

- Memory bullets: imperative (`Always X` / `Never Y` / `Must Z`), 3-15 words
- Rationale on separate indented `**Why:**` line, skipped when self-evident
- Rule bullets: 3-7 words, no inline rationale (per `01-standards/1-rule-writing.md`)
- Chain migrations consolidate rationale at H3 intro, not per bullet
- No `(cf. DEC-XYZ)` source trace: the pointer dies the moment the source is deleted, and keeping the source contradicts the binary-triage rule

## Default fate after migration

- Pure deletion of the source — stub only on explicit user request
- Encoded twice in `reconcile-normative/SKILL.md`: Phase C step 5 content shaping + Phase C step 7 confirmation prompt

## Concrete actions taken this session

- 13 files in `aidd_docs/memory/external/` audited and migrated/deleted (dir emptied, then this file added)
- 5 ADRs deleted (DEC-025, 026, 027, 028, 031) after their rules absorbed the binding content
- 4 rule files cleaned of dead `## Source` sections
- `aidd_docs/internal/ADR.md` index trimmed accordingly
