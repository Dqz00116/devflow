# Debug Phase 3: Form and Test Hypothesis (Autonomous)

## Role

| Role | Responsibilities |
|------|-----------------|
| **Main Agent** | Review hypothesis validity, approve test plan, review test results, determine confirmed or needs refinement. |
| **Subagent(s)** | Form testable hypothesis, execute minimal test (ONE variable), document results, write HYPOTHESIS doc. |

Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

## Execution Model

```
Main Agent reviews root cause + pattern analysis
  |-- Approves hypothesis formation --> dispatches subagent
  |     Subagent: "Hypothesis: [X] is root cause because [Y]"
  |-- Main Agent reviews hypothesis
  |     [Testable and falsifiable?] --> Approve test plan --> dispatch subagent to execute
  |     [Vague or unfalsifiable?] --> Reject, refine --> re-dispatch
  |-- Subagent executes minimal test (change ONE variable, run reproduction)
  |     --> Writes HYPOTHESIS doc
  |-- Main Agent reviews results
  |     [Confirmed?] --> signal completion --> devflow done
  |     [Refuted?] --> gate fails --> fail_route back to debug-root-cause
```

## Input

- `docs/debug/ROOT-CAUSE-{workflow_run_id}.md`
- `docs/debug/PATTERN-{workflow_run_id}.md`

## Output

- `docs/debug/HYPOTHESIS-{workflow_run_id}.md`

## Procedure

- **Approve hypothesis formation**: Evidence sufficient for a single testable hypothesis? If too ambiguous, reject.
- **Form hypothesis** (subagent): `Hypothesis: [X] is the root cause because [Y].` Where [X] is a specific code element, [Y] is the causal chain.
- **Propose minimal test** (subagent): Single change description, ONE variable changed (file + exact change), expected outcomes if true vs false.
- **Approve test plan**: Hypothesis falsifiable? Test changes exactly ONE variable? Clear expected outcomes for both branches?
- **Execute minimal test** (subagent): Make ONE change in temporary/reversible way. Run reproduction. Document setup, result, verdict.
- **Write output** (subagent): `docs/debug/HYPOTHESIS-{workflow_run_id}.md`:
  ```markdown
  # Hypothesis Test - {workflow_run_id}
  ## Hypothesis
  ## Minimal Test (Change, File, Expected if true/false)
  ## Test Execution (Setup, Result, Verdict)
  ## Conclusion
  ## Artifacts
  ```

## Gate

- `file_exists:docs/debug/HYPOTHESIS-{workflow_run_id}.md`

## Fail Route

**If refuted or execution fails**: Subagent documents refutation. Gate fails, triggering `fail_route` back to `debug-root-cause`.

## Completion Criteria

- Single, testable, falsifiable hypothesis formed
- Minimal test changed exactly ONE variable
- Test executed and results documented
- Outcome clearly Confirmed or Refuted
- If refuted, document explains what was excluded
