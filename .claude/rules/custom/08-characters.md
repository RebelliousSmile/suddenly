---
paths:
  - "suddenly/characters/**"
---

# Characters domain rules

- Character statuses: NPC, PC, CLAIMED, ADOPTED, FORKED
- Link types: Claim (retcon, NPC replaced), Adopt (NPC becomes my PC), Fork (new PC linked)
- Claim requires narrative coherence (the PC could have been there at that moment)
- Adopt forbidden if NPC already claimed or adopted
- All link operations go through `LinkService` — never modify character links directly
- A character can have multiple appearances across games (`CharacterAppearance`)
- SharedSequence tracks shared narrative arcs between linked characters
- Follow model enables cross-instance character subscriptions via AP
