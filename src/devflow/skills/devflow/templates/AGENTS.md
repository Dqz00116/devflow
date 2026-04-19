# Project Context

This file provides context for AI agents working on this project.

## Tech Stack

**Language**: {{ project.language }}
**Stack**: {{ project.stack }}
**Version**: {{ project.version }}

## Constraints

{% if constraints.zero_warnings %}
- **ZERO warnings** - All builds must have zero warnings
{% endif %}
{% if constraints.zero_mocks %}
- **ZERO mocks** - Use real instances only in tests
{% endif %}
{% if constraints.nullable %}
- **Nullable enabled** - Use nullable reference types
{% endif %}

## DevFlow v2.0 — CRITICAL: Read This First

This project uses **DevFlow** — a TOML-based progressive disclosure workflow system. You MUST follow the workflow to complete tasks correctly.

### Progressive Disclosure Loop

DevFlow reveals **one step at a time**. Never read ahead, never skip steps.

```
1. devflow current        → Read the current step instruction
2. Execute the step       → Do exactly what the prompt says
3. devflow done           → Check gates → advance or route on failure
4. If gates fail          → Read error → fix → devflow done again
5. Repeat until "Workflow complete!"
```

**Core rule: Only advance through `devflow done`. Do NOT skip steps. Do NOT create files for future steps.**

### Key Commands

```bash
# Workflow progression (PRIMARY — use these)
devflow list-workflows              # List available workflows
devflow select-workflow MODE-A      # Select a workflow
devflow current                     # Show current step instruction
devflow done                        # Check gates and advance
devflow back                        # Go back one step
devflow approve <item>              # Mark item as user-approved

# Ralph Loop — Autonomous execution
devflow run [--tool local] [--max-iterations 10]   # Start autonomous loop
devflow loop-status                                  # Show loop status
devflow sync-backlog                                 # Generate backlog from workflow
devflow loop-reset                                   # Reset loop progress

# Project info
devflow workflow-status             # Show workflow status
devflow validate                    # Check compliance
```

### Gate System

Each step has gates that must pass before advancing:

- `file_exists:path` — File must exist
- `file_contains:path:content` — File must contain text
- `command_success:{test_command}` — Command exits 0 (config-resolved)
- `user_approved:ITEM` — Requires `devflow approve ITEM`
- `state_set:var` — State variable must be set

Config variables like `{test_command}`, `{workflow_run_id}` are resolved from `.devflow/config.toml`.

### Fail Routes

When gates fail, the workflow may automatically route based on failure count:

```
fails 1-2 times → retry or fallback step
fails 3+ times  → escalate to human
```

Fail count persists across visits (resets only when gates pass).

### Workflows

**MODE-A: Feature Development**
1. req-create → 2. req-approve → 3. brainstorm → 4. write-plan → 5. implement-tdd → 6. code-review → 7. test-run → 8. verify → 9. finish

**MODE-B: Debug**
1. debug-root-cause → 2. debug-pattern → 3. debug-hypothesis → 4. debug-fix → 5. debug-question → 6. debug-verify → 7. debug-finish → (auto → MODE-A:write-plan)

Cross-workflow references use `WORKFLOW-ID:STEP-ID` format.

### 5 Iron Laws

| # | Law | Severity | If Violated |
|---|-----|----------|-------------|
| 1 | Read `using-superpowers` skill first | Rigid | Stop, read skill |
| 2 | TDD: Test before code | Rigid | Delete code, restart |
| 3 | Verify before claim | Rigid | Run test → Read → Claim |
| 4 | Root cause before fix | Strong | Ask human after 3 fails |
| 5 | Debug → Repeat full cycle | Strong | Complete plan→test before commit |

## Project Structure

```
{{ project.name }}/
├── .devflow/              # DevFlow configuration
│   ├── workflows/         # Workflow definitions (TOML)
│   ├── prompts/           # Reusable prompt files
│   ├── config.toml        # Project config
│   └── state.toml         # Current state (gitignored)
├── {{ paths.src }}/       # Source code
├── {{ paths.tests }}/     # Tests
├── {{ paths.docs }}/      # Documentation
│   ├── requirements/      # REQ files
│   ├── features/          # FEAT files
│   ├── superpowers/specs/ # Design docs
│   ├── superpowers/plans/ # Implementation plans
│   ├── evidence/          # Verification evidence
│   ├── debug/             # Debug analysis
│   └── completion/        # Workflow completion summaries
└── AGENTS.md              # This file
```

## Key Commands

```bash
# Build
{{ commands.build }}

# Test
{{ commands.test }}
{{ commands.test_unit }}
{{ commands.test_integration }}

# Lint
{{ commands.lint }}
```

## Coding Standards

- Follow existing code patterns
- Write tests before implementation (TDD)
- Keep functions small and focused
- Use meaningful variable names
- Add docstrings for public APIs
- Run linting before committing

## AI Agent Guidelines

When working on this project:

1. **ALWAYS** run `devflow current` first to know what to do
2. **ALWAYS** check requirements before starting (`devflow req list`)
3. **ALWAYS** follow TDD (test before code)
4. **ALWAYS** verify before claiming done (run tests)
5. **ALWAYS** update requirement status when complete
6. **NEVER** skip steps or create files for future steps ahead of time
7. **NEVER** stop until you see "Workflow complete!"

Use the DevFlow CLI to track work:
```bash
devflow status      # See current project status
devflow validate    # Check workflow compliance
```

---

*Generated by DevFlow v2.0*
