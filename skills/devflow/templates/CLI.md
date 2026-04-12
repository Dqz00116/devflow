# DevFlow CLI Reference

Complete reference for the DevFlow command-line interface.

## Installation

**Using uv** (recommended):

```bash
git clone <repository-url>
cd devflow
uv pip install -e .
```

**Using pip**:

```bash
git clone <repository-url>
cd devflow
pip install -e .
```

## Global Options

```bash
devflow [OPTIONS] COMMAND [ARGS...]

Options:
  --version          Show version and exit
  -c, --config PATH  Path to configuration file
  --help             Show help message
```

## Workflow Commands (v2.0)

### list-workflows - List Available Workflows

List all available workflow files in `.devflow/workflows/`.

```bash
devflow list-workflows
```

Example output:
```
Available Workflows:

  1. MODE-A
     Path: /path/to/.devflow/workflows/MODE-A.toml

  2. MODE-B
     Path: /path/to/.devflow/workflows/MODE-B.toml

Use devflow select-workflow <id> to choose
```

---

### select-workflow - Select Workflow

Select and start a workflow.

```bash
devflow select-workflow <workflow-id>
```

Arguments:
- `workflow-id` - Workflow ID (e.g., MODE-A, MODE-B)

Example:
```bash
devflow select-workflow MODE-A
```

---

### current - Get Current Step

Display the current step instruction. This is the primary command for AI agents.

```bash
devflow current [--workflow <id>]
```

Options:
- `--workflow, -w` - Use specific workflow (optional)

---

### done - Mark Step Complete

Check gate conditions and advance to next step if all pass. On failure, automatically routes via fail routes if defined.

```bash
devflow done
```

If gates pass:
- Advances to next step
- Displays new step instruction

If gates fail and a fail route matches:
- Routes to the target step (may be in a different workflow)
- Displays routing information
- Run `devflow current` for the new step instruction

If gates fail and no fail route matches:
- Shows missing conditions and attempt count
- Agent must complete them and run again

**Fail route escalation example (MODE-B):**
```
debug-fix fails 1-2 times → auto-routed to debug-root-cause
debug-fix fails 3+ times  → auto-routed to debug-question (escalation)
debug-finish completes     → auto-transitions to MODE-A:write-plan
```

---

### workflow-status - Show Workflow Status

Display current workflow status including:
- Current workflow ID
- Current step
- Total steps
- Step list with current position
- Steps with fail routes marked as `[has fail routes]`

```bash
devflow workflow-status
```

---

### approve - Mark User Approval

Mark an item as user-approved (for gates requiring `user_approved:item`).

```bash
devflow approve <item>
```

Arguments:
- `item` - Item to approve (e.g., REQ-001, DESIGN-001)

Example:
```bash
devflow approve REQ-001
```

---

### back - Go Back to Previous Step

Return to the previous step in the workflow.

```bash
devflow back
```

---

### set - Set State Variable

Set a state variable (can be referenced in gates via `{var_name}`).

```bash
devflow set <key> <value>
```

Arguments:
- `key` - Variable name
- `value` - Variable value

Example:
```bash
devflow set project_name "My App"
```

---

## Legacy Commands (Optional)

### init - Initialize Project

Initialize a new DevFlow project in the current directory.

```bash
devflow init [OPTIONS]
```

Options:
- `--language, -l` - Project language (python, javascript, typescript, go, rust, dotnet, other)
- `--name, -n` - Project name
- `--force, -f` - Overwrite existing configuration

Example:
```bash
devflow init --language python --name "My Project"
```

Creates:
- `.devflow/config.toml` - Project configuration
- `.devflow/state.toml` - Task state (created automatically)
- `AGENTS.md` - AI agent context

---

### req - Manage Requirements

#### List Requirements

```bash
devflow req list [OPTIONS]
```

Options:
- `--status, -s` - Filter by status

#### Create Requirement

```bash
devflow req new <id> [OPTIONS]
```

Arguments:
- `id` - Requirement ID (format: REQ-001, REQ-002, etc.)

Options:
- `--title, -t` - Requirement title
- `--priority, -p` - Priority (low, medium, high, critical)

Example:
```bash
devflow req new REQ-001 --title "User Authentication" --priority high
```

#### Show Requirement

```bash
devflow req show <id>
```

#### Update Status

```bash
devflow req status <id> <status>
```

---

### feat - Manage Features

#### List Features

```bash
devflow feat list [OPTIONS]
```

#### Create Feature

```bash
devflow feat new <id> [OPTIONS]
```

Options:
- `--title, -t` - Feature title
- `--requirement, -r` - Related requirement ID (required)
- `--priority, -p` - Priority

Example:
```bash
devflow feat new FEAT-001 --requirement REQ-001 --title "Database Module"
```

#### Show Feature

```bash
devflow feat show <id>
```

#### Update Status

```bash
devflow feat status <id> <status>
```

---

### task - Manage Tasks

#### List Tasks

```bash
devflow task list [OPTIONS]
```

#### Create Task

```bash
devflow task new [OPTIONS]
```

Options:
- `--requirement, -r` - Related requirement ID (required)
- `--title, -t` - Task title (required)

Example:
```bash
devflow task new --requirement REQ-001 --title "Implement login endpoint"
```

#### Complete Task

```bash
devflow task done <task_id>
```

---

### status - Project Overview

Show project status overview.

```bash
devflow status
```

---

### validate - Validate Compliance

Validate project configuration and workflow compliance.

```bash
devflow validate
```

---

## Fail Routes & Cross-Workflow References

### Fail Routes

Steps can define `[[steps.fail_route]]` entries that trigger automatic routing on gate failure:

```toml
[[steps]]
id = "debug-fix"
gates = ["command_success:{test_command}"]
next = "debug-verify"

[[steps.fail_route]]
min_fails = 1
max_fails = 2
target = "debug-root-cause"

[[steps.fail_route]]
min_fails = 3
target = "debug-question"
```

**Fields:**
- `min_fails` (required, >= 1) - Minimum failure count to match
- `max_fails` (optional) - Maximum failure count (defaults to infinity)
- `target` (required) - Target step ID or `WORKFLOW-ID:STEP-ID`

**Behavior:**
- Routes match in declaration order; first match wins
- No matching route = stay and retry
- Fail count **persists** across visits (only resets when gates pass)
- When a route fires, `devflow done` shows routing info and `devflow current` shows the new step

### Cross-Workflow References

Use `WORKFLOW-ID:STEP-ID` syntax in `next` or `fail_route.target`:

```toml
[[steps]]
id = "debug-finish"
next = "MODE-A:write-plan"

[[steps.fail_route]]
min_fails = 3
target = "MODE-A:escalation-step"
```

On transition:
- Target workflow is loaded automatically
- `current_workflow` switches
- `workflow_run_id` is preserved

## Configuration

### Project Config (`.devflow/config.toml`)

```toml
[project]
name = "my-project"
language = "python"
stack = "Python 3.11 + FastAPI"
version = "0.1.0"

[commands]
build = "python -m build"
test = "pytest"
lint = "ruff check ."
test_unit = "pytest tests/unit"
test_integration = "pytest tests/integration"

[paths]
src = "src"
tests = "tests"
docs = "docs"

[constraints]
zero_warnings = true
zero_mocks = false
nullable = true
```

---

## Quick Reference

### v2.0 Workflow Commands

```bash
# List and select workflow
devflow list-workflows
devflow select-workflow MODE-A

# Progress through workflow
devflow current      # Show current step
devflow done         # Check gates and advance
devflow approve X    # Mark item approved
```

### Legacy Commands

```bash
# Initialize
devflow init -l python -n "My Project"

# Requirements
devflow req new REQ-001 -t "Core System"
devflow feat new FEAT-001 -r REQ-001 -t "Database"
devflow task new -r REQ-001 -t "Setup DB"

# Status
devflow status
devflow validate
```

---

## Exit Codes

- `0` - Success
- `1` - General error (configuration not found, file not found, etc.)
- `2` - Invalid arguments
