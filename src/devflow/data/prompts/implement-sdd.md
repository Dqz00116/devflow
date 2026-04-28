## Stage 3: Implementation with SDD

Implement feature using Subagent-Driven Development.

### Input
- docs/superpowers/plans/PLAN-{workflow_run_id}.md
- docs/superpowers/specs/DESIGN-{workflow_run_id}.md
- docs/requirements/REQ-{workflow_run_id}.md

### Your Role: SDD Orchestrator

**Use the `subagent-driven-development` skill.**

You are the orchestrator. You do NOT write production code directly.
Your job: Dispatch -> Review -> Merge.

### SDD Cycle (do not skip any step):

**Step 1: DISPATCH subagent**
- Pass the full Subagent Context (below) to an Agent tool call
- Use subagent_type="general-purpose"
- Include the Input files listed above and the Subagent Context section

**Step 2: REVIEW subagent output**
- Use the `requesting-code-review` superpowers skill to dispatch a code-reviewer
- First pass: SPEC COMPLIANCE -- does the implementation match DESIGN and PLAN?
- Second pass: CODE QUALITY -- clean, correct, well-structured?
- IF issues found: return feedback to subagent, re-review
- IF passes both: approve

**Step 3: MERGE**
- Integrate approved changes
- Run tests to confirm gate
- Mark step complete

### Orchestrator Iron Law:
**Main agent MUST NOT write production code directly.**
If violated: DELETE all code changes, restart from Step 1.

### Gate:
- All tests pass: {test_command}

---

## Subagent Context (pass verbatim to subagent)

### Your Task
Implement the feature described in the Input files using TDD.

### Skill Required
- `test-driven-development`

### TDD Cycle (follow strictly):

RED: Write failing test first
  |
GREEN: Write minimal code to pass
  |
REFACTOR: Improve while keeping tests green
  |
Repeat until all PLAN tasks done

### Subagent Iron Law:
**NO production code without a failing test first.**
If violated: DELETE the code, restart from RED.

### Output
- All implementation files
- All test files
- Run `{test_command}` -- must pass before returning
- Self-review using `requesting-code-review` superpowers skill before submitting to orchestrator
