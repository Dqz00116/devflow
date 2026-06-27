## MODE-A: brainstorm — Brainstorm Design

**Autonomy:** Human confirmation required. User must choose and approve the design approach.

**Role:**
- **Main Agent**: Research context, explore approaches, present options, make recommendation.
- **Subagent**: Research, codebase exploration, write design document.

> **MANDATORY:** Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

---

### Inputs

- `docs/features/FEAT-{workflow_run_id}.md` — approved feature document
- `docs/requirements/REQ-{workflow_run_id}.md` — approved requirement document
- Existing codebase (for context)

### Outputs

- `docs/superpowers/specs/DESIGN-{workflow_run_id}.md` — design document with chosen approach

### Gate

```
file_exists:docs/superpowers/specs/DESIGN-{workflow_run_id}.md
```

---

### Methodology

Use the following brainstorming method **within** DevFlow's controlled process:

**1. Explore Context**
   - Read FEAT and REQ docs to understand scope, purpose, constraints, and success criteria.
   - Dispatch a subagent to explore the relevant codebase: read source files, check for similar patterns, identify key interfaces and dependencies.
   - If the request describes multiple independent subsystems (e.g., chat + file storage + billing + analytics), flag this — don't refine details of a project that needs decomposition. The user should scope the first sub-project before proceeding.

**2. Ask Clarifying Questions (if needed)**
   - Ask questions **one at a time** to fill gaps in understanding.
   - Prefer multiple-choice questions when possible.
   - Focus on: purpose, constraints, success criteria.

**3. Propose 2-3 Approaches with Trade-offs**
   - Formulate **distinct** approaches. Each needs: name, description, pros (3-5), cons (3-5), effort estimate (small/medium/large).
   - Lead with your recommended option and explain why.
   - Apply YAGNI ruthlessly — remove unnecessary features from all designs.

**4. Present Design to User & Get Approval**
   - Display each approach (description, key pros/cons, effort). State your recommendation.
   - Ask: *"Which approach should we proceed with?"* Wait for explicit response.
   - If the user proposes a hybrid, update accordingly.
   - **Do NOT proceed until the user has explicitly approved** — this is DevFlow's human gate.

**5. Write & Finalize Design Document**
   - Dispatch a subagent to create `docs/superpowers/specs/DESIGN-{workflow_run_id}.md`.
   - Draft: frontmatter (id, title, status: draft), sections for each approach, recommendation section.
   - Once approach is chosen: set `status: approved`, mark chosen approach `selected: true`, remove unchosen approaches (or move to appendix), add implementation notes (data flow, key interfaces, error handling, testing strategy).
   - After writing, self-review for: placeholders ("TBD"/"TODO"), internal contradictions, scope creep, ambiguous requirements. Fix inline.

**6. User Reviews the Written Spec**
   - Ask the user to review the spec file before proceeding:
     *"Spec written to `docs/superpowers/specs/DESIGN-{workflow_run_id}.md`. Please review it and let me know if you want any changes."*
   - If changes requested, make them and re-run self-review. Only proceed once the user approves.

**7. Verify**
   - Check DESIGN exists with `status: approved`, chosen approach documented, implementation notes actionable.

**8. Proceed**
   - Run `devflow done`.

### Key Principles

- **Explore alternatives** — Always propose 2-3 approaches before settling.
- **One question at a time** — Don't overwhelm with multiple questions.
- **Incremental validation** — User approves the approach AND the written spec.
- **Design for isolation** — Break the system into units with one clear purpose, well-defined interfaces.
- **Follow existing patterns** — Where the codebase has established conventions, match them.
- **Stay focused** — Don't propose unrelated refactoring. Include only what serves the current goal.
- **DevFlow controls progression** — This step produces the DESIGN doc; DevFlow's gate checks for it. Do NOT invoke other skills or transition workflows — `devflow done` handles advancement.
