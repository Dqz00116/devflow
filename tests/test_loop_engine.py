"""Tests for loop_engine module — autonomous loop execution."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from devflow.loop_engine import LoopEngine

os.environ["DEVFLOW_ALLOW_SHELL"] = "1"


@pytest.fixture
def project_root() -> Path:
    """Create a temp project root with a simple 2-step workflow."""
    tmpdir = tempfile.mkdtemp()
    root = Path(tmpdir)

    (root / ".devflow" / "workflows").mkdir(parents=True)
    (root / ".devflow" / "prompts").mkdir(parents=True)
    (root / "docs").mkdir()

    (root / ".devflow" / "workflows" / "TEST.toml").write_text(
        '[workflow]\nid = "TEST"\n\n'
        '[[steps]]\nid = "step-1"\nname = "Step One"\n'
        'prompt = "Create file1"\n'
        'gates = ["file_exists:docs/file1.txt"]\nnext = "step-2"\n\n'
        '[[steps]]\nid = "step-2"\nname = "Step Two"\n'
        'prompt = "Create file2"\n'
        'gates = ["file_exists:docs/file2.txt"]\nnext = ""\n'
    )

    (root / ".devflow" / "config.toml").write_text(
        '[project]\nname = "test"\nlanguage = "python"\n'
    )

    yield root
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestLoopEngine:
    def test_auto_generates_backlog(self, project_root: Path) -> None:
        loop = LoopEngine(project_root, tool="local")
        assert loop.backlog.tasks == []
        success = loop._ensure_backlog()
        assert success is True
        assert len(loop.backlog.tasks) == 2
        assert loop.backlog.tasks[0].id == "step-1"

    def test_run_completes_all_steps(self, project_root: Path, monkeypatch) -> None:
        # Pre-create files so gates pass immediately
        (project_root / "docs" / "file1.txt").write_text("ok")
        (project_root / "docs" / "file2.txt").write_text("ok")

        loop = LoopEngine(project_root, tool="local")
        loop._ensure_backlog()

        # Mock _spawn_agent to avoid real subprocess
        monkeypatch.setattr(loop, "_spawn_agent", lambda prompt: (True, ""))

        result = loop.run(max_iterations=10)
        assert result.status == "complete"
        assert loop.backlog.next_pending() is None

    def test_checkpoint_created(self, project_root: Path, monkeypatch) -> None:
        (project_root / "docs" / "file1.txt").write_text("ok")
        (project_root / "docs" / "file2.txt").write_text("ok")

        loop = LoopEngine(project_root, tool="local")
        loop._ensure_backlog()
        monkeypatch.setattr(loop, "_spawn_agent", lambda prompt: (True, ""))

        loop.run(max_iterations=10)

        # NoVCS driver should create a snapshot directory
        checkpoints_dir = project_root / ".devflow" / "checkpoints"
        assert checkpoints_dir.exists()
        assert any(checkpoints_dir.iterdir())

    def test_progress_logged(self, project_root: Path, monkeypatch) -> None:
        (project_root / "docs" / "file1.txt").write_text("ok")

        loop = LoopEngine(project_root, tool="local")
        loop._ensure_backlog()
        monkeypatch.setattr(loop, "_spawn_agent", lambda prompt: (True, ""))

        result = loop.run(max_iterations=10)
        # step-1 passes, step-2 blocked
        assert result.status == "blocked"
        assert result.step == "step-2"

        progress_path = project_root / ".devflow" / "progress.md"
        assert progress_path.exists()
        content = progress_path.read_text(encoding="utf-8")
        assert "Completed step-1" in content

    def test_blocked_when_gate_fails(self, project_root: Path, monkeypatch) -> None:
        loop = LoopEngine(project_root, tool="local")
        loop._ensure_backlog()
        monkeypatch.setattr(loop, "_spawn_agent", lambda prompt: (True, ""))

        result = loop.run(max_iterations=10)
        assert result.status == "blocked"
        assert result.step == "step-1"

    def test_status_output(self, project_root: Path) -> None:
        loop = LoopEngine(project_root, tool="local")
        loop._ensure_backlog()
        status = loop.status()
        assert "Total tasks: 2" in status
        assert "Pending: 2" in status

    def test_reset_clears_progress(self, project_root: Path) -> None:
        loop = LoopEngine(project_root, tool="local")
        loop._ensure_backlog()
        loop.backlog.mark_done("step-1", checkpoint_id="abc")
        loop.reset()

        assert loop.backlog.tasks[0].passes is False
        assert loop.backlog.tasks[0].checkpoint_id is None
