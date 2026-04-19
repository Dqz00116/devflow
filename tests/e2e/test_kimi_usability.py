"""E2E usability test: use real local AI CLIs to drive DevFlow v2.0 end-to-end.

This test:
1. Detects locally installed AI CLIs (kimi, claude, opencode)
2. Sets up a persistent ChatIM project under tests/e2e/taskflow_e2e/
3. Cleans up any previous test artifacts before starting
4. Sends a prompt to each available CLI asking it to follow DevFlow
5. Waits for completion (up to 10 minutes per tool)
6. Asserts that all expected files exist, tests pass, and workflow is complete
7. Generates a Markdown comparison report at tests/e2e/reports/

Requirements:
- At least one supported AI CLI must be installed and available in PATH
- Each CLI should support non-interactive execution
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

REPO_SRC_DIR = str(Path(__file__).resolve().parents[2] / "src")

# Persistent project directory for inspection after test runs
E2E_PROJECT_DIR = Path(__file__).resolve().parent / "taskflow_e2e"
E2E_REPORTS_DIR = Path(__file__).resolve().parent / "reports"


@dataclass
class ToolConfig:
    """Configuration for an AI CLI tool."""

    tool_id: str
    command_names: list[str]
    help_keywords: list[str]


# Supported AI tools and their configurations
SUPPORTED_TOOLS: list[ToolConfig] = [
    ToolConfig(
        tool_id="kimi",
        command_names=["kimi", "kimi-cli", "kimi-code"],
        help_keywords=["chat", "prompt", "message", "ai", "model", "moonshot"],
    ),
    ToolConfig(
        tool_id="claude",
        command_names=["claude", "claude-code"],
        help_keywords=["chat", "prompt", "message", "ai", "model", "anthropic", "claude"],
    ),
    ToolConfig(
        tool_id="opencode",
        command_names=["opencode", "opc"],
        help_keywords=["chat", "prompt", "message", "ai", "model", "opencode"],
    ),
]


def _which_tool(config: ToolConfig) -> str | None:
    """Find tool executable in PATH."""
    for name in config.command_names:
        path = shutil.which(name)
        if path:
            return path
    return None


def _is_likely_ai_cli(executable: str, keywords: list[str]) -> bool:
    """Heuristic: run --help and check for AI-related keywords."""
    try:
        result = subprocess.run(
            [executable, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        help_text = (result.stdout + result.stderr).lower()
        return any(k in help_text for k in keywords)
    except Exception:
        return False


def _discover_invocation(
    executable: str, config: ToolConfig
) -> tuple[list[str], dict[str, str]] | None:
    """Discover how to invoke an AI CLI in non-interactive mode.

    Returns (args_list, extra_env) or None if we cannot determine a working mode.
    """
    tool_id = config.tool_id

    # Tool-specific preset strategies
    if tool_id == "kimi":
        presets = [
            (["--print", "--yolo", "--input-format", "text", "--max-steps-per-turn", "100"], {}),
            (["-c"], {}),
            (["chat", "-c"], {}),
            (["run"], {}),
        ]
    elif tool_id == "claude":
        presets = [
            (["-p", "--input-format", "text"], {}),
            (["--print", "--input-format", "text"], {}),
            (["-p"], {}),
            (["--print"], {}),
        ]
    elif tool_id == "opencode":
        presets = [
            (["run"], {}),
            (["run", "--format", "json"], {}),
        ]
    else:
        presets = []

    # Try presets first
    for args_prefix, extra_env in presets:
        try:
            if tool_id in ("kimi", "claude"):
                result = subprocess.run(
                    [executable, *args_prefix],
                    input="hello\n",
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
            elif tool_id == "opencode":
                result = subprocess.run(
                    [executable, *args_prefix, "hello"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
            else:
                result = subprocess.run(
                    [executable, *args_prefix],
                    input="hello\n",
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

            stderr = result.stderr.lower()
            if (
                "unknown" not in stderr
                and "unrecognized" not in stderr
                and "invalid" not in stderr
                and all(
                    bad not in stderr
                    for bad in ["tty", "terminal", "curses", "interactive", "isatty"]
                )
            ):
                return (args_prefix, extra_env)
        except Exception:
            pass

    # Generic fallback strategies
    generic_strategies = [
        (["-c"], {}),
        (["chat", "-c"], {}),
        (["run"], {}),
    ]
    for args_prefix, extra_env in generic_strategies:
        try:
            result = subprocess.run(
                [executable, *args_prefix, "hello"],
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
                    for bad in ["tty", "terminal", "curses", "interactive", "isatty"]
                )
            ):
                return (args_prefix, extra_env)
        except Exception:
            pass

    # Plain stdin pipe fallback
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
            for bad in ["tty", "terminal", "curses", "interactive", "isatty"]
        ):
            return ([], {})
    except Exception:
        pass

    return None


def _find_available_tools() -> list[tuple[ToolConfig, str, tuple[list[str], dict[str, str]]]]:
    """Find all available AI CLIs and their invocation modes.

    Returns a list of (ToolConfig, executable_path, invocation) tuples.
    """
    available = []
    for config in SUPPORTED_TOOLS:
        path = _which_tool(config)
        if path is None:
            continue

        if not _is_likely_ai_cli(path, config.help_keywords):
            continue

        invocation = _discover_invocation(path, config)
        if invocation is None:
            continue

        available.append((config, path, invocation))

    return available


# Discover available tools at module load time
_AVAILABLE_TOOLS = _find_available_tools()


# --- Project setup ---


def _cleanup_previous_project() -> None:
    """Remove previous e2e project directory if it exists."""
    if not E2E_PROJECT_DIR.exists():
        return

    for attempt in range(3):
        try:
            shutil.rmtree(E2E_PROJECT_DIR)
            break
        except PermissionError:
            if attempt < 2:
                time.sleep(0.5)
            else:
                raise

    if E2E_PROJECT_DIR.exists():
        raise RuntimeError(
            f"Failed to clean up previous E2E project: {E2E_PROJECT_DIR}"
        )


def _setup_project() -> str:
    """Initialize DevFlow project, custom workflow, tests, and requirements."""
    _cleanup_previous_project()
    E2E_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_SRC_DIR

    # 1. Init project
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "devflow",
            "init",
            "--language",
            "python",
            "--name",
            "ChatIM",
        ],
        cwd=str(E2E_PROJECT_DIR),
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"devflow init failed: {result.stderr}"

    # 2. Create custom E2E workflow
    workflows_dir = E2E_PROJECT_DIR / ".devflow" / "workflows"
    (workflows_dir / "E2E-MODE-A.toml").write_text(
        "[workflow]\n"
        'id = "E2E-MODE-A"\n'
        'name = "E2E Feature Development"\n'
        'extends = ["MODE-A"]\n\n'
        '[[steps]]\n'
        'id = "implement-sdd"\n'
        'name = "Implement with SDD"\n'
        'prompt_file = "prompts/implement-sdd.md"\n'
        'gates = ["command_success:{test_command}"]\n'
        'next = "code-review"\n'
        "[[steps.fail_route]]\n"
        "min_fails = 2\n"
        'target = "MODE-B:debug-root-cause"\n',
        encoding="utf-8",
    )

    # 3. Create requirements.txt
    (E2E_PROJECT_DIR / "requirements.txt").write_text(
        "fastapi\nuvicorn\npytest\nhttpx\n",
        encoding="utf-8",
    )

    # 4. Create preset test file
    tests_dir = E2E_PROJECT_DIR / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_app.py").write_text(
        "import pytest\n"
        "from fastapi.testclient import TestClient\n"
        "from src.main import app\n\n"
        "client = TestClient(app)\n\n"
        'def test_register_user():\n'
        '    response = client.post("/users", json={"username": "alice", "password": "secret"})\n'
        "    assert response.status_code == 201\n"
        "    data = response.json()\n"
        '    assert data["username"] == "alice"\n'
        '    assert "id" in data\n'
        '    assert "password" not in data\n\n'
        'def test_register_duplicate_user_rejects():\n'
        '    client.post("/users", json={"username": "bob", "password": "secret"})\n'
        '    response = client.post("/users", json={"username": "bob", "password": "secret"})\n'
        "    assert response.status_code == 409\n\n"
        'def test_login_success():\n'
        '    client.post("/users", json={"username": "charlie", "password": "secret"})\n'
        '    response = client.post("/login", json={"username": "charlie", "password": "secret"})\n'
        "    assert response.status_code == 200\n"
        '    assert "token" in response.json()\n\n'
        'def test_login_wrong_password():\n'
        '    client.post("/users", json={"username": "dave", "password": "secret"})\n'
        '    response = client.post("/login", json={"username": "dave", "password": "wrong"})\n'
        "    assert response.status_code == 401\n\n"
        'def test_send_message_and_get_conversation():\n'
        '    client.post("/users", json={"username": "sender", "password": "s"})\n'
        '    client.post("/users", json={"username": "receiver", "password": "r"})\n'
        '    msg = {"from_user": "sender", "to_user": "receiver", "content": "hello"}\n'
        '    post_resp = client.post("/messages", json=msg)\n'
        "    assert post_resp.status_code == 201\n"
        '    assert post_resp.json()["read"] is False\n\n'
        '    get_resp = client.get("/messages/sender")\n'
        "    assert get_resp.status_code == 200\n"
        '    msgs = get_resp.json()\n'
        '    assert len(msgs) == 1\n'
        '    assert msgs[0]["content"] == "hello"\n'
        '    assert msgs[0]["from_user"] == "sender"\n\n'
        'def test_send_to_nonexistent_user_returns_404():\n'
        '    client.post("/users", json={"username": "only", "password": "x"})\n'
        '    msg = {"from_user": "only", "to_user": "nobody", "content": "hi"}\n'
        '    response = client.post("/messages", json=msg)\n'
        "    assert response.status_code == 404\n\n"
        'def test_messages_isolated_between_users():\n'
        '    client.post("/users", json={"username": "a", "password": "x"})\n'
        '    client.post("/users", json={"username": "b", "password": "x"})\n'
        '    client.post("/users", json={"username": "c", "password": "x"})\n'
        '    client.post("/messages", json={"from_user": "a", "to_user": "b", "content": "ab"})\n'
        '    msgs = client.get("/messages/c").json()\n'
        '    assert len(msgs) == 0\n'
        '    msgs = client.get("/messages/b").json()\n'
        '    assert len(msgs) == 1\n\n'
        'def test_unread_count_and_read_status():\n'
        '    client.post("/users", json={"username": "u1", "password": "x"})\n'
        '    client.post("/users", json={"username": "u2", "password": "x"})\n'
        '    client.post("/messages", json={"from_user": "u1", "to_user": "u2", "content": "m1"})\n'
        '    contacts = client.get("/contacts/u2").json()\n'
        '    assert len(contacts) == 1\n'
        '    assert contacts[0]["username"] == "u1"\n'
        '    assert contacts[0]["unread_count"] == 1\n\n'
        '    client.post("/messages/read", json={"from_user": "u1", "to_user": "u2"})\n'
        '    contacts = client.get("/contacts/u2").json()\n'
        '    assert contacts[0]["unread_count"] == 0\n\n'
        '    msgs = client.get("/messages/u2").json()\n'
        '    assert msgs[0]["read"] is True\n',
        encoding="utf-8",
    )

    # 5. Ensure config test command points to our test file
    config_path = E2E_PROJECT_DIR / ".devflow" / "config.toml"
    config_text = config_path.read_text(encoding="utf-8")
    config_text = config_text.replace(
        'test = "pytest"', 'test = "pytest tests/test_app.py -v"'
    )
    config_path.write_text(config_text, encoding="utf-8")

    # Read run_id from state after init
    state_path = E2E_PROJECT_DIR / ".devflow" / "state.toml"
    if state_path.exists():
        import toml

        state_data = toml.load(state_path)
        return str(state_data.get("workflow_run_id", ""))
    return ""


def _build_prompt(run_id: str) -> str:
    """Build the prompt for the AI agent.

    We intentionally do NOT tell the agent how to use DevFlow.
    The agent must read SKILL.md and follow the instructions on its own.
    """
    return (
        "You are an AI software engineer. Complete the following project "
        "using the DevFlow v2.0 workflow system.\n\n"
        f"WORK DIRECTORY: {E2E_PROJECT_DIR}\n\n"
        "Read SKILL.md in the project root and follow its instructions exactly. "
        "Do NOT write any code or create any files until SKILL.md tells you to.\n\n"
        "PROJECT: ChatIM\n"
        "- Backend: Python FastAPI in `src/main.py`\n"
        "- Frontend: `index.html` with Tailwind CSS via CDN (no build tools)\n"
        "- Storage: in-memory Python dict\n"
        "- Tests: `tests/test_app.py` already exists. You must make them pass.\n\n"
        "ORIGINAL REQUIREMENTS:\n"
        "Build a simple instant messaging system where:\n"
        "- Users can register (unique username) and login.\n"
        "- Users can send messages to each other.\n"
        "- Messages have a read/unread state.\n"
        "- Users see a contact list with last message preview and unread badge.\n"
        "- The frontend provides a near-realtime chat experience.\n"
        "- Visiting the root URL serves the frontend.\n\n"
        "CORE PRINCIPLES (non-negotiable):\n"
        "- CORS enabled (allow_origins=['*'])\n"
        "- Sending to a non-existent user MUST fail (404)\n"
        "- Unread count is precise: only unread messages SENT TO the current user\n"
        "- Conversations are chronologically ordered (oldest first)\n"
        "- Data isolation: user A cannot see messages between B and C\n"
        "- Frontend is a TWO-PANEL layout: contacts sidebar + active conversation view\n"
        "- Selecting a contact clears unread for that specific conversation\n"
        "- Messages refresh automatically (polling)\n"
        "- All styling uses Tailwind CSS utility classes\n\n"
        "STRICT ACCEPTANCE:\n"
        "The file `tests/test_app.py` is the SOLE acceptance criteria. "
        "Read it carefully. Every test must pass. Do NOT modify the tests.\n\n"
        f"Do everything inside {E2E_PROJECT_DIR}.\n"
    )


# --- Running agent ---


def _run_tool(
    config: ToolConfig,
    executable: str,
    invocation: tuple[list[str], dict[str, str]],
    project_dir: Path,
    prompt: str,
) -> subprocess.CompletedProcess[str]:
    """Run an AI CLI with the given prompt."""
    args_prefix, extra_env = invocation
    tool_id = config.tool_id

    env = os.environ.copy()
    env["DEVFLOW_ALLOW_SHELL"] = "1"
    env["PYTHONPATH"] = REPO_SRC_DIR
    env.update(extra_env)

    use_stdin = False

    if tool_id == "kimi" and "--print" in args_prefix:
        cmd = [executable, *args_prefix]
        use_stdin = True
    elif tool_id == "claude" and ("-p" in args_prefix or "--print" in args_prefix):
        cmd = [executable, *args_prefix]
        use_stdin = True
    elif args_prefix == ["-c"]:
        cmd = [executable, "-c", prompt]
    elif args_prefix == ["chat", "-c"]:
        cmd = [executable, "chat", "-c", prompt]
    elif args_prefix == ["run"]:
        cmd = [executable, "run", prompt]
    elif tool_id == "opencode" and "run" in args_prefix:
        cmd = [executable, *args_prefix, prompt]
    else:
        cmd = [executable]
        use_stdin = True

    return subprocess.run(
        cmd,
        input=prompt if use_stdin else None,
        cwd=str(project_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )


# --- Metrics and reporting ---


def _collect_run_metrics(
    start_time: float,
    end_time: float,
    turn_count: int,
    run_id: str,
    state: dict,
    test_result: subprocess.CompletedProcess[str],
    tool_id: str,
) -> dict:
    """Collect metrics from the completed run for the report."""
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "tool_id": tool_id,
        "duration_seconds": round(end_time - start_time, 2),
        "turn_count": turn_count,
        "final_step": state.get("current_step", "unknown"),
        "workflow_run_id": run_id,
        "status": "PASS",
        "tests_passed": test_result.returncode == 0,
        "test_stdout": test_result.stdout if test_result.returncode == 0 else "",
        "test_stderr": test_result.stderr if test_result.returncode != 0 else "",
    }


def _list_artifacts(project_dir: Path) -> list[dict]:
    """List all generated artifacts with sizes."""
    artifacts = []
    for pattern in [
        "docs/**/*.md",
        "src/*.py",
        "index.html",
        "tests/*.py",
        "*_e2e.log",
    ]:
        for fp in project_dir.glob(pattern):
            if fp.is_file():
                rel = fp.relative_to(project_dir).as_posix()
                size = fp.stat().st_size
                artifacts.append(
                    {
                        "path": rel,
                        "size_bytes": size,
                        "size_human": _human_readable_size(size),
                    }
                )
    return sorted(artifacts, key=lambda x: x["path"])


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _load_previous_reports() -> list[dict]:
    """Load all previous report JSON metadata files."""
    reports = []
    if not E2E_REPORTS_DIR.exists():
        return reports
    for json_file in sorted(E2E_REPORTS_DIR.glob("report_*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            reports.append(data)
        except Exception:
            pass
    return reports


def _generate_report(
    metrics: dict, artifacts: list[dict]
) -> Path:
    """Generate a Markdown comparison report and save it.

    Returns the path to the generated report.
    """
    E2E_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    tool_id = metrics["tool_id"]
    timestamp = metrics["timestamp"].replace(":", "-")
    report_path = E2E_REPORTS_DIR / f"report_{tool_id}_{timestamp}.md"
    json_path = E2E_REPORTS_DIR / f"report_{tool_id}_{timestamp}.json"

    json_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    previous_reports = _load_previous_reports()
    prev = previous_reports[-1] if previous_reports else None

    lines = [
        f"# E2E Test Report — {metrics['tool_id']} — {metrics['timestamp']}",
        "",
        "## Run Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Tool | `{metrics['tool_id']}` |",
        f"| Timestamp | {metrics['timestamp']} |",
        f"| Duration | {metrics['duration_seconds']}s |",
        f"| Total Turns | {metrics['turn_count']} |",
        f"| Final Step | `{metrics['final_step']}` |",
        f"| Workflow Run ID | `{metrics['workflow_run_id']}` |",
        f"| Status | {'PASS' if metrics['status'] == 'PASS' else 'FAIL'} |",
        "",
    ]

    if prev:
        lines.extend(
            [
                "## Comparison with Previous Run",
                "",
                "| Metric | This Run | Previous Run | Delta |",
                "|--------|----------|--------------|-------|",
                f"| Timestamp | {metrics['timestamp']} | {prev['timestamp']} | — |",
                f"| Duration | {metrics['duration_seconds']}s | "
                f"{prev['duration_seconds']}s | "
                f"{metrics['duration_seconds'] - prev['duration_seconds']:+.2f}s |",
                f"| Turns | {metrics['turn_count']} | "
                f"{prev['turn_count']} | "
                f"{metrics['turn_count'] - prev['turn_count']:+d} |",
                f"| Final Step | `{metrics['final_step']}` | `{prev['final_step']}` | — |",
                f"| Status | {metrics['status']} | {prev['status']} | — |",
                "",
            ]
        )

    lines.extend(
        [
            "## Generated Artifacts",
            "",
            "| File | Size |",
            "|------|------|",
        ]
    )
    for art in artifacts:
        lines.append(f"| `{art['path']}` | {art['size_human']} |")
    lines.append("")

    lines.extend(
        [
            "## Test Results",
            "",
            "| Suite | Result |",
            "|-------|--------|",
            f"| `tests/test_app.py` | {'PASS' if metrics['tests_passed'] else 'FAIL'} |",
            "",
        ]
    )
    if not metrics["tests_passed"]:
        lines.extend(
            [
                "### Test Failure Details",
                "",
                "```",
                metrics.get("test_stdout", ""),
                metrics.get("test_stderr", ""),
                "```",
                "",
            ]
        )

    if len(previous_reports) >= 1:
        lines.extend(
            [
                "## Run History",
                "",
                "| # | Tool | Timestamp | Duration | Turns | Status |",
                "|---|------|-----------|----------|-------|--------|",
            ]
        )
        for i, r in enumerate(previous_reports + [metrics], start=1):
            lines.append(
                f"| {i} | {r.get('tool_id', '?')} | {r['timestamp']} | "
                f"{r['duration_seconds']}s | {r['turn_count']} | {r['status']} |"
            )
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            f"*Report generated by `test_kimi_usability.py` at {metrics['timestamp']}*",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# --- Pytest fixtures and tests ---


@pytest.fixture(scope="module", params=[
    pytest.param(
        (config, path, invocation),
        id=config.tool_id,
    )
    for config, path, invocation in _AVAILABLE_TOOLS
] if _AVAILABLE_TOOLS else [
    pytest.param(None, id="no-tools")
])
def ai_tool(request: Any) -> tuple[ToolConfig, str, tuple[list[str], dict[str, str]]] | None:
    """Provide each available AI CLI tool as a test parameter."""
    if request.param is None:
        pytest.skip(
            "No supported AI CLI found in PATH. "
            f"Supported tools: {', '.join(t.tool_id for t in SUPPORTED_TOOLS)}"
        )
    return request.param


@pytest.mark.slow
def test_agent_completes_chatim_with_devflow(
    ai_tool: tuple[ToolConfig, str, tuple[list[str], dict[str, str]]],
) -> None:
    """End-to-end test: AI CLI should complete the full DevFlow workflow.

    The project directory is persisted at tests/e2e/taskflow_e2e/ for manual inspection.
    Any previous run is cleaned up before starting.
    A Markdown comparison report is written to tests/e2e/reports/.
    """
    config, executable, invocation = ai_tool
    tool_id = config.tool_id

    run_start = time.time()
    run_id = _setup_project()
    initial_prompt = _build_prompt(run_id or "<run_id>")

    continuation_prompt = (
        "Continue working on the ChatIM project. "
        "Read SKILL.md again if you need guidance. "
        "Do not stop until the workflow is complete."
    )

    log_path = E2E_PROJECT_DIR / f"{tool_id}_e2e.log"
    all_outputs: list[str] = []

    max_turns = 5
    turn_count = 0
    for turn in range(max_turns):
        prompt = initial_prompt if turn == 0 else continuation_prompt
        result = _run_tool(config, executable, invocation, E2E_PROJECT_DIR, prompt)
        turn_count += 1

        turn_header = f"\n=== {tool_id.upper()} TURN {turn + 1} ===\n"
        turn_output = turn_header + result.stdout + "\n=== STDERR ===\n" + result.stderr
        all_outputs.append(turn_output)
        log_path.write_text("\n".join(all_outputs), encoding="utf-8")

        print(turn_output)
        print(f"\n=== {tool_id.upper()} TURN {turn + 1} RETURN CODE: {result.returncode} ===\n")

        state_path = E2E_PROJECT_DIR / ".devflow" / "state.toml"
        if not state_path.exists():
            if turn == max_turns - 1:
                pytest.fail(f"DevFlow state file was never created after {max_turns} turns")
            continue

        import toml

        state = toml.load(state_path)
        current_step = state.get("current_step")

        if current_step == "finish":
            result = _run_tool(config, executable, invocation, E2E_PROJECT_DIR, continuation_prompt)
            turn_count += 1
            turn_header = f"\n=== {tool_id.upper()} FINAL TURN ===\n"
            turn_output = turn_header + result.stdout + "\n=== STDERR ===\n" + result.stderr
            all_outputs.append(turn_output)
            log_path.write_text("\n".join(all_outputs), encoding="utf-8")
            print(turn_output)
            break
    else:
        pytest.fail(f"Workflow did not reach 'finish' after {max_turns} turns")

    # Final assertions
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

    req_content = (
        E2E_PROJECT_DIR / "docs" / "requirements" / f"REQ-{run_id_actual}.md"
    ).read_text()
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
        f"Tests failed after {tool_id} session:\n{test_result.stdout}\n{test_result.stderr}"
    )

    combined_output = "\n".join(all_outputs).lower()
    assert "workflow complete" in combined_output, (
        f"{tool_id} output does not mention 'Workflow complete!' — it may have stopped early"
    )

    # Generate report
    run_end = time.time()
    artifacts = _list_artifacts(E2E_PROJECT_DIR)
    metrics = _collect_run_metrics(
        run_start, run_end, turn_count, run_id_actual, state, test_result, tool_id
    )
    report_path = _generate_report(metrics, artifacts)
    print(f"\n=== E2E REPORT generated: {report_path} ===\n")
