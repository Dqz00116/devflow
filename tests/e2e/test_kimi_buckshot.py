"""E2E test: Buckshot Roulette — use real local Kimi CLI to drive DevFlow v2.0 end-to-end.

This test:
1. Detects a locally installed Kimi CLI (kimi / kimi-cli / kimi-code)
2. Sets up a persistent Buckshot Roulette project under tests/e2e/buckshot_e2e/
3. Cleans up any previous test artifacts before starting
4. Sends a comprehensive prompt to Kimi asking it to follow DevFlow
5. Waits for completion (up to 10 minutes)
6. Asserts that all expected files exist, tests pass, and workflow is complete
7. Generates a Markdown comparison report at tests/e2e/reports/

Requirements:
- Kimi CLI must be installed and available in PATH
- The CLI should support non-interactive execution via stdin pipe
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

KIMI_CANDIDATES = ["kimi", "kimi-cli", "kimi-code"]
REPO_SRC_DIR = str(Path(__file__).resolve().parents[2] / "src")

# Persistent project directory for inspection after test runs
E2E_PROJECT_DIR = Path(__file__).resolve().parent / "buckshot_e2e"
E2E_REPORTS_DIR = Path(__file__).resolve().parent / "reports"


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


def _discover_kimi_invocation(  # noqa: C901
    executable: str,
) -> tuple[list[str], dict[str, str]] | None:
    """Discover how to invoke Kimi in non-interactive mode.

    Kimi CLI supports `--print` (non-interactive) with `--input-format text` via stdin.
    Returns (args_list, extra_env) or None if we cannot determine a working mode.
    """
    # Strategy 1: Kimi Code CLI print mode (preferred)
    try:
        result = subprocess.run(
            [
                executable,
                "--print",
                "--yolo",
                "--input-format",
                "text",
                "--max-steps-per-turn",
                "100",
            ],
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
            return (
                [
                    "--print",
                    "--yolo",
                    "--input-format",
                    "text",
                    "--max-steps-per-turn",
                    "100",
                ],
                {},
            )
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
        if (
            "unknown" not in result.stderr.lower()
            and "unrecognized" not in result.stderr.lower()
        ):
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
        if (
            "unknown" not in result.stderr.lower()
            and "unrecognized" not in result.stderr.lower()
        ):
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
            "Please install it (e.g. from https://www.moonshot.cn/ "
            "or via your package manager) "
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
            f"Kimi CLI found at '{path}' but its non-interactive invocation mode "
            "could not be determined. "
            "Supported modes: -c <prompt>, chat -c <prompt>, "
            "run <prompt>, or stdin pipe. "
            "Try running it manually to find the right flag."
        )

    # Store invocation metadata for tests
    kimi_executable._invocation = invocation  # type: ignore[attr-defined]
    return path


def _run_kimi(
    executable: str, project_dir: Path, prompt: str
) -> subprocess.CompletedProcess[str]:
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
        timeout=1800,  # 30 minutes — Buckshot Roulette is complex
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
        [
            sys.executable,
            "-m",
            "devflow",
            "init",
            "--language",
            "python",
            "--name",
            "BuckshotRoulette",
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

    # 4. Create preset test file (trap test included)
    tests_dir = E2E_PROJECT_DIR / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_app.py").write_text(
        "import pytest\n"
        "from fastapi.testclient import TestClient\n"
        "from src.main import app\n\n"
        "client = TestClient(app)\n\n"
        "def _start(**kwargs):\n"
        '    r = client.post("/game/start", json=kwargs)\n'
        "    assert r.status_code == 200\n"
        "    return r.json()\n\n"
        'def test_start_game_default():\n'
        '    state = _start()\n'
        '    assert state["round"] == 1\n'
        '    assert state["player_charges"] == 2\n'
        '    assert state["dealer_charges"] == 2\n'
        '    assert len(state["chamber"]) == 3\n'
        '    assert any(state["chamber"])\n'
        '    assert not all(state["chamber"])\n'
        '    assert state["current_turn"] == "player"\n'
        '    assert state["game_over"] is False\n\n'
        'def test_start_game_forced_chamber():\n'
        '    state = _start(forced_chamber=[True, False, True])\n'
        '    assert state["chamber"] == [True, False, True]\n\n'
        'def test_shoot_self_live_loses_charge():\n'
        '    _start(forced_chamber=[True], player_charges=1, dealer_charges=1)\n'
        '    r = client.post("/game/action", json={"action": "shoot_self"})\n'
        "    assert r.status_code == 200\n"
        '    state = r.json()\n'
        '    assert state["player_charges"] == 0\n'
        '    assert state["game_over"] is True\n'
        '    assert state["winner"] == "dealer"\n\n'
        'def test_shoot_self_blank_no_charge_loss():\n'
        '    _start(forced_chamber=[False, True], player_charges=2, dealer_charges=2)\n'
        '    r = client.post("/game/action", json={"action": "shoot_self"})\n'
        "    assert r.status_code == 200\n"
        '    state = r.json()\n'
        '    assert state["player_charges"] == 2\n'
        '    assert state["current_turn"] == "dealer"\n\n'
        'def test_shoot_opponent_live_dealer_loses_charge():\n'
        '    _start(forced_chamber=[True], player_charges=1, dealer_charges=1)\n'
        '    r = client.post("/game/action", json={"action": "shoot_opponent"})\n'
        "    assert r.status_code == 200\n"
        '    state = r.json()\n'
        '    assert state["dealer_charges"] == 0\n'
        '    assert state["game_over"] is True\n'
        '    assert state["winner"] == "player"\n\n'
        'def test_shoot_opponent_blank_turn_switches():\n'
        '    _start(forced_chamber=[False, True], player_charges=2, dealer_charges=2)\n'
        '    r = client.post("/game/action", json={"action": "shoot_opponent"})\n'
        "    assert r.status_code == 200\n"
        '    state = r.json()\n'
        '    assert state["dealer_charges"] == 2\n'
        '    assert state["current_turn"] == "dealer"\n\n'
        'def test_use_magnifier_reveals_shell():\n'
        '    _start(forced_chamber=[True, False], player_charges=2, dealer_charges=2)\n'
        '    r = client.post("/game/action", json={"action": "use_magnifier"})\n'
        "    assert r.status_code == 200\n"
        '    state = r.json()\n'
        '    assert state["last_magnifier_result"] == "live"\n'
        '    assert "magnifier" not in state["player_items"]\n\n'
        'def test_use_handcuffs_skips_dealer_turn():\n'
        '    _start(forced_chamber=[False, True], player_charges=2, dealer_charges=2,\n'
        '           player_items=["handcuffs"], dealer_items=[])\n'
        '    r = client.post("/game/action", json={"action": "use_handcuffs"})\n'
        "    assert r.status_code == 200\n"
        '    state = r.json()\n'
        '    assert state["dealer_skipped"] is True\n'
        '    assert "handcuffs" not in state["player_items"]\n'
        '    # shoot opponent (blank) — turn would normally go to dealer, but handcuffs skip\n'
        '    r2 = client.post("/game/action", json={"action": "shoot_opponent"})\n'
        "    assert r2.status_code == 200\n"
        '    state2 = r2.json()\n'
        '    assert state2["current_turn"] == "player"\n'
        '    assert state2["dealer_skipped"] is False\n\n'
        'def test_ai_turn_makes_valid_action():\n'
        '    _start(forced_chamber=[False, True], player_charges=2, dealer_charges=2,\n'
        '           player_items=[], dealer_items=[])\n'
        '    client.post("/game/action", json={"action": "shoot_self"})\n'
        '    r = client.post("/game/ai-turn")\n'
        "    assert r.status_code == 200\n"
        '    state = r.json()\n'
        '    assert len(state["action_log"]) >= 1\n'
        '    assert any("dealer:" in entry for entry in state["action_log"])\n\n'
        'def test_game_over_player_wins():\n'
        '    _start(forced_chamber=[True], player_charges=2, dealer_charges=1)\n'
        '    r = client.post("/game/action", json={"action": "shoot_opponent"})\n'
        "    assert r.status_code == 200\n"
        '    state = r.json()\n'
        '    assert state["game_over"] is True\n'
        '    assert state["winner"] == "player"\n'
        '    # actions after game over should fail\n'
        '    r2 = client.post("/game/action", json={"action": "shoot_self"})\n'
        "    assert r2.status_code == 400\n\n"
        'def test_game_over_dealer_wins():\n'
        '    _start(forced_chamber=[True], player_charges=1, dealer_charges=2)\n'
        '    r = client.post("/game/action", json={"action": "shoot_self"})\n'
        "    assert r.status_code == 200\n"
        '    state = r.json()\n'
        '    assert state["game_over"] is True\n'
        '    assert state["winner"] == "dealer"\n\n'
        'def test_invalid_action_returns_400():\n'
        '    _start()\n'
        '    r = client.post("/game/action", json={"action": "dance"})\n'
        "    assert r.status_code == 400\n\n"
        'def test_chamber_reload_when_empty():\n'
        '    _start(forced_chamber=[True], player_charges=2, dealer_charges=2)\n'
        '    client.post("/game/action", json={"action": "shoot_opponent"})\n'
        '    state = client.get("/game/state").json()\n'
        '    assert len(state["chamber"]) == 3\n'
        '    assert state["current_shell_index"] == 0\n'
        '    assert state["round"] == 2\n',
        encoding="utf-8",
    )

    # 5. Ensure config test command points to our test file
    config_path = E2E_PROJECT_DIR / ".devflow" / "config.toml"
    config_text = config_path.read_text(encoding="utf-8")
    config_text = config_text.replace(
        'test = "pytest"', 'test = "pytest tests/test_app.py -v"'
    )
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
    return (
        "You are an AI software engineer. Complete a full-stack project "
        "by strictly following the DevFlow v2.0 CLI workflow.\n\n"
        f"WORK DIRECTORY: {E2E_PROJECT_DIR}\n\n"
        "CRITICAL RULES:\n"
        "1. ALWAYS run `devflow current` first to know what to do\n"
        "2. ONLY do what the current step says\n"
        "3. After finishing the step, run `devflow done`\n"
        "4. If `devflow done` fails, read the error, fix it, "
        "and run `devflow done` again\n"
        "5. If a step requires `user_approved`, "
        "run `devflow approve <ITEM>` yourself and continue\n"
        "6. NEVER skip steps and NEVER create files "
        "for future steps ahead of time\n"
        '7. Do not stop until you see "Workflow complete!"\n\n'
        "PROJECT: Buckshot Roulette\n"
        "- Backend: Python FastAPI in `src/main.py`\n"
        "- Frontend: `index.html` with Three.js (OrthographicCamera, 2D flat style)\n"
        "- No build tools: Three.js from CDN, plain HTML/JS/CSS\n"
        "- Tests: `tests/test_app.py` already exists. You must make them pass.\n\n"
        "ORIGINAL REQUIREMENTS:\n"
        "Build a 2D 'Buckshot Roulette' turn-based game:\n"
        "- Two characters: Player (human) and Dealer (AI).\n"
        "- Each starts with 2 charges (lives).\n"
        "- A shotgun chamber holds 3 shells per round (2 live, 1 blank in random order).\n"
        "- Players take turns deciding: shoot themselves, shoot the opponent, or use an item.\n"
        "- Live shell = target loses 1 charge. Blank shell = no damage. Turn always passes after any shot.\n"
        "- When chamber empties, a new round starts with a fresh chamber (round counter increments).\n"
        "- Game ends when either side reaches 0 charges.\n"
        "- Items (simplified): Magnifier (reveals current shell), Handcuffs (opponent skips next turn).\n"
        "- Dealer AI: uses Magnifier if available and shell unknown; if shell known live -> shoot opponent; if known blank -> shoot self; otherwise random-ish.\n"
        "- Frontend: Three.js orthographic camera, 2D flat UI showing both characters, chamber shells, charges (hearts/lives), action buttons, round info, action log, and particle effects (muzzle flash, blood splatter) on shots.\n"
        "- Visiting root URL serves the frontend.\n\n"
        "CORE PRINCIPLES (non-negotiable):\n"
        "- CORS enabled (allow_origins=['*']).\n"
        "- Game state is server-side; frontend polls GET /game/state and renders it.\n"
        "- POST /game/start accepts optional `forced_chamber` (list of bools) for deterministic testing.\n"
        "- POST /game/action accepts {action: 'shoot_self'|'shoot_opponent'|'use_magnifier'|'use_handcuffs'}.\n"
        "- POST /game/ai-turn triggers the dealer's turn and returns the updated state.\n"
        "- State includes: round, player_charges, dealer_charges, chamber (list of bools), current_shell_index, current_turn, player_items, dealer_items, game_over, winner, action_log, last_magnifier_result, dealer_skipped.\n"
        "- Actions after game_over must return 400.\n"
        "- Invalid action strings return 400.\n"
        "- Three.js scene uses OrthographicCamera for a flat 2D board-game look.\n"
        "- Shells are rendered as visible objects (e.g., rectangles/cylinders); live vs blank can be distinguished visually once revealed via Magnifier.\n"
        "- Rich animations: idle breathing/floating for characters; recoil kick on every shot; screen-shake on live hits; shell ejection/fly-out when fired; chamber reload slide-in animation.\n"
        "- Effect animations: red flash overlay on character damage; handcuffs lock-chain visual when used; magnifier lens-beam sweep over current shell; turn-indicator pulse on switch.\n"
        "- Game-over animation: winner text scales in with a burst of particles, loser dims out.\n"
        "- All animations are tweened (lerp/sine) in the render loop — no CSS animations on Three.js objects.\n\n"
        "STRICT ACCEPTANCE:\n"
        "The file `tests/test_app.py` is the SOLE acceptance criteria. "
        "Read it carefully to infer the exact expected API shapes and behavior. "
        "Every test must pass. Do NOT modify the tests.\n\n"
        "WORKFLOW HINT (E2E-MODE-A gates):\n"
        f"- req-create: needs `docs/requirements/REQ-{run_id}.md`\n"
        "- req-approve: needs REQ file containing `status: approved` + "
        f"`docs/features/FEAT-{run_id}.md`\n"
        f"- brainstorm: needs `docs/superpowers/specs/DESIGN-{run_id}.md`\n"
        f"- write-plan: needs `docs/superpowers/plans/PLAN-{run_id}.md`\n"
        "- implement-sdd: `pytest tests/test_app.py -v` must pass\n"
        f"- code-review: run `devflow approve CODE-REVIEW-{run_id}` then done\n"
        "- test-run: tests must pass\n"
        f"- verify: needs `docs/evidence/EVIDENCE-{run_id}.md`\n"
        "- finish: needs `docs/completion/COMPLETION-{run_id}.md` + "
        "REQ file containing `status: done`\n\n"
        "STEP-BY-STEP GUIDE:\n"
        "1. Run `devflow select-workflow E2E-MODE-A`\n"
        "2. Loop:\n"
        "   a. `devflow current`\n"
        "   b. Do the step\n"
        "   c. `devflow done`\n"
        "   d. Fix any gate failures and repeat c\n"
        "3. When you reach `implement-sdd`, write the FastAPI game backend "
        "and Three.js frontend, then run tests until they pass.\n"
        f"4. For `code-review`, self-approve with "
        f"`devflow approve CODE-REVIEW-{run_id}`.\n"
        "5. For `finish`, update the REQ file to include "
        "`status: done` and create the COMPLETION file.\n\n"
        "IMPORTANT: Start by running `devflow select-workflow E2E-MODE-A` "
        "and then `devflow current`.\n"
        f"Do everything inside {E2E_PROJECT_DIR}.\n"
    )


def _collect_run_metrics(
    start_time: float,
    end_time: float,
    turn_count: int,
    run_id: str,
    state: dict,
    test_result: subprocess.CompletedProcess[str],
) -> dict:
    """Collect metrics from the completed run for the report."""
    metrics = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": round(end_time - start_time, 2),
        "turn_count": turn_count,
        "final_step": state.get("current_step", "unknown"),
        "workflow_run_id": run_id,
        "status": "PASS",
        "tests_passed": test_result.returncode == 0,
        "test_stdout": test_result.stdout if test_result.returncode == 0 else "",
        "test_stderr": test_result.stderr if test_result.returncode != 0 else "",
    }
    return metrics


def _list_artifacts(project_dir: Path) -> list[dict]:
    """List all generated artifacts with sizes."""
    artifacts = []
    for pattern in [
        "docs/**/*.md",
        "src/*.py",
        "index.html",
        "tests/*.py",
        "kimi_e2e.log",
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


def _generate_report(metrics: dict, artifacts: list[dict]) -> Path:
    """Generate a Markdown comparison report and save it.

    Returns the path to the generated report.
    """
    E2E_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = metrics["timestamp"].replace(":", "-")
    report_path = E2E_REPORTS_DIR / f"report_{timestamp}.md"
    json_path = E2E_REPORTS_DIR / f"report_{timestamp}.json"

    # Save raw metrics for future comparisons
    json_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    previous_reports = _load_previous_reports()
    prev = previous_reports[-1] if previous_reports else None

    lines = [
        f"# E2E Test Report — {metrics['timestamp']}",
        "",
        "## Run Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Timestamp | {metrics['timestamp']} |",
        f"| Duration | {metrics['duration_seconds']}s |",
        f"| Total Turns | {metrics['turn_count']} |",
        f"| Final Step | `{metrics['final_step']}` |",
        f"| Workflow Run ID | `{metrics['workflow_run_id']}` |",
        f"| Status | {'PASS' if metrics['status'] == 'PASS' else 'FAIL'} |",
        "",
    ]

    # Comparison table
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

    # Artifacts table
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

    # Test results
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

    # History
    if len(previous_reports) >= 1:
        lines.extend(
            [
                "## Run History",
                "",
                "| # | Timestamp | Duration | Turns | Status |",
                "|---|-----------|----------|-------|--------|",
            ]
        )
        for i, r in enumerate(previous_reports + [metrics], start=1):
            lines.append(
                f"| {i} | {r['timestamp']} | {r['duration_seconds']}s | "
                f"{r['turn_count']} | {r['status']} |"
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


@pytest.mark.slow
def test_kimi_completes_buckshot_with_devflow(kimi_executable: str) -> None:
    """End-to-end test: Kimi CLI should complete the full DevFlow workflow.

    The project directory is persisted at tests/e2e/buckshot_e2e/ for manual inspection.
    Any previous run is cleaned up before starting.
    A Markdown comparison report is written to tests/e2e/reports/.
    """
    run_start = time.time()
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
    turn_count = 0
    for turn in range(max_turns):
        prompt = initial_prompt if turn == 0 else continuation_prompt
        result = _run_kimi(kimi_executable, E2E_PROJECT_DIR, prompt)
        turn_count += 1

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
            # One extra turn to run `devflow done` on finish
            result = _run_kimi(kimi_executable, E2E_PROJECT_DIR, continuation_prompt)
            turn_count += 1
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
        f"Tests failed after Kimi session:\n{test_result.stdout}\n{test_result.stderr}"
    )

    combined_output = "\n".join(all_outputs).lower()
    assert "workflow complete" in combined_output, (
        "Kimi output does not mention 'Workflow complete!' — it may have stopped early"
    )

    # Generate comparison report
    run_end = time.time()
    artifacts = _list_artifacts(E2E_PROJECT_DIR)
    metrics = _collect_run_metrics(
        run_start, run_end, turn_count, run_id_actual, state, test_result
    )
    report_path = _generate_report(metrics, artifacts)
    print(f"\n=== E2E REPORT generated: {report_path} ===\n")
