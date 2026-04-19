# DevFlow v2.0

Universal AI Agent Development Workflow CLI with TOML-based progressive disclosure.

## Overview

DevFlow v2.0 is a development workflow tool designed for AI-assisted software development. It uses **TOML configuration** to define workflows with **progressive disclosure** - AI agents see one step at a time, advancing only when gates are satisfied.

### Key Features

- **TOML Workflow Definition** - Configure workflows in `.devflow/workflows/*.toml`
- **Progressive Disclosure** - One step at a time via CLI
- **Gate System** - Objective verification before advancement
- **Fail Routes** - Automatic routing on gate failure with escalation thresholds
- **Cross-Workflow References** - Seamless transitions between workflows (e.g., MODE-B → MODE-A)
- **Workflow Inheritance** - Extend existing workflows
- **Prompt Reuse** - File references for complex prompts
- **Config Variables** - Reference `{test_command}`, `{lint_command}` etc. from config
- **Universal Design** - Works with any programming language
- **Ralph Loop** - Autonomous execution: `devflow run` drives the workflow automatically
- **VCS Abstraction** - Git/SVN/no-VCS checkpointing via unified driver interface

## Installation

```bash
pip install agent-devflow
```

Or from source:

```bash
git clone https://github.com/Dqz00116/devflow
cd devflow
pip install -e .
```

## Quick Start

> **If `.devflow/` already exists in the project, skip `init` and use it directly.**
>
> **`devflow init` copies workflows and prompts from the DevFlow repository's own `.devflow/` as the template.**

```bash
# Only run init if .devflow/ does NOT already exist
devflow init --language python --name "My Project"

# List available workflows
devflow list-workflows

# Select a workflow (e.g., MODE-A for feature development)
devflow select-workflow MODE-A

# Follow the displayed instruction
devflow current

# When done, mark step complete and advance
devflow done

# Repeat until workflow complete
```

## Workflow Commands

```bash
devflow list-workflows              # List all available workflows
devflow select-workflow MODE-A      # Select and start a workflow
devflow current                     # Show current step instruction
devflow done                        # Check gates and advance (or route on failure)
devflow back                        # Go back to previous step
devflow workflow-status             # Show workflow status
devflow approve ITEM                # Mark item as user-approved
devflow set KEY VALUE               # Set a state variable

# Ralph Loop — Autonomous Execution
devflow run [--tool local] [--max-iterations 10]   # Start autonomous loop
devflow loop-status                                  # Show loop status and remaining tasks
devflow sync-backlog                                 # Generate backlog from current workflow
devflow loop-reset                                   # Reset loop progress (preserves history)
```

## Workflow Structure

Workflows are defined in TOML format:

```toml
# .devflow/workflows/my-workflow.toml
[workflow]
id = "MY-WORKFLOW"
name = "Feature Development"
extends = []  # Inheritance support

[[steps]]
id = "req-create"
name = "Create Requirement"
prompt = """
Your instruction here...
"""
gates = ["file_exists:docs/requirements/REQ-{workflow_run_id}.md"]
next = "next-step"

[[steps]]
id = "complex-step"
name = "Complex Step"
prompt_file = "prompts/complex.md"  # File reference
gates = ["command_success:{test_command}"]
next = ""

[[steps.fail_route]]
min_fails = 1
max_fails = 2
target = "fallback-step"    # Fails 1-2 times → go to fallback

[[steps.fail_route]]
min_fails = 3
target = "OTHER-WORKFLOW:escalation"  # Fails 3+ times → cross-workflow
```

### Config Variables

Reference project commands from `.devflow/config.toml` in gates and prompts:

- `{test_command}` - Test command (e.g., `pytest`, `go test ./...`)
- `{test_unit_command}` - Unit test command
- `{test_integration_command}` - Integration test command
- `{lint_command}` - Lint command
- `{build_command}` - Build command
- `{workflow_run_id}` - Current workflow run ID (auto-generated)

## Gate Conditions

Gates verify step completion before advancing:

- `file_exists:path/to/file` - File must exist
- `file_exists_pattern:docs/REQ-*.md` - Any file matching glob
- `file_contains:path/file.md:content` - File must contain text
- `file_contains_pattern:docs/REQ-*.md:content` - Any matching file contains text
- `user_approved:ITEM-001` - User approval required (via `devflow approve`)
- `command_success:pytest` - Command must exit 0
- `state_set:var_name` - State variable must be set

## Fail Routes

When gates fail, steps can define automatic routing based on failure count. This implements branching without requiring agent decisions.

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

**Behavior:**
- `min_fails`: Required, integer >= 1
- `max_fails`: Optional, defaults to infinity
- `target`: Step ID or cross-workflow reference (`WORKFLOW-ID:STEP-ID`)
- Routes match in declaration order; first match wins
- No matching route = stay and retry
- Fail count **persists** across visits (only resets when gates pass), enabling escalation

## Cross-Workflow References

Steps can reference steps in other workflows:

```toml
[[steps]]
id = "debug-finish"
next = "MODE-A:write-plan"    # After debug, enter MODE-A at write-plan
```

On transition:
- Target workflow is loaded automatically
- `current_workflow` switches to the target
- `workflow_run_id` is preserved for file naming continuity

## Included Workflows

### MODE-A: Feature Development

1. **req-create** - Create requirement document
2. **req-approve** - Get user approval + create FEAT document
3. **brainstorm** - Explore design options
4. **write-plan** - Decompose into tasks
5. **implement-sdd** - TDD implementation
6. **code-review** - Review changes (requires `user_approved`)
7. **test-run** - Run all tests
8. **verify** - Collect evidence
9. **finish** - Deliver and cleanup (requires REQ status: done)

### MODE-B: Debug

1. **debug-root-cause** - Investigate root cause
2. **debug-pattern** - Pattern analysis
3. **debug-hypothesis** - Form and test hypothesis (fail → back to root-cause)
4. **debug-fix** - Implement fix (fails 1-2x → root-cause; fails 3x → escalate)
5. **debug-question** - Question architecture (requires `user_approved`, then → root-cause)
6. **debug-verify** - Verify fix
7. **debug-finish** - Complete debug → auto-transitions to MODE-A:write-plan

**Fail route escalation:**
```
debug-fix fails 1-2 times → debug-root-cause (re-investigate)
debug-fix fails 3+ times  → debug-question (escalate to human)
debug-question approved   → debug-root-cause (try again with guidance)
debug-finish complete     → MODE-A:write-plan (full review cycle)
```

## Project Structure

```
.devflow/
├── workflows/
│   ├── MODE-A.toml          # Feature development
│   └── MODE-B.toml          # Debug workflow
├── prompts/
│   ├── brainstorm.md        # Reusable prompts
│   ├── implement-sdd.md
│   └── ...
├── config.toml              # Project config
└── state.toml               # Current workflow & step (gitignored)

docs/
├── requirements/            # REQ files
├── features/                # FEAT files (technical implementation docs)
├── superpowers/specs/       # Design docs
├── superpowers/plans/       # Implementation plans
├── evidence/                # Verification evidence
├── debug/                   # Debug analysis
└── completion/              # Workflow completion summaries
```

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

[paths]
src = "src"
tests = "tests"
docs = "docs"
```

## Legacy CLI Commands

DevFlow includes legacy commands for direct requirement/task management. These bypass the workflow engine; prefer workflow commands (`current`/`done`) for AI agents.

```bash
devflow init --language python --name "My Project"
devflow req new REQ-001 --title "Feature"
devflow feat new FEAT-001 -r REQ-001 -t "Implementation"
devflow task new -r REQ-001 -t "Task"
devflow status
```

## License

MIT License
