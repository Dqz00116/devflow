# Debug Phase 4: Implement Fix (Autonomous)

## Role

| Role | Responsibilities |
|------|-----------------|
| **Main Agent** | Review fix scope, ensure changes target only root cause (no unrelated modifications), approve/reject subagent output. |
| **Subagent(s)** | Write failing test first (TDD), implement minimal fix, verify all tests pass, update HYPOTHESIS doc with fix details. |

Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

## Execution Model

```
Main Agent reviews hypothesis + confirms fix scope
  |-- Dispatches subagent for TDD cycle
  |     Subagent: write failing test --> implement minimal fix --> run tests --> document in HYPOTHESIS doc
  |-- Main Agent reviews fix
  |     [Scope correct? root cause only] --> signal completion --> devflow done
  |     [Scope issue?] --> Reject --> dispatch correction --> re-review
  |-- Fail routes:
  |     1-2 failures --> debug-root-cause
  |     3+ failures  --> debug-question (human intervention)
```

## Input

- `docs/debug/HYPOTHESIS-{workflow_run_id}.md` (confirmed hypothesis)
- `docs/debug/ROOT-CAUSE-{workflow_run_id}.md`, `docs/debug/PATTERN-{workflow_run_id}.md`

## Output

- Updated `docs/debug/HYPOTHESIS-{workflow_run_id}.md` with fix details
- Fixed source code (working tree modified)

## Procedure

- **Review fix scope** (main agent): What to fix = exact root cause, nothing more. What NOT to fix = style, adjacent working code, refactoring. Constraint = minimal lines changed, one logical change.
- **TDD cycle** (subagent): (a) Write failing test that reproduces the bug — fails BEFORE fix, passes AFTER, minimal assertions. Run `{test_command}` to confirm failure. (b) Implement minimal fix — root cause only, no formatting/refactoring/speculative changes. (c) Run `{test_command}` — new test passes + no regressions. On 1st/2nd failure: document, main agent decides re-dispatch or route to `debug-root-cause`. On 3rd failure: route to `debug-question`.
- **Document fix** (subagent): Append to `docs/debug/HYPOTHESIS-{workflow_run_id}.md`:
  ```markdown
  ## Fix Applied
  - Root Cause, Fix Summary, File(s) Changed, Change description
  - Test Added, Test Result, Failure Count
  ```
- **Review fix** (main agent): Addresses ONLY root cause? Changes minimal? Test properly reproduces bug? No regressions?

## Gate

- `command_success:{test_command}` — All tests must pass

## Fail Routes

| Failures | Target | Behavior |
|----------|--------|----------|
| 1-2 | `debug-root-cause` | Hypothesis may be wrong; re-investigate |
| 3+ | `debug-question` | **Human intervention required** — stop, present findings |

## Completion Criteria

- Failing test written BEFORE fix
- Fix minimal, targets root cause only
- All tests pass (no regressions)
- Fix documented in HYPOTHESIS document
