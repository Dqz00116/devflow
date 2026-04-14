---
name: devflow
description: DevFlow v2.0 - Universal AI Agent Development Workflow CLI. Use when starting AI-assisted development with progressive disclosure workflow.
---

# DevFlow v2.0

DevFlow is a universal AI-assisted development workflow system using TOML-based progressive disclosure.

## What You Get

- **Progressive Disclosure** - One step at a time via CLI
- **TOML Workflow Definition** - Configure in `.devflow/workflows/*.toml`
- **Gate System** - Objective verification before advancement
- **Fail Routes** - Automatic routing on gate failure with escalation thresholds
- **Cross-Workflow References** - Seamless transitions between workflows
- **Workflow Inheritance** - Extend and customize existing workflows
- **Config Variables** - Reference `{test_command}`, `{lint_command}` etc. from config
- **CLI Tool** - Manage workflow state and progression

## Quick Start

### 1. Install DevFlow

```bash
git clone <repository-url>
cd devflow
pip install -e .
```

### 2. Initialize Project (Skip if `.devflow/` already exists)

> **Agent rule: If `.devflow/` already exists in the current project, do NOT run `init`. Use the existing workflows directly.**
>
> **`devflow init` uses the DevFlow repository's own `.devflow/` as the template for workflows and prompts.**

```bash
# Only run this if .devflow/ is NOT present
devflow init --language python --name "My Project"
```

### 3. Start Development

```bash
# List available workflows
devflow list-workflows

# Select a workflow
devflow select-workflow MODE-A

# Follow the displayed instruction
devflow current

# When done, mark complete and advance
devflow done

# Repeat until workflow complete
```

## How DevFlow Works

### Progressive Disclosure

Instead of reading a full workflow document, DevFlow reveals **one step at a time**:

```
┌─────────────────────────────────────────┐
│ 1. Agent: devflow current               │
│    CLI: Show current step instruction   │
│                                         │
│ 2. Agent: Execute the instruction       │
│                                         │
│ 3. Agent: devflow done                  │
│    CLI: Check gates → Advance or route  │
└─────────────────────────────────────────┘
```

**Core rule: Only advance workflow through `devflow done`. Do NOT skip steps.**

### Gate System

Each step has gate conditions that must be satisfied before advancing:

- `file_exists:docs/REQ-{workflow_run_id}.md` - Document created
- `file_contains:docs/REQ-{workflow_run_id}.md:status: approved` - Content verified
- `user_approved:DESIGN-001` - User confirmation (via `devflow approve DESIGN-001`)
- `command_success:{test_command}` - Tests pass (config-resolved)

### Fail Routes

When gates fail, steps can define **fail routes** — automatic routing to a different step based on failure count. This implements branching without requiring agent decisions.

```toml
[[steps]]
id = "debug-fix"
gates = ["command_success:{test_command}"]
next = "debug-verify"

[[steps.fail_route]]
min_fails = 1
max_fails = 2
target = "debug-root-cause"    # Fails 1-2 times → re-investigate

[[steps.fail_route]]
min_fails = 3
target = "debug-question"      # Fails 3+ times → escalate to human
```

**Rules:**
- `min_fails`: Required, integer >= 1
- `max_fails`: Optional, integer >= min_fails (defaults to infinity)
- `target`: Required, step ID or cross-workflow reference (`WORKFLOW:STEP`)
- Routes match in declaration order; first match wins
- No matching route = stay and retry (existing behavior)
- Fail count **persists** across visits (only resets when gates pass)
- This enables escalation: fail 1-2 → retry, fail 3+ → escalate

### Cross-Workflow References

Steps can reference steps in other workflows using `WORKFLOW-ID:STEP-ID` format:

```toml
[[steps]]
id = "debug-finish"
next = "MODE-A:write-plan"    # After debug, enter MODE-A at write-plan
```

On cross-workflow transition:
- Target workflow is loaded automatically
- `current_workflow` switches to the target
- `workflow_run_id` is preserved for file naming continuity

### Workflow Configuration

Workflows are defined in TOML format:

```toml
# .devflow/workflows/my-workflow.toml
[workflow]
id = "MY-WORKFLOW"
name = "My Custom Workflow"
description = "Description of this workflow"
extends = ["MODE-A"]  # Optional: inherit from existing

[[steps]]
id = "req-create"
name = "Create Requirement"
prompt = """
## Getting Started

Your instruction here...
"""
gates = ["file_exists:docs/requirements/REQ-{workflow_run_id}.md"]
next = "next-step"

[[steps]]
id = "complex-step"
name = "Complex Step"
prompt_file = "prompts/complex.md"  # Reference external file
gates = ["command_success:{test_command}"]
next = ""  # Empty = workflow complete

[[steps.fail_route]]
min_fails = 1
target = "fallback-step"      # On failure, route to fallback
```

### Config Variables

Reference project commands from `.devflow/config.toml` in gates and prompts:

- `{test_command}` - Test command (e.g., `pytest`, `go test ./...`)
- `{test_unit_command}` - Unit test command
- `{test_integration_command}` - Integration test command
- `{lint_command}` - Lint command
- `{build_command}` - Build command
- `{workflow_run_id}` - Current workflow run ID (auto-generated)

## CLI Commands

### Workflow Commands (Primary - Use These)

```bash
devflow list-workflows              # List all available workflows
devflow select-workflow <id>        # Select and start a workflow
devflow current                     # Get current step instruction
devflow done                        # Check gates and advance (or route on failure)
devflow back                        # Go back to previous step
devflow workflow-status             # Show workflow status
devflow approve <item>              # Mark item as user-approved
devflow set <key> <value>           # Set a state variable
```

### Legacy Commands (Not for AI agents)

```bash
devflow init                        # Initialize project
devflow req new REQ-001             # Create requirement
devflow feat new FEAT-001           # Create feature
devflow task new                    # Create task
devflow status                      # Project status
devflow validate                    # Check compliance
```

## Example Workflows

DevFlow includes two example workflows that you can use directly or extend:

### MODE-A: Feature Development

For building new features, enhancements, or new modules.

**Steps:**
1. **req-create** → Create requirement document
2. **req-approve** → Get user approval + create FEAT document
3. **brainstorm** → Explore design options
4. **write-plan** → Decompose into tasks
5. **implement-tdd** → TDD implementation
6. **code-review** → Review changes (requires `user_approved`)
7. **test-run** → Run all tests
8. **verify** → Collect evidence
9. **finish** → Deliver and cleanup (requires REQ status: done)

**Use when:** Building new features, enhancing existing functionality

### MODE-B: Debug

For systematic debugging of bugs, errors, and unexpected behavior.

**Steps:**
1. **debug-root-cause** → Investigate root cause
2. **debug-pattern** → Pattern analysis
3. **debug-hypothesis** → Form and test hypothesis (on fail → back to root-cause)
4. **debug-fix** → Implement fix (fails 1-2x → root-cause; fails 3x → escalate)
5. **debug-question** → Question architecture (requires `user_approved`, then → root-cause)
6. **debug-verify** → Verify fix
7. **debug-finish** → Complete debug → **auto-transitions to MODE-A:write-plan**

**Use when:** Debugging bugs, fixing errors, test failures

**Fail route escalation:**
```
debug-fix fails 1-2 times → debug-root-cause (re-investigate)
debug-fix fails 3+ times  → debug-question (escalate to human)
debug-question approved   → debug-root-cause (try again with guidance)
debug-finish complete     → MODE-A:write-plan (full review cycle)
```

### Creating Custom Workflows

Create your own workflow by adding a TOML file:

```toml
# .devflow/workflows/CUSTOM.toml
[workflow]
id = "CUSTOM"
name = "Custom Workflow"
description = "My custom development process"

[[steps]]
id = "step1"
name = "Step One"
prompt = "Instructions for step 1"
gates = []
next = "step2"

[[steps]]
id = "step2"
name = "Step Two"
prompt_file = "prompts/step2.md"
gates = ["command_success:{test_command}"]
next = ""

[[steps.fail_route]]
min_fails = 2
target = "OTHER-WORKFLOW:fallback-step"  # Cross-workflow fail route
```

### Extending Existing Workflows

```toml
# .devflow/workflows/MY-MODE-A.toml
[workflow]
id = "MY-MODE-A"
name = "My Feature Workflow"
extends = ["MODE-A"]  # Inherit all MODE-A steps

# Override a step
[[steps]]
id = "req-create"
name = "Custom Requirement"
prompt = "My custom requirement instructions"
next = "req-approve"

# Add new step
[[steps]]
id = "custom-step"
name = "Custom Step"
prompt = "Additional step"
gates = []
next = "brainstorm"
```

## 5 Iron Laws

| # | Law | Status | If Violated |
|---|-----|--------|-------------|
| 1 | Read `using-superpowers` first | Rigid | Stop, read skill |
| 2 | TDD: Test before code | Rigid | Delete code, restart |
| 3 | Verify before claim | Rigid | Run test → Read → Claim |
| 4 | Root cause before fix | Strong | Ask human after 3 fails |
| 5 | Debug → Repeat full cycle | Strong | Complete plan→test before commit |

## Document Structure

```
project/
├── .devflow/
│   ├── workflows/           # Workflow definitions (TOML)
│   │   ├── MODE-A.toml      # Feature development
│   │   ├── MODE-B.toml      # Debug workflow
│   │   └── CUSTOM.toml      # Your custom workflows
│   ├── prompts/             # Reusable prompt files
│   ├── config.toml          # Project config
│   └── state.toml           # Current state (auto-managed, gitignored)
├── docs/
│   ├── requirements/        # REQ files
│   ├── features/            # FEAT files (technical implementation docs)
│   ├── superpowers/specs/   # Design docs
│   ├── superpowers/plans/   # Implementation plans
│   ├── evidence/            # Verification evidence
│   ├── debug/               # Debug analysis
│   └── completion/          # Workflow completion summaries
└── AGENTS.md                # Project context
```

## Skills Reference

These are external skills you should read when instructed:

| Skill | Type | When |
|-------|------|------|
| using-superpowers | Rigid | **ALWAYS FIRST** |
| brainstorming | Flexible | New features |
| systematic-debugging | Rigid | Bugs/issues |
| writing-plans | Flexible | After brainstorm |
| test-driven-development | Rigid | Implementation |
| subagent-driven-development | Flexible | Plan execution |
| requesting-code-review | Flexible | After implementation |
| verification-before-completion | Rigid | Before claiming done |
| finishing-a-development-branch | Flexible | Ready to merge |

## Configuration

Project configuration in `.devflow/config.toml`:

```toml
[project]
name = "my-project"
language = "python"
stack = "Python 3.11 + FastAPI"

[commands]
test = "pytest"
test_unit = "pytest tests/unit -v"
test_integration = "pytest tests/integration -v"
lint = "ruff check ."
build = "python -m build"
```

---

*DevFlow v2.0 - Progressive Disclosure Workflow*
