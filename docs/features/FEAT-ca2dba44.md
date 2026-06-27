---
id: FEAT-ca2dba44
title: Fix implement-sdd.md to enforce SDD subagent dispatch
req: REQ-ca2dba44
status: draft
---

## Technical Approach

### Problem

The current `implement-sdd.md` prompt blends SDD orchestration (dispatch subagent → review → merge) and TDD details (RED → GREEN → REFACTOR) in the same prompt. AI agents see the familiar TDD pattern, execute it directly, and skip subagent dispatch.

### Solution

Restructure the prompt into two clear sections with a hard boundary:

**1. Main Agent Instructions (top section)**
- Non-negotiable step order: Dispatch → Review → Merge
- SDD Iron Law: Main agent MUST NOT write production code directly
- Review rubric: spec compliance first, code quality second
- TDD details are NOT shown to main agent — only referenced as "the subagent will use TDD"

**2. Subagent Context (inline, passed via Agent tool prompt)**
- The TDD cycle details (RED → GREEN → REFACTOR) live here
- The "NO production code without failing test first" Iron Law belongs here
- Full context: plan, design, REQ references

### Files Changed

1. `.devflow/prompts/implement-sdd.md` — source prompt
2. `src/devflow/data/prompts/implement-sdd.md` — bundled copy (must stay in sync)

### No Changes To

- `MODE-A.toml` — step structure unchanged
- Gate condition — remains `command_success:{test_command}`
