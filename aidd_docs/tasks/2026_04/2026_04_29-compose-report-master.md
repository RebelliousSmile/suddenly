# Master Plan: Compose Report Page

## Overview

- **Goal**: Add a "Commencer" button on the characters list that opens a dedicated mobile-friendly compose page to create a report linked to a character (and its game)
- **Risk Score**: 8/10
- **Branch**: `feat/compose-report`

## Child Plans

| #   | Plan                    | File                                      | Status  | Validated |
| --- | ----------------------- | ----------------------------------------- | ------- | --------- |
| 1   | Report language field   | `./2026_04_29-compose-report-part-1.md`   | done    | [x]       |
| 2   | Compose page            | `./2026_04_29-compose-report-part-2.md`   | pending | [ ]       |
| 3   | Characters integration  | `./2026_04_29-compose-report-part-3.md`   | blocked | [ ]       |

## Validation Protocol

1. Complete Part 1 (migration), run `make check`
2. [ ] Checkpoint 1: migration applied, tests pass
3. Complete Part 2 (compose page), run `make check`
4. [ ] Checkpoint 2: compose page functional, tests pass
5. Complete Part 3 (button integration), run `make check`
6. [ ] Final: end-to-end user journey validated

## Estimations

- **Confidence**: 9/10
- **Duration**: ~2h
