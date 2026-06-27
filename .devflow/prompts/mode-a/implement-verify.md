## MODE-A: implement-verify — Implement and Verify

**Autonomy:** Autonomous (no human gate)

**Role:**
- **Main Agent**: Orchestrate multi-round inner loop, analyze dependency graph, dispatch subagents, review outputs, manage convergence, generate evidence.
- **Implementation Subagent** (one per task): TDD (RED-GREEN-REFACTOR)
- **Review Subagent**: Code review per task
- **Fix Subagent**: Apply fixes after failed review
- **Test Subagent**: Run tests, report results
- **Verification Subagent**: Run acceptance criteria verification, collect evidence

> **MANDATORY:** Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

---

### Inputs

- `docs/superpowers/plans/PLAN-{workflow_run_id}.md` — tasks and dependency graph
- `docs/superpowers/specs/DESIGN-{workflow_run_id}.md` — design spec
- `docs/requirements/REQ-{workflow_run_id}.md` — acceptance criteria

### Outputs

- All source/test files created/modified per the plan
- `docs/evidence/EVIDENCE-{workflow_run_id}.md` — evidence with raw command output

### Gates

```
command_success:{test_command}
file_exists:docs/evidence/EVIDENCE-{workflow_run_id}.md
```

---

### Inner Loop Algorithm

```
Round 1: Topology-sorted parallel implementation
  - Read PLAN, analyze task dependency graph
  - Identify batch: tasks with zero unsatisfied deps
  - Dispatch parallel subagents (one per task, TDD)
  - Each completes -> dispatch review subagent
  - Review fails -> dispatch fix subagent -> re-review -> loop until pass
  - Batch complete -> next batch until all tasks done

Round 2: Unified testing
  - Run {test_command}
  - All pass -> goto Verification
  - Failures exist -> collect, topology-analyze, decompose into fix tasks -> goto Round 1
  - Max 5 rounds; if monotonic convergence lost -> request human

Verification:
  - For each acceptance criterion: IDENTIFY -> RUN -> READ -> VERIFY -> CLAIM
  - Generate docs/evidence/EVIDENCE-{run_id}.md with raw command output
  - devflow set review_implement_verify_passed true
```

---

### Detailed Procedure

#### Round 1: Topology-Sorted Parallel Implementation

1. **Read Plan and Analyze Dependency Graph.** Read PLAN, extract tasks and deps. Build dependency graph. Identify pure-test vs implementation vs infrastructure tasks.

2. **Identify Batches.** Batch N = tasks whose all deps are satisfied. Start with batch 1 (zero deps).

3. **Dispatch Parallel Implementation Subagents.** One subagent per task, dispatched simultaneously. Each follows RED-GREEN-REFACTOR:
   - RED: Write a failing test first
   - GREEN: Write minimal production code to pass
   - REFACTOR: Improve code quality while tests stay green
   - **IRON LAW:** No production code without a failing test first.
   - Return: list of files created/modified + summary.

4. **Review Each Completed Task.** As each subagent completes, dispatch a review subagent. Checks: spec compliance, correctness, code quality. Output: `PASS` or `FAIL: [description]`.

5. **Fix Loop on Review Failure.** On FAIL: dispatch fix subagent with review feedback, then re-review. Loop until all reviews pass.

6. **Advance to Next Batch.** Recalculate next batch (tasks whose deps are now satisfied). If none remain, proceed to Round 2.

#### Round 2: Unified Testing

1. **Run Test Command.** Dispatch test subagent to execute `{test_command}` and capture full output.

2. **All Pass -> Verification.** If all pass, proceed to Verification.

3. **Collect and Analyze Failures.** Main agent collects failure output, analyzes root causes, maps failures to tasks.

4. **Decompose into Fix Tasks.** Decompose failures into independent fix tasks (same 2-5 min structure). Include deps and test output as context. Go to Round 1 with these fix tasks.

5. **Convergence Check.** Max 5 rounds. Problem count must decrease each round. If it increases or stays same, pause and request human intervention.

#### Verification

For each acceptance criterion in REQ:

- **IDENTIFY.** Understand what the criterion requires.
- **RUN.** Dispatch verification subagent to execute the verifying command and capture ALL output (stdout + stderr). Must use raw output — no summarizing or filtering.
- **READ.** Read raw output.
- **VERIFY.** Compare output against criterion. **Forbidden:** "should work", "probably passes" — require explicit citation of proof.
- **CLAIM.** Document result:
  ```
  ### AC-[N]: [criterion text]
  **Command:** `[command]`
  **Output:** ```
  [raw output]
  ```
  **Verdict:** PASS/FAIL
  ```
- **Generate Evidence Document.** Dispatch subagent to create `docs/evidence/EVIDENCE-{workflow_run_id}.md` with: frontmatter (id, feature, date), evidence summary (total/passed/failed), criterion verification details, final test suite output. Must contain **raw, unedited** command output only — no paraphrasing.
- **Set State Variable.** Run `devflow set review_implement_verify_passed true`.

---

#### Proceed

Once gates are satisfied, run `devflow done`.

---

### Constraints

- One subagent per task for maximum parallelism
- Max 5 full rounds (Round 1 -> Round 2 cycles)
- Problem count must decrease each round; otherwise pause for human
- Evidence document must contain **raw, unedited command output** — no "should work" claims
- **IRON LAW:** No production code without a failing test first
