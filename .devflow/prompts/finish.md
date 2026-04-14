## Stage 7: Finish

Complete the workflow and present delivery options.

### Output File:
docs/completion/COMPLETION-{workflow_run_id}.md

### Tasks:
1. Read `finishing-a-development-branch` skill

2. Verify all complete:
   - All tests pass
   - Evidence collected
   - Code reviewed
   - Documentation updated

3. Present options to user:

   **Delivery Options:**
   1. Merge locally
      → Merge branch to main
      → Cleanup worktree

   2. Push and create PR
      → Push branch to origin
      → Create pull request

   3. Keep branch as-is
      → Do nothing, branch remains

   4. Discard work
      → Requires "discard" confirmation

4. Execute user choice

5. Create completion document:

   ## Summary
   - Feature: [Name]
   - Status: Complete
   - Evidence: docs/evidence/EVIDENCE-{workflow_run_id}.md

6. Update requirement:
   - Set REQ-{workflow_run_id}.md status: done

### Gate:
- COMPLETION-{workflow_run_id}.md created
