# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DevFlow v2.0 is a Python CLI tool for AI-assisted software development using TOML-based progressive disclosure workflows. It orchestrates step-by-step workflows (e.g., feature development, debugging) with gate-based verification and automatic fail-route escalation.

## Common Commands

- **Install locally**: `pip install -e .`
- **Install from PyPI**: `pip install agent-devflow`
- **Run tests**: `pytest` (or `pytest tests/test_<module>.py` for a single file)
- **Run a single test**: `pytest tests/test_<module>.py::TestClass::test_method -v`
- **Lint**: `ruff check .`
- **Format**: `black .` (line length is 100 per `pyproject.toml`)
- **Type check**: `mypy src/devflow`
- **Run CLI**: `python -m devflow` or `devflow`
- **Validate project**: `devflow validate` (checks `.devflow/workflows/`, `SKILL.md`, and configured test command)

## Release to PyPI

Always use the release script to avoid uploading stale artifacts:

```bash
# Preview
uv run python scripts/release.py --dry-run patch

# Execute (bumps version, cleans dist, builds, verifies, commits, tags, pushes, uploads)
uv run python scripts/release.py patch   # or minor / major
```

The script guards against:
- Stale files in `dist/` (cleans before build)
- Version mismatches (verifies dist filenames match pyproject.toml)
- Unclean git state (warns + prompts for confirmation)

> **Note:** `command_success` gates require `DEVFLOW_ALLOW_SHELL=1` to execute. Tests that exercise shell gates already set this (see `tests/test_workflow_engine.py`).

## Architecture

### Core Modules

- **`src/devflow/cli.py`** — Click-based CLI entry point. Defines two categories of commands: legacy document-management commands (`req`, `feat`, `task`, `status`) and workflow v2 commands (`current`, `done`, `select-workflow`, `list-workflows`, `back`, `approve`, `set`). The CLI uses `WorkflowEngine.from_project()` or `WorkflowEngine.from_workflow()` to load the active workflow.

- **`src/devflow/workflow_engine.py`** — `WorkflowEngine` is the central orchestrator. It loads workflows, tracks the current step via `StateStore`, checks gates via `gate_checker.check_all_gates()`, and handles advancement (`advance()`), backtracking (`go_back()`), and cross-workflow transitions. It also injects config variables into state before resolving gates/prompts.

- **`src/devflow/workflow_parser.py`** — Parses TOML workflow files into `Workflow`, `Step`, and `FailRoute` dataclasses. Supports workflow inheritance via `extends = ["MODE-A"]` and merges parent/child workflows with `merge_workflows()`. Prompt files referenced by `prompt_file` are resolved relative to `.devflow/prompts/` first, then the workflow directory.

- **`src/devflow/gate_checker.py`** — Evaluates gate conditions (`file_exists`, `file_contains`, `file_exists_pattern`, `file_contains_pattern`, `user_approved`, `command_success`, `state_set`). Variables like `{test_command}` and `{workflow_run_id}` are resolved against `StateStore` before checking. `command_success` runs shell commands with a 60-second timeout, but only if `DEVFLOW_ALLOW_SHELL=1` is set in the environment; otherwise it fails immediately.

- **`src/devflow/state_store.py`** — Simple TOML-backed key-value store at `.devflow/state.toml`. Tracks `current_workflow`, `current_step`, `workflow_run_id`, user-defined variables, `approved_items`, and per-step fail counts (`{step_id}_fail_count`).

- **`src/devflow/config.py`** — Loads `.devflow/config.toml` and provides typed access to `project`, `commands`, `paths`, `constraints`, and `workflow` settings. Includes language presets for Python, JS/TS, Go, Rust, and .NET.

### Ralph Loop Modules

- **`src/devflow/loop_engine.py`** — `LoopEngine` drives the workflow autonomously. It reads `.devflow/backlog.json`, maps tasks to workflow steps, spawns an agent runner, auto-validates via `engine.advance()`, and creates VCS checkpoints on success. Supports `max_iterations`, pause on block, and progress logging.
- **`src/devflow/vcs.py`** — VCS abstraction layer (`VCSDriver` base class with `GitDriver`, `SVNDriver`, `NoVCSDriver`). Auto-detects Git/SVN/no-VCS. Provides `checkpoint()`, `get_last_checkpoint_id()`, `has_uncommitted_changes()`, and `get_diff_summary()`. Configurable via `project.vcs` in `config.toml`.
- **`src/devflow/backlog.py`** — Read/write `.devflow/backlog.json`. Tracks tasks with `id`, `workflow_id`, `step_id`, `passes`, `checkpoint_id`, and `metadata`. Can auto-generate from a workflow TOML via `Backlog.generate_from_workflow()`.
- **`src/devflow/progress.py`** — Append-only `ProgressLogger` for `.devflow/progress.md`. Each entry includes timestamp, step ID, patterns learned, gotchas, and checkpoint reference. Summaries are injected into agent prompts for cross-iteration memory.
- **`src/devflow/agent_runner.py`** — In-process agent wrapper for `--tool local`. Executes a prompt against the current workflow step and returns results. Used when no external CLI is available.

### Key Behavioral Patterns

- **Workflow files** live in `.devflow/workflows/*.toml`. Bundled defaults (MODE-A.toml, MODE-B.toml) and prompt files are copied from `src/devflow/data/` during `devflow init`.

- **Progressive disclosure**: `devflow current` renders the current step’s prompt and gates. `devflow done` checks gates and advances (or routes on failure). Only `advance()` should move workflow state forward.

- **Fail routes** are evaluated when gates fail. The tentative fail count is incremented, matched against `[[steps.fail_route]]` entries in declaration order, and persisted only if a route matches or no route matches. Fail counts persist across visits and reset only when gates pass.

- **Cross-workflow references** use the format `WORKFLOW-ID:STEP-ID` in `next` or `fail_route.target`. On transition, `WorkflowEngine._switch_to_workflow()` updates the engine and state; `workflow_run_id` is preserved.

- **Config variables** (`{test_command}`, `{lint_command}`, `{build_command}`, `{workflow_run_id}`, etc.) are injected into state by `_inject_config_variables()` before gate/prompt resolution.

- **`devflow init`** creates `.devflow/`, docs directories, and renders `SKILL.md` from Jinja2 templates in `src/devflow/templates/`. Workflow and prompt files are copied from the DevFlow repository's own `.devflow/` when running from source; when installed as a package, it falls back to bundled files in `src/devflow/data/`.

### Testing Conventions

- Tests are in `tests/` using pytest. Fixtures typically create temporary project roots with `.devflow/workflows/`, `.devflow/config.toml`, and copied bundled data from `src/devflow/data/workflows/`.
