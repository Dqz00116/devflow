---
id: PLAN-ca2dba44
title: Fix implement-sdd.md to enforce SDD subagent dispatch
design: DESIGN-ca2dba44
---

## Tasks

- [ ] TASK-001: Rewrite `.devflow/prompts/implement-sdd.md` with Two-Zone structure — add orchestrator role, SDD Iron Law, and isolated subagent TDD context
- [ ] TASK-002: Sync `src/devflow/data/prompts/implement-sdd.md` to match

## Test Strategy

- Manual verification: read the prompt and confirm SDD Iron Law is present, TDD details are in subagent section only, main agent role is "orchestrator"
- Existing test suite passes: `pytest`
