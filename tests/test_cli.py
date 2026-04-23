"""Tests for CLI integration — subprocess tests for devflow commands."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import toml


@pytest.fixture
def project_root() -> Path:
    """Create a temp project root with workflows and config."""
    tmpdir = tempfile.mkdtemp()
    root = Path(tmpdir)

    (root / ".devflow" / "workflows").mkdir(parents=True)
    (root / ".devflow" / "prompts").mkdir(parents=True)
    for d in [
        "debug", "features", "requirements", "evidence", "completion",
        "superpowers/specs", "superpowers/plans",
    ]:
        (root / "docs" / d).mkdir(parents=True)

    src_data = Path("src/devflow/data/workflows")
    shutil.copy2(src_data / "MODE-A.toml", root / ".devflow" / "workflows" / "MODE-A.toml")
    shutil.copy2(src_data / "MODE-B.toml", root / ".devflow" / "workflows" / "MODE-B.toml")

    (root / ".devflow" / "config.toml").write_text(
        '[project]\nname = "test"\nlanguage = "python"\n'
        '[commands]\ntest = "echo ok"\ntest_unit = "echo ok"\ntest_integration = "echo ok"\n'
    )

    yield root
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def project_root_failing() -> Path:
    """Project root with test command that always fails."""
    tmpdir = tempfile.mkdtemp()
    root = Path(tmpdir)

    (root / ".devflow" / "workflows").mkdir(parents=True)
    (root / ".devflow" / "prompts").mkdir(parents=True)
    for d in [
        "debug", "features", "requirements", "evidence", "completion",
        "superpowers/specs", "superpowers/plans",
    ]:
        (root / "docs" / d).mkdir(parents=True)

    src_data = Path("src/devflow/data/workflows")
    shutil.copy2(src_data / "MODE-A.toml", root / ".devflow" / "workflows" / "MODE-A.toml")
    shutil.copy2(src_data / "MODE-B.toml", root / ".devflow" / "workflows" / "MODE-B.toml")

    (root / ".devflow" / "config.toml").write_text(
        '[project]\nname = "test"\nlanguage = "python"\n'
        '[commands]\ntest = "exit 1"\n'
    )

    yield root
    shutil.rmtree(tmpdir, ignore_errors=True)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run devflow command in given directory using the same Python interpreter."""
    env = {"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    return subprocess.run(
        [sys.executable, "-m", "devflow"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
    )


def _get_run_id(root: Path) -> str:
    """Read workflow_run_id from state."""
    state_path = root / ".devflow" / "state.toml"
    data = toml.load(state_path)
    return data.get("workflow_run_id", "")


class TestCLISelectWorkflow:
    """Test devflow select-workflow."""

    def test_select_mode_a(self, project_root: Path) -> None:
        r = _run(["select-workflow", "MODE-A"], project_root)
        assert r.returncode == 0
        assert "MODE-A" in r.stdout

    def test_select_mode_b(self, project_root: Path) -> None:
        r = _run(["select-workflow", "MODE-B"], project_root)
        assert r.returncode == 0
        assert "MODE-B" in r.stdout

    def test_select_nonexistent(self, project_root: Path) -> None:
        r = _run(["select-workflow", "NONEXISTENT"], project_root)
        assert r.returncode == 0  # CLI doesn't exit with error
        assert "not found" in r.stdout.lower() or "Error" in r.stdout


class TestCLICurrent:
    """Test devflow current."""

    def test_current_shows_first_step(self, project_root: Path) -> None:
        _run(["select-workflow", "MODE-B"], project_root)
        r = _run(["current"], project_root)
        assert r.returncode == 0
        assert "debug-root-cause" in r.stdout

    def test_current_shows_fail_routes(self, project_root: Path) -> None:
        _run(["select-workflow", "MODE-B"], project_root)
        run_id = _get_run_id(project_root)

        # Navigate to debug-fix
        (project_root / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        _run(["done"], project_root)  # -> pattern
        (project_root / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        _run(["done"], project_root)  # -> hypothesis
        (project_root / "docs" / "debug" / f"HYPOTHESIS-{run_id}.md").write_text("H")
        _run(["done"], project_root)  # -> debug-fix

        r = _run(["current"], project_root)
        assert "On Failure:" in r.stdout
        assert "debug-root-cause" in r.stdout


class TestCLIDone:
    """Test devflow done."""

    def test_done_gate_fail(self, project_root: Path) -> None:
        _run(["select-workflow", "MODE-B"], project_root)
        r = _run(["done"], project_root)
        assert r.returncode == 0
        # Should show failure info
        assert "not complete" in r.stdout.lower() or "not found" in r.stdout.lower()

    def test_done_gate_pass(self, project_root: Path) -> None:
        _run(["select-workflow", "MODE-B"], project_root)
        run_id = _get_run_id(project_root)
        (project_root / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")

        r = _run(["done"], project_root)
        assert r.returncode == 0
        assert "satisfied" in r.stdout.lower() or "advanced" in r.stdout.lower()

    def test_done_fail_route_routing(self, project_root_failing: Path) -> None:
        """CLI done triggers fail_route auto-routing."""
        _run(["select-workflow", "MODE-B"], project_root_failing)
        run_id = _get_run_id(project_root_failing)

        # Navigate to debug-fix
        (project_root_failing / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        _run(["done"], project_root_failing)
        (project_root_failing / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        _run(["done"], project_root_failing)
        (project_root_failing / "docs" / "debug" / f"HYPOTHESIS-{run_id}.md").write_text("H")
        _run(["done"], project_root_failing)

        # debug-fix gate fails -> fail_route to debug-root-cause
        r = _run(["done"], project_root_failing)
        assert "Routing to" in r.stdout or "Routed" in r.stdout

        # Verify current step changed
        r2 = _run(["current"], project_root_failing)
        assert "debug-root-cause" in r2.stdout


class TestCLIWorkflowStatus:
    """Test devflow workflow-status."""

    def test_shows_workflow_id(self, project_root: Path) -> None:
        _run(["select-workflow", "MODE-B"], project_root)
        r = _run(["workflow-status"], project_root)
        assert "MODE-B" in r.stdout

    def test_shows_has_fail_routes(self, project_root: Path) -> None:
        _run(["select-workflow", "MODE-B"], project_root)
        r = _run(["workflow-status"], project_root)
        assert "[has fail routes]" in r.stdout


class TestCLIApprove:
    """Test devflow approve."""

    def test_approve_item(self, project_root: Path) -> None:
        r = _run(["approve", "TEST-ITEM"], project_root)
        assert r.returncode == 0
        assert "Approved" in r.stdout

    def test_approve_idempotent(self, project_root: Path) -> None:
        _run(["approve", "ITEM-1"], project_root)
        r = _run(["approve", "ITEM-1"], project_root)
        assert "Approved" in r.stdout


class TestCLISet:
    """Test devflow set."""

    def test_set_variable(self, project_root: Path) -> None:
        r = _run(["set", "my_key", "my_value"], project_root)
        assert r.returncode == 0
        assert "Set: my_key=my_value" in r.stdout


class TestCLIBack:
    """Test devflow back."""

    def test_back_after_advance(self, project_root: Path) -> None:
        _run(["select-workflow", "MODE-B"], project_root)
        run_id = _get_run_id(project_root)
        (project_root / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        _run(["done"], project_root)  # advance to pattern

        r = _run(["back"], project_root)
        assert r.returncode == 0
        assert "Returned to" in r.stdout


class TestCLIListWorkflows:
    """Test devflow list-workflows."""

    def test_lists_available_workflows(self, project_root: Path) -> None:
        r = _run(["list-workflows"], project_root)
        assert r.returncode == 0
        assert "MODE-A" in r.stdout
        assert "MODE-B" in r.stdout
