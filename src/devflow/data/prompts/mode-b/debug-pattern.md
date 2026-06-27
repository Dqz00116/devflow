# Debug Phase 2: Pattern Analysis (Autonomous)

## Role

| Role | Responsibilities |
|------|-----------------|
| **Main Agent** | Define comparison dimensions, review differences, determine pattern relevance, confirm completeness. |
| **Subagent(s)** | Find working examples, read reference implementations, compare working vs broken code, check dependency versions, write PATTERN doc. |

Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

## Execution Model

```
Main Agent defines comparison scope (dimensions to compare)
  |-- Dispatches parallel subagents: working examples, code comparison, deps/config, git history
  |-- Main Agent reviews differences
  |     [Relevant pattern found?] --> Confirm --> subagent writes PATTERN doc --> devflow done
  |     [No clear pattern?] --> Adjust dimensions --> dispatch again
```

## Input

- `docs/debug/ROOT-CAUSE-{workflow_run_id}.md`
- Current codebase state

## Output

- `docs/debug/PATTERN-{workflow_run_id}.md`

## Procedure

- **Define comparison dimensions**: Similar working features? Codebase patterns consistent? Past similar bugs (git history)? Reference implementations / docs? Dependency mismatch or config drift?
- **Search working examples** (subagent, parallel): Similar features following same architecture pattern. Reference implementations — does broken code deviate from canonical pattern? Historical fixes via `git log --all --oneline --grep="fix"` in same area.
- **Compare working vs broken** (subagent): Per comparison pair — component paths, differences flagged as relevant vs incidental.
- **Check dependency changes** (subagent): Lock files, manifests, config files — what differs between working and broken environments.
- **Review patterns**: Do differences explain root cause? Recurring pattern (e.g. "null checks missing in async callbacks")? Actionable for a fix?
- **Write output** (subagent): `docs/debug/PATTERN-{workflow_run_id}.md`:
  ```markdown
  # Pattern Analysis - {workflow_run_id}
  ## Comparison Dimensions
  ## Working vs Broken (table: Aspect | Working | Broken | Assessment)
  ## Dependency Changes
  ## Historical Context
  ## Identified Pattern
  ## Implications for Fix
  ```

## Gate

- `file_exists:docs/debug/PATTERN-{workflow_run_id}.md`

## Completion Criteria

- Working vs broken differences clearly documented
- Similar patterns in codebase examined
- Dependency/config drift checked
- Clear pattern linking root cause to code structure identified
