## MODE-A: write-plan — Write Implementation Plan

**Autonomy:** Autonomous (no human gate)

**Role:**
- **Main Agent**: Task decomposition, file structure design, test strategy definition, orchestration.
- **Subagent**: Write plan document.
- **Review Subagent**: Check plan vs specification consistency.

> **MANDATORY:** Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

---

### Inputs

- `docs/requirements/REQ-{workflow_run_id}.md` — approved requirement
- `docs/superpowers/specs/DESIGN-{workflow_run_id}.md` — approved design spec

### Outputs

- `docs/superpowers/plans/PLAN-{workflow_run_id}.md` — implementation plan
- State variable `review_plan_spec_consistency_passed` set to `true`

### Gates

```
file_exists:docs/superpowers/plans/PLAN-{workflow_run_id}.md
state_set:review_plan_spec_consistency_passed
```

---

### Procedure

1. **Main Agent — Read Inputs.** Read REQ and DESIGN. If the feature covers multiple independent subsystems, split into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

2. **Main Agent — Design File Structure.** Before defining tasks, map out every file to create or modify. Use exact file paths (no placeholders). Structure as a tree diagram. Design units with clear boundaries: each file has one responsibility. Prefer smaller, focused files. Follow existing codebase patterns.

3. **Main Agent — Decompose into Bite-Sized Tasks.** Break implementation into tasks using `- [ ] TASK-NNN: [action, 2-5 min]`. Each task is the smallest unit that carries its own test cycle. Fold setup, config, scaffolding into the task whose deliverable needs them. Each task must produce an independently testable deliverable. Format each task as:
   - **Files:** exact paths for Create / Modify / Test
   - **Interfaces:** what it consumes from previous tasks, what it produces for later tasks
   - **Steps:** actionable `- [ ]` items with code, commands, and expected output
   - **No TBD/TODO/"implement later"** — every step contains the actual content. Never write "add appropriate error handling" without showing the code. If two steps repeat logic, repeat the code — tasks may be read out of order.

4. **Main Agent — Define Test Strategy.** Specify unit tests (which modules, scenarios), integration tests, edge cases (boundary conditions, error paths, empty states).

5. **Subagent — Write Plan Document.** Create `docs/superpowers/plans/PLAN-{workflow_run_id}.md` with:
   - **Header:** Feature name, goal, architecture (2-3 sentences), tech stack, global constraints from spec
   - **File structure tree**
   - **All tasks** with full code, interfaces, and steps per Task Structure above
   - **Dependency graph** showing task relationships
   - **Test strategy** section

6. **Main Agent — Self-Review.** After writing, scan the plan with fresh eyes:
   - **Spec coverage:** Does every spec requirement have a task? List gaps.
   - **Placeholder scan:** Search for TBD, TODO, "implement later", "similar to Task N" — fix all.
   - **Type consistency:** Do function names, signatures, and property names match across tasks?
   - Fix issues inline via subagent. If a spec requirement lacks a task, add it.

7. **Review Subagent — Plan-Spec Consistency Check.** Dispatch a review subagent with REQ, DESIGN, and PLAN. Checks:
   - Every acceptance criterion has a plan task
   - Every DESIGN component has file paths in plan
   - Every interface/data structure/algorithm appears in a task
   - No plan task introduces out-of-scope work
   - Test strategy covers criteria
   - File paths match DESIGN conventions
   - Output: `PASS: All checks passed` or `FAIL: [N] - [description]`. Loop until PASS.

8. **Main Agent — Set State Variable.** Run `devflow set review_plan_spec_consistency_passed true`.

9. **Proceed.** Run `devflow done`.
