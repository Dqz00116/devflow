# Squeez-Inspired Evidence Pipeline for DevFlow

Inspired by [Squeez: Task-Conditioned Tool-Output Pruning for Coding Agents](https://arxiv.org/abs/2604.04979) (Kovács, KR Labs, 2026).

## Core Insight

Squeez proves that **tool-output pruning should be a standard component of agent systems**.
A fine-tuned 2B model can retain 86% of critical evidence while cutting 92% of useless
tokens — far outperforming larger zero-shot models and all heuristic baselines.

Three principles from the paper apply directly to workflow frameworks:

1. **Verbatim evidence, not summaries.** Do not rewrite or abstract — preserve original
   text so decisions remain traceable and free from model hallucination.
2. **Tool-type awareness.** Different tool outputs (test runs, lint, grep, file reads)
   have radically different token distributions and require different pruning strategies.
3. **Query-conditioned pruning.** What counts as "relevant" depends on the current
   task. Prune against the current step's needs, not globally.

## Problem: DevFlow's Information Flow Gap

DevFlow's current framework data flow:

```
Step N → gate check (pass/fail boolean) → advance → Step N+1 gets new prompt
```

Gate outputs are discarded. Step prompts can only reference config variables
(`{test_command}`, `{lint_command}`) — there is no way to inject evidence from
prior steps into the current step's context.

The `ProgressLogger` writes one-line human summaries to `progress.md`, losing all
verbatim evidence. When a step fails and routes elsewhere, the target step receives
no structured context about *what* failed.

## Proposals

### 1. Gate Output Capture (Foundation)

**Current:** `check_command_success()` runs a command and returns only `(bool, message)`.
Stdout/stderr are discarded.

**Proposal:** Upgrade `GateResult` to carry structured evidence:

```python
@dataclass
class GateResult:
    passed: bool
    message: str
    evidence: GateEvidence | None

@dataclass
class GateEvidence:
    gate_type: str           # "command_success", "file_contains", ...
    label: str               # "test_output", "lint_output", ...
    raw_output: str          # captured output
    verbatim_excerpts: list[str]  # key excerpts (aligned with Squeez's "verbatim evidence block")
    token_count: int
```

Gate definitions in TOML gain optional `label` and `capture` fields so outputs
become addressable evidence.

**Files:** `src/devflow/gate_checker.py`

### 2. Structured Evidence Store

**Current:** `ProgressLogger` appends free-text summaries to `progress.md`. Not
queryable, not typed, no verbatim preservation.

**Proposal:** `EvidenceStore` that stores structured, step-scoped evidence under
`.devflow/evidence/{workflow_run_id}/{step_id}/`. Each entry carries tool type,
label, raw output, verbatim excerpts, and token count. The progress logger
becomes a consumer of the evidence store rather than the primary record.

**Files:** new `src/devflow/evidence_store.py`, refactor `src/devflow/progress.py`

### 3. Evidence Injection Variables

**Current:** `_resolve_step_variables()` only resolves config variables like
`{test_command}` and `{workflow_run_id}`.

**Proposal:** Extend variable syntax to reference upstream evidence:

```markdown
## Stage 5: Testing

Prior test results:
{evidence:implement-sdd:test_output}

Lint results:
{evidence:implement-sdd:lint_output}
```

The framework resolves these at prompt-render time by querying the EvidenceStore.
If evidence exceeds a configured token budget, automatic pruning kicks in:

| Evidence type | Pruning strategy |
|---|---|
| `test_output` | Keep failures + summary line |
| `lint_output` | Keep error/warning lines only |
| `file_read` | Truncate at function/class boundaries |
| `build_output` | Keep first error chain + last lines |

This directly implements Squeez's "task-conditioned pruning": the current step's
prompt is the query, and upstream evidence is pruned against it.

**Files:** `src/devflow/workflow_engine.py`, `src/devflow/gate_checker.py`

### 4. Context Budget Constraints

**Current:** No awareness of context size. Framework does not track or limit how
much information is injected into a step's prompt.

**Proposal:** Add `max_evidence_tokens` and `pruning_strategy` to config constraints:

```toml
[constraints]
zero_warnings = true
max_evidence_tokens = 4000       # per-step evidence injection cap
evidence_pruning = "failure-first"  # prioritize failures over passing output
```

The engine tracks cumulative injected tokens during variable resolution and
triggers progressively more aggressive pruning when approaching the budget.

**Files:** `src/devflow/config.py`, `src/devflow/workflow_engine.py`

### 5. Fail Route Evidence Context

**Current:** Fail routes only change the step pointer. The target step receives
no structured information about what caused the failure.

```toml
# Current: blind routing
[[steps.fail_route]]
min_fails = 1
target = "debug-root-cause"
```

**Proposal:** Fail routes can declare evidence to carry forward:

```toml
# Proposed: evidence-aware routing
[[steps.fail_route]]
min_fails = 1
target = "debug-root-cause"
inject_evidence = ["test_output", "lint_output"]
```

When a fail route triggers, the framework automatically extracts the declared
evidence from the EvidenceStore and injects it into the target step's state,
making it available via `{evidence:...}` variables in the target prompt.

**Files:** `src/devflow/workflow_parser.py`, `src/devflow/workflow_engine.py`

### 6. Step Evidence Dependencies (Declarative)

**Current:** Steps have no way to declare what upstream evidence they need.

**Proposal:** Optional `needs_evidence` field in step TOML definitions:

```toml
[[steps]]
id = "test-run"
name = "Run All Tests"
prompt_file = "prompts/test-run.md"
gates = ["command_success:{test_command}"]
needs_evidence = [
    "implement-sdd:test_output",
    "implement-sdd:lint_output",
]
next = "verify"
```

Benefits:
- **Explicit dependency tracking** — the TOML itself documents information flow
- **Incremental execution** — if an upstream step re-runs, downstream evidence caches
  can be invalidated
- **Auto-injection** — the framework collects declared evidence before rendering
  the step prompt, no manual `{evidence:...}` references needed

**Files:** `src/devflow/workflow_parser.py`

## Priority

| # | Proposal | Effort | Impact | Paper alignment |
|---|---|---|---|---|
| 1 | Gate Output Capture | Small (`gate_checker.py`) | Foundation for all below | 27 tool types, output diversity |
| 2 | Structured Evidence Store | Medium (new module) | Enables queryable, typed evidence | "Verbatim evidence block" |
| 3 | Evidence Injection Variables | Small (`workflow_engine.py`) | Most visible user benefit | "Task-conditioned pruning" |
| 4 | Context Budget Constraints | Small (`config.py`) | Prevents context bloat | 92% compression motivation |
| 5 | Fail Route Evidence Context | Medium (parser + engine) | Smarter failure recovery | Evidence-driven decision making |
| 6 | Step Evidence Dependencies | Small (parser + schema) | Self-documenting workflows | Query-conditioned relevance |

1 + 2 + 3 together form the minimum viable evidence pipeline: capture → store → inject.
