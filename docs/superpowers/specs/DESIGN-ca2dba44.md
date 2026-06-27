---
id: DESIGN-ca2dba44
title: Fix implement-sdd.md prompt structure for SDD enforcement
status: draft
---

## Problem Summary

`implement-sdd.md` blends SDD orchestration and TDD details in one prompt. AI reads it, recognizes the TDD pattern, and executes TDD directly — skipping subagent dispatch entirely.

## Approach A: Two-Zone Prompt (Recommended)

Single file with a hard boundary between main agent duties and subagent context.

```
## Your Role: SDD Orchestrator

### MANDATORY ORDER (do not skip):
1. DISPATCH subagent with context below
2. REVIEW subagent output (spec first, code second)
3. MERGE approved changes

### Iron Law:
**Main agent MUST NOT write production code directly.**
Violation: discard all changes, dispatch subagent.

---

## Subagent Context (pass verbatim to Agent tool)
...
TDD cycle details live here
...
```

**Pros:**
- Single file, easy to maintain
- Main agent gets a clear role boundary
- Iron Law explicitly forbids direct coding
- Subagent context is reusable via copy-paste into Agent tool

**Cons:**
- TDD details still visible to main agent (mitigated by role framing)
- Depends on AI compliance (no structural enforcement)

## Approach B: Separate Subagent Prompt File

Split into two files: `implement-sdd.md` (orchestrator) + `implement-sdd-subagent.md` (TDD worker).

**Pros:** Complete separation, main agent never sees TDD details
**Cons:** Two files to maintain, harder to discover, version skew risk

## Approach C: Token-Level Enforcement Only

Keep current structure but add stronger "DO NOT WRITE CODE" language throughout.

**Pros:** Minimal diff
**Cons:** Same root cause — AI still sees TDD as its own task. Unlikely to work.

## Recommendation

**Approach A** — Two-Zone Prompt. It fixes the root cause (role confusion) with minimal structural change. The key insight: tell the main agent WHAT it IS (SDD orchestrator), not just WHAT to DO (TDD steps). The Iron Law "no direct code" paired with a clear "your role is orchestrator" framing creates the behavior change.
