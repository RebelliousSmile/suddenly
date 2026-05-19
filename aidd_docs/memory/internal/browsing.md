---
name: browsing
description: How AI browses the Suddenly project
argument-hint: N/A
scope: frontend
---

# Browser Setup

- **Browsing Tool**: Playwright via `mcp__playwright__*` MCP tools
- **Starting URL**: `http://localhost:8000`
- **Authentication**: Session-based — POST `/accounts/login/` with CSRF token, or `force_authenticate` in API tests
