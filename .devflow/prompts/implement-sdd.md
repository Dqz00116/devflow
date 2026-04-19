## Stage 3: Implementation with SDD

Implement feature using Subagent-Driven Development.

### Input:
- PLAN-{workflow_run_id}.md
- DESIGN-{workflow_run_id}.md

### Skills Required:
- `subagent-driven-development`
- `test-driven-development` (used by subagents)

### SDD Cycle:

1. **Dispatch implementer subagent** with full context (plan, design, REQ)
   - Subagent uses `test-driven-development` skill
   - Subagent follows TDD cycle:
     ```
     RED: Write failing test
       ↓
     GREEN: Write minimal code to pass
       ↓
     REFACTOR: Improve while keeping tests green
       ↓
     Repeat
     ```

2. **Review by main agent** (spec compliance FIRST, code quality SECOND)
   - Check spec compliance
   - Check code quality
   - IF issues: fix and re-review

3. **Mark complete**

### Iron Law:
**NO production code without failing test first.**
If violated: DELETE code, restart.

### Gate:
- All tests pass: {test_command}
