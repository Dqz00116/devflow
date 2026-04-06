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
devflow [OPTIONS] COMMAND [ARGS]...

Options:
  --version          Show version and exit
  -c, --config PATH  Path to configuration file
  --help             Show help message
```

## Commands

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
- `docs/WORKFLOW.md` - Development workflow
- `docs/REQUIREMENTS.md` - Requirements guide
- `docs/requirements/TEMPLATE.md` - Requirement template
- `docs/features/TEMPLATE.md` - Feature template

---

### req - Manage Requirements

#### List Requirements

```bash
devflow req list [OPTIONS]
```

Options:
- `--status, -s` - Filter by status (draft, analyzing, analyzed, approved, in_progress, done)

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

Status values: `draft`, `analyzing`, `analyzed`, `approved`, `in_progress`, `done`

Example:
```bash
devflow req status REQ-001 approved
```

---

### feat - Manage Features

#### List Features

```bash
devflow feat list [OPTIONS]
```

Options:
- `--status, -s` - Filter by status (planned, in_progress, implemented, testing, done)
- `--requirement, -r` - Filter by requirement ID

#### Create Feature

```bash
devflow feat new <id> [OPTIONS]
```

Arguments:
- `id` - Feature ID (format: FEAT-001, FEAT-002, etc.)

Options:
- `--title, -t` - Feature title
- `--requirement, -r` - Related requirement ID (required)
- `--priority, -p` - Priority (low, medium, high, critical)

Example:
```bash
devflow feat new FEAT-001 --requirement REQ-001 --title "Database Module" --priority high
```

#### Show Feature

```bash
devflow feat show <id>
```

#### Update Status

```bash
devflow feat status <id> <status>
```

Status values: `planned`, `in_progress`, `implemented`, `testing`, `done`

Example:
```bash
devflow feat status FEAT-001 implemented
```

---

### task - Manage Tasks

#### List Tasks

```bash
devflow task list [OPTIONS]
```

Options:
- `--requirement, -r` - Filter by requirement ID
- `--status, -s` - Filter by status (backlog, todo, in_progress, review, done)

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

Example:
```bash
devflow task done TASK-001
```

---

### status - Project Overview

Show project status overview including requirements, features, and tasks.

```bash
devflow status
```

Displays:
- Project information (name, language, version)
- Requirements summary with status breakdown
- Features summary with status breakdown
- Tasks summary with status breakdown
- Recent tasks
- Suggested next steps

---

### validate - Validate Compliance

Validate project configuration and workflow compliance.

```bash
devflow validate
```

Checks:
- Configuration file exists
- Required workflow files exist (WORKFLOW.md, AGENTS.md, REQUIREMENTS.md)
- Project settings are valid

---

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

[workflow]
stages = ["backlog", "analyzing", "analyzed", "approved", "in_progress", "done"]
```

### Global Config

**Linux/macOS**: `~/.config/devflow/config.toml`

**Windows**: `%APPDATA%\devflow\config.toml`

---

## Supported Languages

DevFlow includes presets for:

| Language | Build | Test | Lint |
|----------|-------|------|------|
| Python | `python -m build` | `pytest` | `ruff check .` |
| JavaScript | `npm run build` | `npm test` | `npm run lint` |
| TypeScript | `npm run build` | `npm test` | `npm run lint` |
| Go | `go build ./...` | `go test ./...` | `golangci-lint run` |
| Rust | `cargo build` | `cargo test` | `cargo clippy` |
| .NET | `dotnet build` | `dotnet test` | `dotnet format` |

---

## Quick Reference

```bash
# Initialize
devflow init -l python -n "My Project"

# Requirements → Features → Tasks
devflow req new REQ-001 -t "Core System" -p high
devflow feat new FEAT-001 -r REQ-001 -t "Database" -p high
devflow task new -r REQ-001 -t "Setup DB connection"

# Check status
devflow status
devflow validate
```

---

## Exit Codes

- `0` - Success
- `1` - General error (configuration not found, file not found, etc.)
- `2` - Invalid arguments
