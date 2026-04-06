---
name: devflow
description: Use when starting a new software project or need to establish a structured AI-assisted development workflow with requirements tracking and staged development process
---

# DevFlow

DevFlow is a universal AI-assisted development workflow system. It provides structured guidance for AI agents plus CLI tooling to track requirements and tasks.

## What You Get

- **8-Stage Development Workflow** - From requirement to finish
- **CLI Tool** - Track requirements (`req`) and tasks (`task`)
- **Project Templates** - AGENTS.md, WORKFLOW.md, REQUIREMENTS.md
- **5 Iron Laws** - Quality enforcement rules

## Quick Start

### 1. Install DevFlow CLI

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

### 2. Initialize Project

```bash
devflow init --language python --name "My Project"
```

This creates:
- `.devflow/config.toml` - Project configuration
- `AGENTS.md` - AI context for this project
- `docs/WORKFLOW.md` - Complete workflow guide
- `docs/REQUIREMENTS.md` - Requirements guide
- `docs/requirements/TEMPLATE.md` - Requirement template

### 3. Start Development

```bash
# Check current status
devflow status

# Create first requirement
devflow req new REQ-001 --title "Feature Name"

# Follow the workflow in docs/WORKFLOW.md
```

## Workflow Overview

```mermaid
flowchart LR
    REQ[Requirement] --> BRAIN[Brainstorming]
    BRAIN --> PLAN[Writing Plans]
    PLAN --> IMPL[Implementation]
    IMPL --> REVIEW[Code Review]
    REVIEW --> TEST[Testing]
    TEST --> VERIFY[Verification]
    VERIFY --> FINISH[Finish]
```

## When to Use Each Component

| Component | Use When | Location |
|-----------|----------|----------|
| **DevFlow CLI** | Managing requirements/tasks, checking status | Run `devflow --help` |
| **SKILL.md** (this file) | Installing, getting started | Project root |
| **WORKFLOW.md** | Following development stages | `docs/WORKFLOW.md` |
| **AGENTS.md** | Understanding project context | Project root |
| **DevFlow Skill** | Detailed workflow guidance | `skills/devflow/SKILL.md` |

## CLI Commands

```bash
# Quick reference - see docs/CLI.md for complete reference
devflow init                    # Initialize new project
devflow req new REQ-001         # Create requirement
devflow feat new FEAT-001 -r REQ-001  # Create feature
devflow task new -r REQ-001     # Create task
devflow status                  # Show project status
```

See [docs/CLI.md](docs/CLI.md) for complete CLI reference.

## Next Steps

1. **Initialize**: Run `devflow init` in your project directory
2. **Read Workflow**: Open `docs/WORKFLOW.md` for complete workflow
3. **Read AGENTS.md**: Review project-specific context
4. **Create Requirement**: `devflow req new REQ-001 --title "First Feature"`

## Supported Languages

- Python, JavaScript/TypeScript, Go, Rust, .NET, Other (custom)

## Documentation Map

```
.
├── SKILL.md              ← You are here (entry point)
├── README.md             # User installation guide
├── skills/devflow/
│   └── SKILL.md          # Detailed AI workflow skill
└── After init:
    ├── AGENTS.md         # Project context
    └── docs/
        ├── WORKFLOW.md   # Complete workflow
        └── REQUIREMENTS.md
```

---

*DevFlow v1.0 - Universal AI Development Workflow*
