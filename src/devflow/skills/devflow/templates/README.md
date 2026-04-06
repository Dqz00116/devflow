# DevFlow

Universal AI Agent Development Workflow CLI - Works with any software project.

## Overview

DevFlow is a development workflow tool designed for AI-assisted software development. It combines:

- **CLI Tool** - Manage requirements, tasks, and project state
- **AI Agent Skills** - Structured workflow guidance for AI agents (see [SKILL.md](SKILL.md))
- **Universal Design** - Works with any programming language or framework

## Installation

**Using uv** (recommended):

```bash
git clone <repository-url>
cd devflow
uv pip install -e .
```

Or install directly from local path:

```bash
uv pip install /path/to/devflow
```

**Using pip**:

```bash
git clone <repository-url>
cd devflow
pip install -e .
```

## Quick Start

```bash
# Initialize a new project
devflow init --language python --name "My Project"

# Create a requirement (business need)
devflow req new REQ-001 --title "User Authentication"

# After REQ approved, create feature (technical implementation)
devflow feat new FEAT-001 -r REQ-001 -t "Auth Module"

# Create tasks for execution
devflow task new -r REQ-001 -t "Implement login endpoint"

# When implementation done, mark FEAT implemented
devflow feat status FEAT-001 implemented

# Then mark REQ done
devflow req status REQ-001 done

# Check status anytime
devflow status
```

## Documentation

- **[SKILL.md](SKILL.md)** - AI Agent workflow guide (for AI assistants)
- **[docs/WORKFLOW.md](skills/devflow/templates/WORKFLOW.md)** - Project-specific workflow template
- **[docs/CLI.md](skills/devflow/templates/CLI.md)** - Complete CLI reference

## Supported Languages

DevFlow includes presets for:

- **Python** (pytest, ruff)
- **JavaScript/TypeScript** (npm, jest)
- **Go** (go test, golangci-lint)
- **Rust** (cargo, clippy)
- **.NET** (dotnet, xunit)
- **Other** (custom configuration)

## Commands

See [docs/CLI.md](skills/devflow/templates/CLI.md) for complete CLI reference.

Quick reference:

```bash
devflow init --language python --name "My Project"  # Initialize
devflow req new REQ-001 --title "Core System"       # Create requirement
devflow feat new FEAT-001 -r REQ-001 -t "Database"  # Create feature
devflow task new -r REQ-001 -t "Implement"          # Create task
devflow status                                       # Show status
```

## Configuration

DevFlow uses TOML configuration files:

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

[paths]
src = "src"
tests = "tests"
docs = "docs"
```

## Development Workflow

DevFlow implements an 8-stage feature development workflow:

```
Stage 0: Requirement    → Define and approve requirements
Stage 1: Brainstorming  → Explore design options
Stage 2: Writing Plans  → Create implementation plan
Stage 3: Implementation → TDD + code review
Stage 4: Code Review    → Review with AI/human
Stage 5: Testing        → Run all tests
Stage 6: Verification   → Verify claims
Stage 7: Finish         → Merge and cleanup
```

See [SKILL.md](SKILL.md) for complete workflow details.

## License

MIT License
