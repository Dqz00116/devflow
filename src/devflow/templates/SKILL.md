---
name: devflow
description: Use when a task requires structured development workflow with gate-based verification, progressive disclosure, or step-by-step advancement. Use for feature development, debugging, or any task where tests must pass before proceeding to the next step.
---

# DevFlow

DevFlow is a CLI-driven progressive disclosure workflow. You advance one verified step at a time.

## When to Use

- Task requires writing requirements, design docs, or code in stages
- You need gate-based verification (tests must pass before advancing)
- User mentions `devflow` commands or `.devflow/` directory
- Structured feature development or systematic debugging is needed

**When NOT to use:** The task is a simple one-off change that doesn't need staged workflow.

## Quick Start

```bash
devflow --help          # Verify CLI is installed
```

If `devflow` is not found, install first:

```bash
pip install agent-devflow     # From PyPI
```

Or from source:

```bash
pip install -e .
```

If the project does not have a `.devflow/` directory, initialize it:

```bash
devflow init --language <language> --name "<project-name>"
```

Then start the workflow:

```bash
devflow list-workflows              # See available workflows
devflow select-workflow MODE-A      # Pick one
devflow current                     # Read current step
```

## Core Loop (ALWAYS follow this)

```
1. devflow current     → Read what to do
2. Execute the step    → Write code, create docs, run tests
3. devflow done        → Check gates → advance or retry
4. Repeat until "Workflow complete!"
```

**Core rule: Only advance through `devflow done`. Never skip steps. Never create files for future steps.**

## Commands

| Command | Purpose |
|---------|---------|
| `devflow current` | Show current step instruction |
| `devflow done` | Check gates and advance |
| `devflow back` | Go back one step |
| `devflow approve ITEM` | Mark item as user-approved |
| `devflow set KEY VALUE` | Set state variable |
| `devflow list-workflows` | List available workflows |
| `devflow select-workflow ID` | Select and start a workflow |
| `devflow run` | Start autonomous Ralph Loop |

## Gate Types

Gates block advancement until satisfied:

- `file_exists:path` — File must exist
- `file_contains:path:content` — File must contain text
- `command_success:{test_command}` — Command exits 0
- `user_approved:ITEM` — Requires `devflow approve ITEM`
- `state_set:var` — State variable must be set

## Fail Routes

When gates fail, the workflow may route based on failure count:

```
fails 1-2 → retry or fallback step
fails 3+  → escalate to human
```

Fail count persists across visits (resets only when gates pass).

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Writing code before `devflow current` | Stop. Run `devflow current` first |
| Creating files for future steps | Only create what the current step asks for |
| Skipping `devflow done` | All advancement must go through `devflow done` |
| Ignoring gate failures | Fix the issue, then `devflow done` again |

## 5 Iron Laws

| # | Law | Severity |
|---|-----|----------|
| 1 | Read `using-superpowers` skill first | Rigid |
| 2 | TDD: Test before code | Rigid |
| 3 | Verify before claim | Rigid |
| 4 | Root cause before fix | Strong |
| 5 | Debug → Repeat full cycle | Strong |

