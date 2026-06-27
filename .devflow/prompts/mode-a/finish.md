## MODE-A: finish — Complete and Deliver

**Autonomy:** Autonomous (no human gate)

**Role:**
- **Main Agent**: Present delivery options, execute user's choice, create completion document.
- **Subagent**: Create completion document, update requirement status.

> **MANDATORY:** Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

---

### Inputs

- `docs/requirements/REQ-{workflow_run_id}.md` — requirement document
- `docs/evidence/EVIDENCE-{workflow_run_id}.md` — evidence from verification
- Current branch / worktree state

### Outputs

- `docs/completion/COMPLETION-{workflow_run_id}.md` — completion document
- Updated `docs/requirements/REQ-{workflow_run_id}.md` with `status: done`

### Gates

```
file_exists:docs/completion/COMPLETION-{workflow_run_id}.md
file_contains:docs/requirements/REQ-{workflow_run_id}.md:status: done
```

---

### Procedure

1. **Main Agent — Read Context.** Read REQ and EVIDENCE. Check git state (branch name, uncommitted changes, diff summary). Detect workspace environment: determine if this is a normal repo or a worktree.

2. **Main Agent — Verify Completion Readiness.** Before presenting options, confirm: all source files committed (or ready), EVIDENCE exists with raw output, all AC verdicts are PASS. Run the project test command and verify all tests pass. If tests fail, report the failures and stop — do not proceed until tests pass.

3. **Main Agent — Present Delivery Options.** Show the user these options with a summary of feature title, AC pass rate N/N, and branch name:
   - **1. Merge locally** — Merge branch to main, cleanup worktree (and delete branch after successful merge)
   - **2. Push and create PR** — Push to origin, create pull request (keep worktree alive for PR iteration)
   - **3. Keep branch as-is** — No action (preserve worktree)
   - **4. Discard work** — Requires explicit "discard" confirmation

   Wait for user choice. Present only 3 options (omit merge) if on detached HEAD.

4. **Main Agent — Execute User's Choice.**
   - Option 1: Checkout base branch, pull, merge feature branch. Verify tests on merged result. Clean up worktree (if applicable), then `git branch -d <feature-branch>`.
   - Option 2: Push branch with `git push -u origin <feature-branch>`, then create PR using EVIDENCE as description. Do NOT clean up worktree.
   - Option 3: Report "Keeping branch <name>. Worktree preserved at <path>." No cleanup.
   - Option 4: Confirm with "Are you sure? Type 'discard' to confirm." Only proceed on exact match. Clean up worktree, then `git branch -D <feature-branch>`.
   - For worktree cleanup: `cd` to main repo root first, then `git worktree remove <worktree-path>`, then `git worktree prune`. Only clean up worktrees under `.worktrees/` or `worktrees/`; do not touch harness-owned workspaces.

5. **Subagent — Create Completion Document.** Create `docs/completion/COMPLETION-{workflow_run_id}.md` with frontmatter (id, title, status: complete, date, req_ref, evidence_ref) and sections: Summary, Acceptance Criteria (per-criterion PASS/FAIL), Delivery (method + notes).

6. **Subagent — Update Requirement Status.** Update `docs/requirements/REQ-{workflow_run_id}.md`: change `status: approved` to `status: done`.

7. **Main Agent — Verify.** Check COMPLETION exists with correct content, REQ has `status: done`.

8. **Proceed.** Run `devflow done` to complete the workflow.
