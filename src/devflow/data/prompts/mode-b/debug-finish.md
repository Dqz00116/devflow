# Debug Phase 6: Complete Debug (Autonomous)

## Role

| Role | Responsibilities |
|------|-----------------|
| **Main Agent** | Confirm delivery completeness, review completion doc, initiate cross-workflow transition to MODE-A. |
| **Subagent(s)** | Create COMPLETION doc, compile final summary, present to user. |

Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

## Execution Model

```
Subagent compiles all debug artifacts into completion document
  |-- Main Agent reviews for completeness and accuracy
  |     [Complete?] --> Subagent presents summary to user --> devflow done
  |     [Incomplete?] --> dispatch correction --> re-review
  |       --> devflow done triggers: MODE-B:debug-finish --> MODE-A:write-plan
```

## Input

- `docs/debug/ROOT-CAUSE-{workflow_run_id}.md`
- `docs/debug/PATTERN-{workflow_run_id}.md`
- `docs/debug/HYPOTHESIS-{workflow_run_id}.md`
- `docs/debug/VERIFICATION-{workflow_run_id}.md`
- All other debug artifacts from this run

## Output

- `docs/debug/SUMMARY-{workflow_run_id}.md`
- Presentation to user

## Procedure

- **Compile summary document** (subagent): `docs/debug/SUMMARY-{workflow_run_id}.md`:
  ```markdown
  # Debug Summary - {workflow_run_id}
  ## Bug [one line]
  ## Debug Summary (Root Cause, Pattern Identified, Fix Applied, Verification)
  ## Artifacts (table: Document | Path)
  ## Next Steps
  ```
- **Review completion document**: All four phases have output documents? Every doc exists on disk? Summary accurate? Verification confirms all tests pass?
- **Present summary to user** (subagent):
  ```
  Bug fixed! Summary:
  - Root cause: [brief]
  - Fix applied: [brief]
  - All tests pass: [result]
  The fix requires proper planning, review, and verification.
  You will be transitioned to MODE-A:write-plan.
  To proceed, run: devflow done
  ```
- **Signal completion**: `devflow done` checks gate (`file_exists`), advances to `next = "MODE-A:write-plan"`.

## Gate

- `file_exists:docs/debug/SUMMARY-{workflow_run_id}.md`

## Cross-Workflow Transition

After success, workflow engine transitions **automatically** to `MODE-A:write-plan`. `workflow_run_id` preserved for cross-referencing all debug artifacts.

## Completion Criteria

- All debug phase documents exist on disk
- SUMMARY doc summarizes the full debug run
- User presented with clear summary
- Workflow transitions to MODE-A:write-plan
