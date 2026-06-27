# Debug Phase 5: Verify Fix (Autonomous)

## Role

| Role | Responsibilities |
|------|-----------------|
| **Main Agent** | Confirm verification sufficiency, approve regression prevention strategy, review all results, sign off. |
| **Subagent(s)** | Run comprehensive tests (original, edge cases, related functionality, full suite), document results, write VERIFICATION doc, recommend regression tests. |

Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

## Execution Model

```
Main Agent defines verification criteria
  |-- Dispatches parallel subagents:
  |     A: original fix test + edge cases
  |     B: related functionality tests
  |     C: full test suite {test_command}
  |     D: regression test opportunities
  |-- Main Agent reviews all results
  |     [All pass?] --> Confirm --> subagent writes VERIFICATION doc --> devflow done
  |     [Failures?] --> dispatch fix subagent --> route to debug-fix or debug-root-cause
```

## Input

- All previous debug documents from this run
- Fixed codebase state

## Output

- `docs/debug/VERIFICATION-{workflow_run_id}.md`

## Procedure

- **Define verification criteria**: Original reproduction passes. Edge cases tested (boundary values, error inputs, concurrency). Related functionality covered. Full suite passes. Regression tests considered.
- **Run comprehensive tests** (subagents, parallel):
  - **Subagent A**: Run fix test + edge cases (empty input, null, boundaries, load). Document each.
  - **Subagent B**: Identify + test modules sharing data flow/call-chain/pattern with fixed code.
  - **Subagent C**: Run `{test_command}` — full output, no truncation. Capture failure message + file + line on any fail.
- **Review results**: ALL pass in all categories = proceed. ANY failure = fix incomplete / regression — route to debug-fix or debug-root-cause (no fail route here — regression, not hypothesis failure).
- **Consider regression prevention** (subagent): Is bug in critical path? Frequently changed code? Would regression test have caught it? If yes, add it.
- **Write output** (subagent): `docs/debug/VERIFICATION-{workflow_run_id}.md`:
  ```markdown
  # Verification Report - {workflow_run_id}
  ## Fix Summary
  ## Verification Results (Original test, Edge cases, Related functionality, Full suite)
  ## Regression Prevention (Added? Rationale)
  ## Conclusion
  ```

## Gates

- `file_exists:docs/debug/VERIFICATION-{workflow_run_id}.md`
- `command_success:{test_command}`

## Completion Criteria

- Original reproduction no longer triggers the bug
- Edge cases tested and pass
- Related functionality not broken
- Full test suite passes
- Regression prevention considered and documented
- VERIFICATION doc captures raw, unedited test output
