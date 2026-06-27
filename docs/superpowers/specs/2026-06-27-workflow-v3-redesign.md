# DevFlow Workflow v3.0 Redesign

**Date:** 2026-06-27
**Status:** approved
**Branch:** main

## Overview

Refactor MODE-A and MODE-B workflows to adopt an architect/subagent execution model: the main agent handles design, planning, and review exclusively; all operational actions (file I/O, code editing, search, command execution) are delegated to parallel Haiku subagents. Merge MODE-A's four execution-phase steps into a single topology-driven implement-verify loop, extract all inline prompts to separate files organized by mode directory, and enable autonomous progression except where human judgment is explicitly required.

---

## 1. Step Structure

### 1.1 MODE-A (6 steps, was 9)

```
req-create → req-approve → brainstorm → write-plan → implement-verify → finish
  auto        human          human        auto          auto            auto
```

| Step ID | Name | Autonomy | Gates |
|---------|------|----------|-------|
| `req-create` | Create Requirement | auto | `file_exists:docs/requirements/REQ-{run_id}.md` |
| `req-approve` | Approve Requirement | **human** | `file_exists:docs/requirements/REQ-{run_id}.md`, `file_contains:docs/requirements/REQ-{run_id}.md:status: approved`, `file_exists:docs/features/FEAT-{run_id}.md` |
| `brainstorm` | Brainstorm Design | **human** | `file_exists:docs/superpowers/specs/DESIGN-{run_id}.md` |
| `write-plan` | Write Implementation Plan | auto | `file_exists:docs/superpowers/plans/PLAN-{run_id}.md`, `state_set:review_plan_spec_consistency_passed` |
| `implement-verify` | Implement + Verify | auto | `command_success:{test_command}`, `file_exists:docs/evidence/EVIDENCE-{run_id}.md` |
| `finish` | Complete & Deliver | auto | `file_exists:docs/completion/COMPLETION-{run_id}.md`, `file_contains:docs/requirements/REQ-{run_id}.md:status: done` |

**Merged steps** (removed): `implement-sdd`, `code-review`, `test-run`, `verify` → now combined into `implement-verify`.

**New gate**: `write-plan` gains `state_set:review_plan_spec_consistency_passed` — set by the main agent after dispatching a plan-vs-spec consistency review subagent that passes.

### 1.2 MODE-B (7 steps, structure unchanged)

```
debug-root-cause → debug-pattern → debug-hypothesis → debug-fix ──→ debug-verify → debug-finish
      ↑                  ↑              ↑               │  fail 1-2   │                │
      └──────────────────┴──────────────┴───────────────┘             │                │
                                                          fail 3+     │                │
                                                              ↓       │                │
                                                       debug-question │                │
                                                              ↓       │                │
                                                       debug-root-cause               │
                                                                                       │
                                                                          └──→ MODE-A:write-plan
```

| Step ID | Name | Autonomy | Gates |
|---------|------|----------|-------|
| `debug-root-cause` | Root Cause Investigation | auto | `file_exists:docs/debug/ROOT-CAUSE-{run_id}.md` |
| `debug-pattern` | Pattern Analysis | auto | `file_exists:docs/debug/PATTERN-{run_id}.md` |
| `debug-hypothesis` | Form & Test Hypothesis | auto | `file_exists:docs/debug/HYPOTHESIS-{run_id}.md` |
| `debug-fix` | Implement Fix | auto | `command_success:{test_command}` |
| `debug-question` | Question Architecture | **human** | `user_approved:ARCHITECTURE-REVIEW-{run_id}` |
| `debug-verify` | Verify Fix | auto | `file_exists:docs/debug/VERIFICATION-{run_id}.md`, `command_success:{test_command}` |
| `debug-finish` | Complete Debug | auto | `file_exists:docs/debug/COMPLETION-{run_id}.md` |

**Fail routes preserved**:
- `debug-hypothesis`: any failure → back to `debug-root-cause`
- `debug-fix`: 1-2 failures → back to `debug-root-cause`; 3+ failures → `debug-question`
- `debug-question`: after human input → back to `debug-root-cause`

**Cross-workflow**: `debug-finish` → `MODE-A:write-plan`

---

## 2. Main Agent / Subagent Execution Model

### 2.1 Principle

| Role | Model | Responsibilities |
|------|-------|-----------------|
| Main Agent | (current session model) | Design, planning, task decomposition, review of subagent outputs, architectural decisions |
| Subagent | Haiku | File I/O, code editing, test execution, search, document drafting, TDD implementation |

### 2.2 Execution Pattern

```
Main Agent reads prompt → designs approach → decomposes into independent tasks
    ↓
Dispatches parallel Haiku subagents for each independent task
    ↓
Each subagent returns result → Main Agent reviews
    ↓
Review fails? → Dispatch fix subagent → re-review → loop until pass
    ↓
All pass? → Main Agent signals completion → devflow done
```

### 2.3 Autonomous vs Human Confirmation

**Autonomous (no human gate):**
- All steps except `req-approve`, `brainstorm` (MODE-A) and `debug-question` (MODE-B)
- `implement-verify` inner loop: max 5 rounds; if problem count does not decrease monotonically, pause and request human intervention
- `write-plan` plan-spec consistency review: subagent-driven, auto-loop until pass

**Human confirmation required:**
- `req-approve` — explicit user approval of requirements
- `brainstorm` — user chooses design approach
- `debug-question` — reached after 3+ consecutive fix failures; user decides refactor/fix/abandon

---

## 3. `implement-verify` Inner Loop

### 3.1 Algorithm

```
Round 1: Topology-sorted parallel implementation
  ├─ 1a. Read PLAN-{run_id}.md, analyze task dependency graph
  ├─ 1b. Identify first batch: tasks with zero unsatisfied dependencies
  ├─ 1c. Dispatch parallel Haiku subagents (one per task, each follows TDD)
  ├─ 1d. Each subagent completes → dispatch review subagent for that task
  ├─ 1e. Review fails → dispatch fix subagent → re-review → loop until pass
  ├─ 1f. Batch complete → next batch (1b) until all tasks done

Round 2: Unified testing
  ├─ 2a. Run {test_command}
  ├─ 2b. All pass → goto Verification
  ├─ 2c. Failures exist → collect failure list, analyze topology
  ├─ 2d. Decompose failures into independent fix tasks → goto Round 1
  ├─ 2e. Max 5 rounds; if monotonic convergence lost → request human intervention

Verification:
  ├─ V1. For each acceptance criterion: IDENTIFY→RUN→READ→VERIFY→CLAIM
  ├─ V2. Generate docs/evidence/EVIDENCE-{run_id}.md with raw command output
  ├─ V3. devflow set review_implement_verify_passed true
  └─ V4. devflow done
```

### 3.2 Constraints

- Each subagent invocation uses Haiku model
- Max 5 full rounds (Round 1→2 cycles)
- Problem count must decrease each round; otherwise pause for human
- Evidence document must contain raw, unedited command output — no "should work" claims

---

## 4. Prompt File Organization

### 4.1 Directory Structure

```
.devflow/prompts/
├── mode-a/
│   ├── req-create.md
│   ├── req-approve.md
│   ├── brainstorm.md
│   ├── write-plan.md
│   ├── implement-verify.md
│   └── finish.md
└── mode-b/
    ├── debug-root-cause.md
    ├── debug-pattern.md
    ├── debug-hypothesis.md
    ├── debug-fix.md
    ├── debug-question.md
    ├── debug-verify.md
    └── debug-finish.md
```

### 4.2 Naming Convention

- `{mode-dir}/{step-id}.md` — e.g. `mode-a/implement-verify.md`
- Referenced in TOML as `prompt_file = "mode-a/implement-verify.md"`
- Existing `load_prompt()` resolves relative to `.devflow/prompts/` — no engine change needed

### 4.3 Migration

**Deleted files** (flat prompts/ directory):
`req-create.md`, `brainstorm.md`, `write-plan.md`, `implement-sdd.md`, `code-review.md`, `verify.md`, `finish.md`, `debug-root-cause.md`, `debug-pattern.md`, `debug-hypothesis.md`, `debug-fix.md`

**Inline prompts extracted to files**:
- MODE-A: `req-approve` → `mode-a/req-approve.md`; `test-run` → merged into `mode-a/implement-verify.md`
- MODE-B: `debug-question` → `mode-b/debug-question.md`; `debug-verify` → `mode-b/debug-verify.md`; `debug-finish` → `mode-b/debug-finish.md`

### 4.4 Prompt Content Guidelines

- All prompts written in **English**
- Each prompt defines: role (main agent vs subagent), input files, output files, step-by-step procedure, gate conditions
- Autonomous steps include subagent dispatch patterns and review loops
- Human-gated steps explicitly state "Do NOT proceed without explicit user approval"

---

## 5. Engine Changes

### 5.1 No New Gate Types

The `implement-verify` loop and `write-plan` plan-spec review use the existing `state_set` gate type:

```toml
# write-plan gate
gates = [
    "file_exists:docs/superpowers/plans/PLAN-{workflow_run_id}.md",
    "state_set:review_plan_spec_consistency_passed",
]
```

No changes to `gate_checker.py`, `workflow_parser.py`, or `workflow_engine.py`.

### 5.2 No TOML Schema Changes

The existing `[[steps]]` schema with `prompt_file`, `gates`, `next`, and `[[steps.fail_route]]` supports all requirements. No new fields needed.

---

## 6. Test Fixture Impact

E2E test fixtures must be updated:
- `tests/e2e/taskflow_e2e/.devflow/workflows/MODE-A.toml`
- `tests/e2e/taskflow_e2e/.devflow/workflows/MODE-B.toml`
- `tests/e2e/taskflow_e2e_v2/.devflow/workflows/MODE-A.toml`
- `tests/e2e/taskflow_e2e_v2/.devflow/workflows/MODE-B.toml`
- `tests/e2e/taskflow_e2e/.devflow/workflows/E2E-MODE-A.toml`
- `tests/e2e/taskflow_e2e_v2/.devflow/workflows/E2E-MODE-A.toml`

Plus any test assertions that reference the old step IDs (`implement-sdd`, `code-review`, `test-run`, `verify`) must be updated to `implement-verify`.

---

## 7. Implementation Sequence

1. Create `mode-a/` and `mode-b/` directories under `.devflow/prompts/`
2. Write all 13 new prompt files (6 mode-a + 7 mode-b) — parallel subagent dispatch
3. Rewrite MODE-A.toml: 6 steps, new IDs, mode-a/ paths, new gates
4. Rewrite MODE-B.toml: 7 steps, mode-b/ paths, all `prompt_file` (no inline)
5. Delete flat prompt files (11 files)
6. Update E2E test fixture TOML files
7. Update test assertions referencing old step IDs
8. Run full test suite: `pytest`
9. Validate: `devflow validate`
