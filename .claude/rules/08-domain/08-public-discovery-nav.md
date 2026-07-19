---
paths:
  - "templates/components/_nav*.html"
  - "templates/base.html"
  - "templates/**/nav*.html"
---

# Public discovery navigation

- Primary nav (desktop + mobile) = **Home · Stories · Quotes · The project** (v3 menu)
- "The project" = external link to `https://suddenly.social` (marketing/feature site)
- Never add Explorer (`/explore/`) or Jouer (`/feed/`) to the primary nav — dropped in v3
- Public discovery surfaces = `games:stories` + `games:quotes_wall` (public read, no auth)
- Account links (profile, my games, logout) stay in the usermenu auth block
- Apply nav changes to both desktop and mobile — no divergence
- Discovery views still accept `AnonymousUser`; querysets filter to released + public
  **Why:** `/explore/` and `/feed/` routes stay live and anonymous-accessible — only their top-nav entry points were removed; open federation still needs login-free discovery via Stories/Quotes.
