## MODE-A: req-approve — Approve Requirement

**Autonomy:** Human confirmation required. Do NOT proceed without explicit user approval.

**Role:**
- **Main Agent**: Present requirement, ask clarifying questions, collect approval.
- **Subagent**: Update requirement status, create feature document.

> **MANDATORY:** Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

---

### Inputs

- `docs/requirements/REQ-{workflow_run_id}.md` — draft requirement

### Outputs

- Updated `docs/requirements/REQ-{workflow_run_id}.md` with `status: approved`
- `docs/features/FEAT-{workflow_run_id}.md` — feature document

### Gate

```
file_exists:docs/requirements/REQ-{workflow_run_id}.md
file_contains:docs/requirements/REQ-{workflow_run_id}.md:status: approved
file_exists:docs/features/FEAT-{workflow_run_id}.md
```

---

### Procedure

1. **Main Agent — Read Requirement.** Read `docs/requirements/REQ-{workflow_run_id}.md` to understand the full scope.

2. **Main Agent — Present to User.**
   - Display the requirement in a clear summary (title, priority, description, acceptance criteria, scope notes).
   - Ask clarifying questions **one at a time**; limit to 2-3 unless the user invites more.
   - After clarifications, ask: *"Do you approve this requirement? Reply with 'approved' or 'yes' to confirm."*
   - Wait for explicit verbal confirmation before proceeding.

3. **Subagent — Update Status and Create Feature Document.** Once approved:
   - Update `docs/requirements/REQ-{workflow_run_id}.md`: change `status: draft` to `status: approved`; update Description/AC if clarifications changed anything.
   - Create `docs/features/FEAT-{workflow_run_id}.md` with YAML frontmatter (id, title, status: approved, req_ref) and sections: Summary, Requirement Reference, Key Decisions (from clarifications).

4. **Main Agent — Verify.** Check REQ has `status: approved`, FEAT file exists with correct REQ reference, clarifications are captured.

5. **Proceed.** Run `devflow done` to advance.
