## MODE-A: req-create — Create Requirement Document

**Autonomy:** Autonomous (no human gate)

**Role:**
- **Main Agent**: Scope definition, requirement structuring, user intent capture.
- **Subagent**: File I/O, document creation.

> **MANDATORY:** Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

---

### Inputs

- User conversation / problem statement (from session context)
- Existing docs/ directory structure

### Outputs

- `docs/requirements/REQ-{workflow_run_id}.md` — structured requirement document

---

### Procedure

1. **Main Agent — Capture Scope.** Analyze the problem statement. Extract: feature name, problem statement, scope boundaries (in/out), priority. Do NOT design solutions — focus on WHAT, not HOW.

2. **Main Agent — Decompose into Requirements.**
   - Write a concise **Description** (problem, audience, expected outcome).
   - Write **Acceptance Criteria** — each must be specific, verifiable, independent; prefixed with `- [ ]`.
   - Write **Notes** for constraints, dependencies, open questions.

3. **Subagent — Create the Requirement File.** Create `docs/requirements/REQ-{workflow_run_id}.md` with YAML frontmatter (id, title, status: draft, priority) plus the Description, Acceptance Criteria, and Notes sections. Do NOT include implementation details.

4. **Main Agent — Verify.** Check file exists, frontmatter is valid YAML, criteria are testable, no implementation details leaked. If verification fails, dispatch a fix subagent, then re-verify.

5. **Proceed.** Run `devflow done` to advance.

---

### Gate

```
file_exists:docs/requirements/REQ-{workflow_run_id}.md
```
