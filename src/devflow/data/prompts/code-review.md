## Stage 4: Code Review

Review implementation against spec and quality standards.

### Input:
- PLAN-{workflow_run_id}.md
- DESIGN-{workflow_run_id}.md

### Tasks:
1. Read `requesting-code-review` skill

2. Get change context:
   ```bash
   BASE_SHA=$(git rev-parse HEAD~1)
   HEAD_SHA=$(git rev-parse HEAD)
   ```

3. Dispatch code-reviewer with:
   - Implementation code
   - Plan document
   - Git SHAs

4. Process feedback:
   - Critical: Fix immediately
   - Important: Fix before proceeding
   - Minor: Log for later

### Gate:
- Critical issues resolved
- User approved (if required)
