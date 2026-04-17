"""E2E usability test: use real local Kimi CLI to drive DevFlow v2.0 end-to-end.

This test:
1. Detects a locally installed Kimi CLI (kimi / kimi-cli / kimi-code)
2. Sets up a persistent TaskFlow project under tests/e2e/taskflow_e2e/
3. Cleans up any previous test artifacts before starting
4. Sends a comprehensive prompt to Kimi asking it to follow DevFlow
5. Waits for completion (up to 10 minutes)
6. Asserts that all expected files exist, tests pass, and workflow is complete
7. Preserves the project directory for manual inspection

Requirements:
- Kimi CLI must be installed and available in PATH
- The CLI should support non-interactive execution via `-c <prompt>` or stdin pipe
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KIMI_CANDIDATES = ["kimi", "kimi-cli", "kimi-code"]
REPO_SRC_DIR = str(Path(__file__).resolve().parents[2] / "src")

# Persistent project directory for inspection after test runs
E2E_PROJECT_DIR = Path(__file__).resolve().parent / "taskflow_e2e"


def _which_kimi() -> str | None:
    """Find Kimi executable in PATH."""
    for name in KIMI_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    return None


def _is_likely_ai_cli(executable: str) -> bool:
    """Heuristic: run --help and check for AI-related keywords."""
    try:
        result = subprocess.run(
            [executable, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        help_text = (result.stdout + result.stderr).lower()
        keywords = ["chat", "prompt", "message", "conversation", "ai", "model", "moonshot"]
        return any(k in help_text for k in keywords)
    except Exception:
        return False


def _discover_kimi_invocation(executable: str) -> tuple[list[str], dict[str, str]] | None:
    """Discover how to invoke Kimi in non-interactive mode.

    Kimi CLI supports `--print` (non-interactive) with `--input-format text` via stdin.
    Returns (args_list, extra_env) or None if we cannot determine a working mode.
    """
    # Strategy 1: Kimi Code CLI print mode (preferred)
    try:
        result = subprocess.run(
            [executable, "--print", "--yolo", "--input-format", "text", "--max-steps-per-turn", "100"],
            input="hello\n",
            capture_output=True,
            text=True,
            timeout=15,
        )
        stderr = result.stderr.lower()
        if (
            "unknown" not in stderr
            and "unrecognized" not in stderr
            and all(
                bad not in stderr
                for bad in [
                    "tty",
                    "terminal",
                    "curses",
                    "interactive",
                    "isatty",
                ]
            )
        ):
            return (["--print", "--yolo", "--input-format", "text", "--max-steps-per-turn", "100"], {})
    except Exception:
        pass

    # Strategy 2: try -c "hello"
    try:
        result = subprocess.run(
            [executable, "-c", "hello"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if "unknown" not in result.stderr.lower() and "unrecognized" not in result.stderr.lower():
            return (["-c"], {})
    except Exception:
        pass

    # Strategy 3: try chat subcommand with -c
    try:
        result = subprocess.run(
            [executable, "chat", "-c", "hello"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if "unknown" not in result.stderr.lower() and "unrecognized" not in result.stderr.lower():
            return (["chat", "-c"], {})
    except Exception:
        pass

    # Strategy 4: try run subcommand
    try:
        result = subprocess.run(
            [executable, "run", "hello"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if "unknown" not in result.stderr.lower():
            return (["run"], {})
    except Exception:
        pass

    # Strategy 5: plain stdin pipe fallback
    try:
        result = subprocess.run(
            [executable],
            input="hello\n",
            capture_output=True,
            text=True,
            timeout=15,
        )
        stderr = result.stderr.lower()
        if all(
            bad not in stderr
            for bad in [
                "tty",
                "terminal",
                "curses",
                "interactive",
                "isatty",
            ]
        ):
            return ([], {})
    except Exception:
        pass

    return None


@pytest.fixture(scope="module")
def kimi_executable() -> str:
    """Locate and validate Kimi CLI executable."""
    path = _which_kimi()
    if path is None:
        pytest.skip(
            "Kimi CLI not found in PATH. "
            "Please install it (e.g. from https://www.moonshot.cn/ or via your package manager) "
            f"and ensure one of these commands is available: {', '.join(KIMI_CANDIDATES)}"
        )

    if not _is_likely_ai_cli(path):
        pytest.skip(
            f"Command '{path}' was found but does not appear to be the Kimi AI CLI. "
            f"Please ensure the correct executable is in PATH."
        )

    invocation = _discover_kimi_invocation(path)
    if invocation is None:
        pytest.skip(
            f"Kimi CLI found at '{path}' but its non-interactive invocation mode could not be determined. "
            "Supported modes: -c <prompt>, chat -c <prompt>, run <prompt>, or stdin pipe. "
            "Try running it manually to find the right flag."
        )

    # Store invocation metadata for tests
    kimi_executable._invocation = invocation  # type: ignore[attr-defined]
    return path


def _run_kimi(executable: str, project_dir: Path, prompt: str) -> subprocess.CompletedProcess[str]:
    """Run Kimi CLI with the given prompt."""
    invocation = getattr(kimi_executable, "_invocation", ([], {}))
    args_prefix, extra_env = invocation

    env = os.environ.copy()
    env["DEVFLOW_ALLOW_SHELL"] = "1"
    env["PYTHONPATH"] = REPO_SRC_DIR
    env.update(extra_env)

    use_stdin = False
    if args_prefix == ["-c"]:
        cmd = [executable, "-c", prompt]
    elif args_prefix == ["chat", "-c"]:
        cmd = [executable, "chat", "-c", prompt]
    elif args_prefix == ["run"]:
        cmd = [executable, "run", prompt]
    elif "--print" in args_prefix:
        # Kimi print mode: flags go on command line, prompt via stdin
        cmd = [executable, *args_prefix]
        use_stdin = True
    else:
        # Generic stdin pipe mode
        cmd = [executable]
        use_stdin = True

    return subprocess.run(
        cmd,
        input=prompt if use_stdin else None,
        cwd=str(project_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,  # 10 minutes should be enough for a small project
    )


def _cleanup_previous_project() -> None:
    """Remove previous e2e project directory if it exists."""
    if E2E_PROJECT_DIR.exists():
        shutil.rmtree(E2E_PROJECT_DIR, ignore_errors=True)


def _setup_project() -> str:
    """Initialize DevFlow project, custom workflow, tests, and requirements.

    Returns the workflow_run_id if available.
    """
    _cleanup_previous_project()
    E2E_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_SRC_DIR

    # 1. Init project
    result = subprocess.run(
        [sys.executable, "-m", "devflow", "init", "--language", "python", "--name", "TaskFlow"],
        cwd=str(E2E_PROJECT_DIR),
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"devflow init failed: {result.stderr}"

    # 2. Create custom E2E workflow
    workflows_dir = E2E_PROJECT_DIR / ".devflow" / "workflows"
    (workflows_dir / "E2E-MODE-A.toml").write_text(
        '[workflow]\n'
        'id = "E2E-MODE-A"\n'
        'name = "E2E Feature Development"\n'
        'extends = ["MODE-A"]\n\n'
        '[[steps]]\n'
        'id = "implement-tdd"\n'
        'name = "Implement with TDD"\n'
        'prompt_file = "prompts/implement-tdd.md"\n'
        'gates = ["command_success:{test_command}"]\n'
        'next = "code-review"\n'
        '[[steps.fail_route]]\n'
        'min_fails = 2\n'
        'target = "MODE-B:debug-root-cause"\n',
        encoding="utf-8",
    )

    # 3. Create requirements.txt
    (E2E_PROJECT_DIR / "requirements.txt").write_text(
        "fastapi\nuvicorn\npytest\nhttpx\n",
        encoding="utf-8",
    )

    # 4. Create preset test file (trap test included)
    tests_dir = E2E_PROJECT_DIR / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_app.py").write_text(
        'import pytest\n'
        'from fastapi.testclient import TestClient\n'
        'from src.main import app\n\n'
        'client = TestClient(app)\n\n'
        'def test_get_tasks_empty():\n'
        '    response = client.get("/tasks")\n'
        '    assert response.status_code == 200\n'
        '    assert response.json() == []\n\n'
        'def test_create_task():\n'
        '    response = client.post("/tasks", json={"title": "Buy milk"})\n'
        '    assert response.status_code == 201\n'
        '    data = response.json()\n'
        '    assert data["title"] == "Buy milk"\n'
        '    assert data["completed"] is False\n'
        '    assert "id" in data\n\n'
        'def test_create_task_empty_title_rejects():\n'
        '    response = client.post("/tasks", json={"title": ""})\n'
        '    assert response.status_code == 422\n\n'
        'def test_toggle_task():\n'
        '    create = client.post("/tasks", json={"title": "Test"})\n'
        '    task = create.json()\n'
        '    response = client.patch(f"/tasks/{task[\'id\']}")\n'
        '    assert response.status_code == 200\n'
        '    assert response.json()["completed"] is True\n\n'
        'def test_delete_task():\n'
        '    create = client.post("/tasks", json={"title": "Delete me"})\n'
        '    task = create.json()\n'
        '    response = client.delete(f"/tasks/{task[\'id\']}")\n'
        '    assert response.status_code == 204\n',
        encoding="utf-8",
    )

    # 5. Ensure config test command points to our test file
    config_path = E2E_PROJECT_DIR / ".devflow" / "config.toml"
    config_text = config_path.read_text(encoding="utf-8")
    config_text = config_text.replace('test = "pytest"', 'test = "pytest tests/test_app.py -v"')
    config_path.write_text(config_text, encoding="utf-8")

    # Read run_id from state after init (it may or may not exist yet)
    state_path = E2E_PROJECT_DIR / ".devflow" / "state.toml"
    if state_path.exists():
        import toml
        state_data = toml.load(state_path)
        return str(state_data.get("workflow_run_id", ""))
    return ""


def _build_prompt(run_id: str) -> str:
    """Build the comprehensive prompt for Kimi."""
    return f"""You are an AI software engineer. Complete a full-stack project by strictly following the DevFlow v2.0 CLI workflow.

WORK DIRECTORY: {E2E_PROJECT_DIR}

CRITICAL RULES:
1. ALWAYS run `devflow current` first to know what to do
2. ONLY do what the current step says
3. After finishing the step, run `devflow done`
4. If `devflow done` fails, read the error, fix it, and run `devflow done` again
5. If a step requires `user_approved`, run `devflow approve <ITEM>` yourself and continue
6. NEVER skip steps and NEVER create files for future steps ahead of time
7. Do not stop until you see "Workflow complete!"

PROJECT: TaskFlow
- Backend: Python FastAPI in `src/main.py`
- Frontend: `index.html` with inline JavaScript (no build tools)
- Storage: in-memory Python list or dict (no SQLite/Postgres)
- Tests: `tests/test_app.py` already exists. You must make them pass.

API Requirements for `src/main.py`:
- `GET /tasks` → return list of tasks, newest first
- `POST /tasks` → accepts `{{"title": string}}`, returns 201; if title is empty string, return 422
- `PATCH /tasks/{{id}}` → toggle `completed` boolean, return updated task
- `DELETE /tasks/{{id}}` → delete task, return 204

Frontend Requirements for `index.html`:
- Input box + Add button
- Display list of tasks with toggle (complete/uncomplete) and delete buttons
- Must call the backend API endpoints above

WORKFLOW HINT (E2E-MODE-A gates):
- req-create: needs `docs/requirements/REQ-{run_id}.md`
- req-approve: needs REQ file containing `status: approved` + `docs/features/FEAT-{run_id}.md`
- brainstorm: needs `docs/superpowers/specs/DESIGN-{run_id}.md`
- write-plan: needs `docs/superpowers/plans/PLAN-{run_id}.md`
- implement-tdd: `pytest tests/test_app.py -v` must pass
- code-review: run `devflow approve CODE-REVIEW-{run_id}` then done
- test-run: tests must pass
- verify: needs `docs/evidence/EVIDENCE-{run_id}.md`
- finish: needs `docs/completion/COMPLETION-{run_id}.md` + REQ file containing `status: done`

STEP-BY-STEP GUIDE:
1. Run `devflow select-workflow E2E-MODE-A`
2. Loop:
   a. `devflow current`
   b. Do the step
   c. `devflow done`
   d. Fix any gate failures and repeat c
3. When you reach `implement-tdd`, write the FastAPI app and frontend, then run tests until they pass.
4. For `code-review`, self-approve with `devflow approve CODE-REVIEW-{run_id}`.
5. For `finish`, update the REQ file to include `status: done` and create the COMPLETION file.

IMPORTANT: Start by running `devflow select-workflow E2E-MODE-A` and then `devflow current`.
Do everything inside {E2E_PROJECT_DIR}.
"""


@pytest.mark.slow
def test_kimi_completes_taskflow_with_devflow(kimi_executable: str) -> None:
    """End-to-end test: Kimi CLI should complete the full DevFlow workflow.

    The project directory is persisted at tests/e2e/taskflow_e2e/ for manual inspection.
    Any previous run is cleaned up before starting.
    """
    run_id = _setup_project()
    initial_prompt = _build_prompt(run_id or "<run_id>")

    continuation_prompt = (
        "Continue the DevFlow workflow from the current step.\n"
        "1. Run `devflow current` to see what to do.\n"
        "2. Execute the step.\n"
        "3. Run `devflow done`.\n"
        "4. If gates fail, fix the issue and run `devflow done` again.\n"
        "5. If a step needs `user_approved`, run `devflow approve <ITEM>` yourself.\n"
        "Repeat until you see 'Workflow complete!'. Do not stop early."
    )

    log_path = E2E_PROJECT_DIR / "kimi_e2e.log"
    all_outputs: list[str] = []

    max_turns = 5
    for turn in range(max_turns):
        prompt = initial_prompt if turn == 0 else continuation_prompt
        result = _run_kimi(kimi_executable, E2E_PROJECT_DIR, prompt)

        turn_header = f"\n=== TURN {turn + 1} ===\n"
        turn_output = turn_header + result.stdout + "\n=== STDERR ===\n" + result.stderr
        all_outputs.append(turn_output)
        log_path.write_text("\n".join(all_outputs), encoding="utf-8")

        print(turn_output)
        print(f"\n=== TURN {turn + 1} RETURN CODE: {result.returncode} ===\n")

        state_path = E2E_PROJECT_DIR / ".devflow" / "state.toml"
        if not state_path.exists():
            if turn == max_turns - 1:
                pytest.fail("DevFlow state file was never created after max turns")
            continue

        import toml
        state = toml.load(state_path)
        current_step = state.get("current_step")

        # If we've reached finish, try one more turn to actually complete it
        if current_step == "finish":
            # One extra turn to run `devflow done` on finish and get "Workflow complete!"
            result = _run_kimi(kimi_executable, E2E_PROJECT_DIR, continuation_prompt)
            turn_header = "\n=== FINAL TURN ===\n"
            turn_output = turn_header + result.stdout + "\n=== STDERR ===\n" + result.stderr
            all_outputs.append(turn_output)
            log_path.write_text("\n".join(all_outputs), encoding="utf-8")
            print(turn_output)
            break
    else:
        pytest.fail(f"Workflow did not reach 'finish' after {max_turns} turns")

    # Final assertions based on filesystem state
    import toml
    state = toml.load(state_path)
    current_step = state.get("current_step")
    assert current_step == "finish", (
        f"Expected to end on step 'finish', got {current_step}"
    )

    run_id_actual = state.get("workflow_run_id", run_id or "")
    assert run_id_actual, "workflow_run_id missing from state"

    required_files = [
        E2E_PROJECT_DIR / "docs" / "requirements" / f"REQ-{run_id_actual}.md",
        E2E_PROJECT_DIR / "docs" / "features" / f"FEAT-{run_id_actual}.md",
        E2E_PROJECT_DIR / "docs" / "superpowers" / "specs" / f"DESIGN-{run_id_actual}.md",
        E2E_PROJECT_DIR / "docs" / "superpowers" / "plans" / f"PLAN-{run_id_actual}.md",
        E2E_PROJECT_DIR / "docs" / "evidence" / f"EVIDENCE-{run_id_actual}.md",
        E2E_PROJECT_DIR / "docs" / "completion" / f"COMPLETION-{run_id_actual}.md",
        E2E_PROJECT_DIR / "src" / "main.py",
        E2E_PROJECT_DIR / "index.html",
    ]
    for f in required_files:
        assert f.exists(), f"Missing expected artifact: {f.relative_to(E2E_PROJECT_DIR)}"

    req_content = (E2E_PROJECT_DIR / "docs" / "requirements" / f"REQ-{run_id_actual}.md").read_text()
    # Note: agent may overwrite the REQ file during finish; we only strictly
    # require the final gate condition (status: done) to be satisfied.
    assert "status: done" in req_content, "REQ file missing 'status: done'"

    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = REPO_SRC_DIR
    test_result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_app.py", "-v"],
        cwd=str(E2E_PROJECT_DIR),
        capture_output=True,
        text=True,
        env=test_env,
    )
    assert test_result.returncode == 0, (
        f"Tests failed after Kimi session:\n{test_result.stdout}\n{test_result.stderr}"
    )

    combined_output = "\n".join(all_outputs).lower()
    assert "workflow complete" in combined_output, (
        "Kimi output does not mention 'Workflow complete!' — it may have stopped early"
    )
