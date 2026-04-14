## Stage 2: Writing Plans

Break down implementation into small, actionable tasks.

### Output File:
docs/superpowers/plans/PLAN-{workflow_run_id}.md

### Tasks:
1. Read `writing-plans` skill

2. Check scope (break into separate plans if needed)

3. Design file structure:
   ```
   src/
   ├── module/
   │   ├── __init__.py
   │   └── feature.py
   tests/
   └── ...
   ```

4. Decompose into bite-sized tasks:
   ## Tasks
   - [ ] TASK-001: [Specific action, 2-5 min]
   - [ ] TASK-002: [Specific action, 2-5 min]

   **Forbidden**: TBD, TODO, "implement later", "similar to X"

5. Define test strategy:
   ## Test Strategy
   - Unit tests for...
   - Integration tests for...

6. Self-review:
   - Spec coverage complete
   - No placeholders
   - Exact file paths specified

### Gate:
- PLAN-{workflow_run_id}.md written
