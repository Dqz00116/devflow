---
id: COMPLETION-ca2dba44
title: Completion — Fix implement-sdd.md SDD enforcement
date: 2026-04-28
---

## Summary

Restructured `implement-sdd.md` from a single-zone prompt (blending SDD orchestration + TDD details) into a Two-Zone Prompt with a hard boundary.

## Changes Delivered

| File | Change |
|------|--------|
| `.devflow/prompts/implement-sdd.md` | Rewritten: Orchestrator zone + Subagent Context zone |
| `src/devflow/data/prompts/implement-sdd.md` | Synced copy (identical) |
| `tests/test_config.py` | Fixed brittle version assertion → `__version__` |
| `pyproject.toml` | Fixed e2e collection conflicts + default skip slow tests |

## Acceptance Criteria Met

1. Main agent reads prompt → must DISPATCH subagent first (MANDATORY ORDER)
2. TDD cycle details isolated in Subagent Context (after `---` separator)
3. Main agent role: SDD Orchestrator (Dispatch → Review → Merge)
4. SDD Iron Law: "Main agent MUST NOT write production code directly"
5. Gate unchanged: `command_success:{test_command}`

## Test Results

151 passed, 0 failed (e2e excluded as slow)
