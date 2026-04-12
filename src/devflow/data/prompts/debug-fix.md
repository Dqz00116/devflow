## Phase 4: Fix Implementation

Implement the minimal fix for the root cause.

### Output:
Update docs/debug/HYPOTHESIS-{workflow_run_id}.md with fix details

### Tasks:
1. Create failing test FIRST:
   - Test should reproduce the bug
   - Test should fail before fix
   - Test should pass after fix

2. Implement single fix:
   - Fix ONLY the root cause
   - No unrelated changes
   - Minimal, focused change

3. Verify fix:
   ```bash
   pytest  # Should pass
   ```

   - Test passes
   - No regressions
   - Original issue resolved

4. Document fix in HYPOTHESIS-{workflow_run_id}.md:
   ## Fix Applied
   File: [path]
   Change: [description]
   Reason: [link to root cause]

5. If fix fails:
   - Attempt < 3: Return to Phase 1 (new investigation)
   - Attempt >= 3: Jump to Phase 4.5 (Question Architecture)

### Gate:
- All tests pass
