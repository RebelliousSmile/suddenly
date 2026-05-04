# Master Plan: US-16 — Revoke Accepted Link

## Overview

- **Goal**: Proper CharacterLink revocation — status field, service extraction, notification, and UI entry points
- **Risk Score**: 5/10
- **Branch**: `feat/us-16-revoke-link`

## Child Plans

| #   | Plan                        | File                                        | Status     | Validated |
| --- | --------------------------- | ------------------------------------------- | ---------- | --------- |
| 1   | Model + Service + Notify    | `2026_05_04-#18-revoke-link-part-1.md`      | pending    | [ ]       |
| 2   | UI entry points             | `2026_05_04-#18-revoke-link-part-2.md`      | blocked    | [ ]       |

## Validation Protocol

1. Complete Part 1, run `make check`
2. [ ] Checkpoint 1: revocation works end-to-end via direct URL, notification sent
3. Unblock Part 2
4. [ ] Final: revoke button reachable from character detail and GM dashboard

## Estimations

- **Confidence**: 9/10
- **Duration**: 3-4h total
