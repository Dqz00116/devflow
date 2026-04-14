## Stage 3: Implementation with TDD

Implement feature using Test-Driven Development.

### Input:
- PLAN-{workflow_run_id}.md
- DESIGN-{workflow_run_id}.md

### Skills Required:
- `test-driven-development`
- `subagent-driven-development`

### TDD Cycle:
```
RED: Write failing test
  ↓
GREEN: Write minimal code to pass
  ↓
REFACTOR: Improve while keeping tests green
  ↓
Repeat
```

### Iron Law:
**NO production code without failing test first.**
If violated: DELETE code, restart.

### Per Task:
1. Dispatch implementer with full context (plan, design, REQ)
2. Answer questions
3. Subagent implements/tests/commits
4. Dispatch spec reviewer
5. IF issues: fix and re-review
6. Dispatch code quality reviewer
7. IF issues: fix and re-review
8. Mark complete

### Review Order:
Spec compliance FIRST, code quality SECOND

### Gate:
- All tests pass: pytest
