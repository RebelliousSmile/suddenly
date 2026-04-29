# Master Plan: Markdown Editor (EasyMDE)

## Overview

- **Goal**: Replace plain textareas in report forms with EasyMDE Markdown editor, preserving @mention support
- **Risk Score**: 7/10
- **Branch**: `feat/markdown-editor`

## Child Plans

| #   | Plan                    | File                                         | Status  | Validated |
| --- | ----------------------- | -------------------------------------------- | ------- | --------- |
| 1   | Frontend — EasyMDE      | `./2026_04_29-markdown-editor-part-1.md`     | pending | [ ]       |
| 2   | Templates — integration | `./2026_04_29-markdown-editor-part-2.md`     | blocked | [ ]       |

## Validation Protocol

1. Complete Part 1, rebuild bundle, verify `static/dist/` updated
2. [ ] Checkpoint 1: EasyMDE initializes, @mention works in isolation
3. Complete Part 2, verify both forms render editor correctly
4. [ ] Final: write report via compose page end-to-end, mention a character, submit

## Estimations

- **Confidence**: 9/10
- **Duration**: ~2h
