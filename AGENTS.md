# AGENTS.md

Guidance for AI agents (OpenCode / Claude / others) working in this repo. Read alongside `CLAUDE.md`, which holds the detailed module architecture — this file captures only what an agent is likely to get wrong.

## Project

`agent-devflow` — a Python CLI (`devflow`) for TOML-based, gate-driven dev workflows. Python >= 3.9. Build backend: hatchling. `uv` is the primary tool runner (`uv.lock` is committed).

## Commands

```bash
pip install -e .                 # editable install (or: uv pip install -e .)
pytest                           # unit + integration suite (slow e2e auto-deselected, see below)
pytest tests/test_workflow_engine.py -v                      # one file
pytest tests/test_cli.py::TestClass::test_method -v          # one test
ruff check .                     # lint
black .                          # format (line length 100)
mypy src/devflow                 # type check (strict — see Conventions)
python -m devflow                # run the CLI (or: devflow)
devflow validate                 # check .devflow/ + SKILL.md + configured test command
```

## Tests — non-obvious

- Default `pytest` applies `addopts` from `pyproject.toml`: `-v --tb=short -m "not slow"`, and ignores `tests/e2e/{buckshot,taskflow}_e2e/`.
- The two **e2e tests** (`tests/e2e/test_kimi_*.py`) are marked `slow` and **deselected by default**. They drive real external AI CLIs (`kimi`, `claude`, `opencode`) from PATH and `pytest.skip()` if none are found. Run with: `pytest -m slow`.
- Most unit tests build a throwaway project root in a tmpdir and copy bundled data from `src/devflow/data/{workflows,prompts}/`. Follow that pattern when adding fixtures — don't touch the real `.devflow/`.
- **Baseline is not always green** — `main` has carried pre-existing test failures (notably some `tests/test_workflow_engine.py` cross-workflow-transition cases) unrelated to your change. Capture the pre-change baseline (`pytest -q` before editing) before treating any failure as your regression.

## Release — never hand-edit versions

The package version lives in **3 files** and must stay in sync: `pyproject.toml`, `src/devflow/__init__.py` (`__version__`), and `src/devflow/config.py` (`version:`). `scripts/release.py` enforces this. Always release via:

```bash
uv run python scripts/release.py --dry-run patch   # preview
uv run python scripts/release.py patch             # bump + build + verify + commit + tag + push + publish
```

The package version (e.g. `0.1.6`) is independent of the marketing "v2.0" in `README.md` / `CLAUDE.md` — don't "fix" the mismatch.

## Workflow engine gotchas

- `command_success:` gates **execute shell** and are disabled unless `DEVFLOW_ALLOW_SHELL=1` is set in the env (60s timeout). Tests that exercise them set this flag.
- Config variables (`{test_command}`, `{lint_command}`, `{workflow_run_id}`, ...) are injected into state before gates/prompts resolve. A gate with an unresolved `{var}` fails with a clear message rather than passing silently.
- `devflow init` behavior differs by install: from a source checkout it copies the repo's own `.devflow/` as the template; installed as a package, it falls back to bundled `src/devflow/data/`.
- The wheel packages `src/devflow` and maps `src/devflow/data` -> `devflow/data` as shared data. Bundled workflow/prompt defaults live there.
- `.devflow/state.toml` is runtime state and is gitignored — never commit it.
- Fail-route counts persist across step visits and reset only when gates pass (this is the escalation mechanism).
- Two command families exist: workflow v2 (`current`, `done`, `select-workflow`, `list-workflows`, `back`, `approve`, `set`, `run`, `loop-status`, `sync-backlog`, `loop-reset`, `workflow-status`) is the intended path for agents; legacy doc-management (`req`, `feat`, `task`, `status`) bypasses the engine.

## Conventions

- Line length **100** (black + ruff). Ruff enabled rules: `E F I W C90`.
- mypy is **strict**: `disallow_untyped_defs = true`, `warn_return_any = true` — annotate all function signatures.
- `zero_warnings = true` is set under `[constraints]` in `.devflow/config.toml` — keep lint / type / test output clean.

## Where to look deeper

- `CLAUDE.md` — authoritative per-module architecture (WorkflowEngine, gate types, fail routes, Ralph Loop, VCS drivers). Start here for "how does X work".
- `.devflow/` — the repo's own live workflow project (MODE-A / MODE-B, prompts, config). It is also the default `init` template when running from source.
