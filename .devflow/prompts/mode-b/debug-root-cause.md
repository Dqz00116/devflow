# Debug Phase 1: Root Cause Investigation (Autonomous)

## Role

| Role | Responsibilities |
|------|-----------------|
| **Main Agent** | Design investigation, review evidence, confirm root cause, sign off. |
| **Subagent(s)** | Gather errors/stack traces, run git log/diff, trace data flow, write ROOT-CAUSE doc. |

Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

## Execution Model

```
Main Agent designs investigation
  |-- Dispatches parallel subagents for each subsystem/data source
  |     Subagents collect evidence (commands, file reads, git)
  |-- Main Agent reviews findings
  |     [Evidence sufficient?] --> Confirm root cause --> signal completion
  |     [Evidence insufficient?] --> Dispatch more subagents --> re-review
  |-- Confirmed --> Main Agent dispatches subagent to write ROOT-CAUSE doc --> devflow done
```

## Input

- User-reported bug description
- Current codebase state (working tree, recent commits)
- Previous debug context (if re-investigation after fail route)

## Output

- `docs/debug/ROOT-CAUSE-{workflow_run_id}.md`

## Procedure

- **Design investigation**: Identify subsystems, what evidence is needed per candidate, can subagents work in parallel.
- **Gather evidence** (subagent): Error message + stack trace with line numbers. Minimal reproduction steps + frequency + environment. `git log --oneline -10` + `git diff HEAD~1`. Data flow trace: origin, transformations, where output goes wrong, expected vs actual at each boundary.
- **Review findings**: Reproducible consistently? Failure point exact? Root cause vs symptom distinguished? Alternative causes ruled out?
- **Root cause confirmation** (by main agent):
  ```
  Root Cause: [one sentence]
  Evidence: [key evidence]
  Alternatives Ruled Out: [candidates eliminated and why]
  ```
- **Write output** (subagent): `docs/debug/ROOT-CAUSE-{workflow_run_id}.md`:
  ```markdown
  # Root Cause Investigation - {workflow_run_id}
  ## Bug Summary
  ## Error Information, Affected files
  ## Reproduction (Steps, Frequency, Environment)
  ## Root Cause, Evidence, Alternatives Ruled Out
  ## Data Flow Trace
  ```

## Gate

- `file_exists:docs/debug/ROOT-CAUSE-{workflow_run_id}.md`

## Completion Criteria

- Issue reliably reproducible
- Exact failure point identified (file, line, function)
- Root cause clearly stated with supporting evidence
- Alternative causes considered and ruled out
