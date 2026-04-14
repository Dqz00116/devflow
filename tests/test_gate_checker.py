"""Tests for gate_checker module — gate evaluation and variable resolution."""

import tempfile
from pathlib import Path

import pytest

from devflow.gate_checker import (
    check_all_gates,
    check_command_success,
    check_file_contains,
    check_file_exists,
    check_gate,
    check_state_set,
    check_user_approved,
    resolve_variables,
)
from devflow.state_store import StateStore


@pytest.fixture
def project_root() -> Path:
    """Create a temp project root with some files."""
    tmpdir = tempfile.mkdtemp()
    root = Path(tmpdir)
    (root / "docs").mkdir()
    (root / "docs" / "test.md").write_text("status: approved\ncontent here")
    (root / "docs" / "other.md").write_text("status: draft")
    yield root
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def state() -> StateStore:
    """Create a StateStore for variable resolution."""
    tmpdir = tempfile.mkdtemp()
    s = StateStore(Path(tmpdir) / "state.toml")
    s.set("test_command", "echo ok")
    s.set("workflow_run_id", "abc12345")
    yield s
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestResolveVariables:
    """Test variable resolution in text."""

    def test_resolve_known_variable(self, state: StateStore) -> None:
        result = resolve_variables("run {test_command}", state)
        assert result == "run echo ok"

    def test_resolve_workflow_run_id(self, state: StateStore) -> None:
        result = resolve_variables("REQ-{workflow_run_id}.md", state)
        assert result == "REQ-abc12345.md"

    def test_unresolved_variable_kept(self, state: StateStore) -> None:
        result = resolve_variables("{unknown_var}", state)
        assert result == "{unknown_var}"

    def test_no_variables(self, state: StateStore) -> None:
        result = resolve_variables("plain text", state)
        assert result == "plain text"

    def test_multiple_variables(self, state: StateStore) -> None:
        state.set("cmd1", "echo")
        state.set("cmd2", "hello")
        result = resolve_variables("{cmd1} {cmd2}", state)
        assert result == "echo hello"


class TestCheckFileExists:
    """Test file_exists gate."""

    def test_file_exists(self, project_root: Path, state: StateStore) -> None:
        passed, msg = check_file_exists("docs/test.md", project_root, state)
        assert passed

    def test_file_not_exists(self, project_root: Path, state: StateStore) -> None:
        passed, msg = check_file_exists("docs/missing.md", project_root, state)
        assert not passed

    def test_file_exists_with_variable(self, project_root: Path, state: StateStore) -> None:
        (project_root / "docs" / "REQ-abc12345.md").write_text("content")
        passed, msg = check_file_exists(
            "docs/REQ-{workflow_run_id}.md", project_root, state
        )
        assert passed


class TestCheckFileContains:
    """Test file_contains gate."""

    def test_contains_text(self, project_root: Path, state: StateStore) -> None:
        passed, msg = check_file_contains("docs/test.md", "status: approved", project_root, state)
        assert passed

    def test_not_contains_text(self, project_root: Path, state: StateStore) -> None:
        passed, msg = check_file_contains("docs/test.md", "nonexistent", project_root, state)
        assert not passed

    def test_file_not_found(self, project_root: Path, state: StateStore) -> None:
        passed, msg = check_file_contains("docs/missing.md", "anything", project_root, state)
        assert not passed

    def test_contains_with_variable(self, project_root: Path, state: StateStore) -> None:
        (project_root / "docs" / "REQ-abc12345.md").write_text("status: approved")
        passed, msg = check_file_contains(
            "docs/REQ-{workflow_run_id}.md", "status: approved", project_root, state
        )
        assert passed


class TestCheckCommandSuccess:
    """Test command_success gate."""

    def test_successful_command(self, monkeypatch) -> None:
        monkeypatch.setenv("DEVFLOW_ALLOW_SHELL", "1")
        passed, msg = check_command_success("echo ok", Path.cwd())
        assert passed

    def test_failing_command(self, monkeypatch) -> None:
        monkeypatch.setenv("DEVFLOW_ALLOW_SHELL", "1")
        passed, msg = check_command_success("exit 1", Path.cwd())
        assert not passed

    def test_command_disabled_without_env_var(self, monkeypatch) -> None:
        monkeypatch.delenv("DEVFLOW_ALLOW_SHELL", raising=False)
        passed, msg = check_command_success("echo ok", Path.cwd())
        assert not passed
        assert "Shell command execution disabled" in msg


class TestCheckUserApproved:
    """Test user_approved gate."""

    def test_approved(self, state: StateStore) -> None:
        state.set("approved_items", ["REQ-001", "DESIGN-001"])
        passed, msg = check_user_approved("REQ-001", state)
        assert passed

    def test_not_approved(self, state: StateStore) -> None:
        state.set("approved_items", ["REQ-001"])
        passed, msg = check_user_approved("REQ-002", state)
        assert not passed

    def test_empty_approved_list(self, state: StateStore) -> None:
        state.set("approved_items", [])
        passed, msg = check_user_approved("REQ-001", state)
        assert not passed


class TestCheckStateSet:
    """Test state_set gate."""

    def test_variable_set(self, state: StateStore) -> None:
        state.set("my_var", "value")
        passed, msg = check_state_set("my_var", state)
        assert passed

    def test_variable_not_set(self, state: StateStore) -> None:
        passed, msg = check_state_set("nonexistent", state)
        assert not passed


class TestCheckGate:
    """Test unified check_gate dispatcher."""

    def test_file_exists_gate(self, project_root: Path, state: StateStore) -> None:
        passed, msg = check_gate("file_exists:docs/test.md", project_root, state)
        assert passed

    def test_file_contains_gate(self, project_root: Path, state: StateStore) -> None:
        passed, msg = check_gate(
            "file_contains:docs/test.md:status: approved", project_root, state
        )
        assert passed

    def test_command_success_gate(self, state: StateStore, monkeypatch) -> None:
        # Variables are resolved before reaching check_gate in normal flow,
        # but test with already-resolved value
        monkeypatch.setenv("DEVFLOW_ALLOW_SHELL", "1")
        state.set("test_command", "echo ok")
        resolved = resolve_variables("command_success:{test_command}", state)
        passed, msg = check_gate(resolved, Path.cwd(), state)
        assert passed

    def test_unresolved_variable_in_gate(self, state: StateStore) -> None:
        passed, msg = check_gate("command_success:{not_configured}", Path.cwd(), state)
        assert not passed
        assert "Unresolved" in msg

    def test_user_approved_gate(self, state: StateStore) -> None:
        state.set("approved_items", ["ITEM-001"])
        passed, msg = check_gate("user_approved:ITEM-001", Path.cwd(), state)
        assert passed

    def test_state_set_gate(self, state: StateStore) -> None:
        state.set("my_var", "val")
        passed, msg = check_gate("state_set:my_var", Path.cwd(), state)
        assert passed

    def test_unknown_gate_type_passes(self, state: StateStore) -> None:
        passed, msg = check_gate("unknown_type:something", Path.cwd(), state)
        assert passed
        assert "Unknown" in msg


class TestCheckAllGates:
    """Test check_all_gates aggregation."""

    def test_all_pass(self, project_root: Path, state: StateStore) -> None:
        gates = ["file_exists:docs/test.md"]
        all_passed, results = check_all_gates(gates, project_root, state)
        assert all_passed

    def test_some_fail(self, project_root: Path, state: StateStore) -> None:
        gates = ["file_exists:docs/test.md", "file_exists:docs/missing.md"]
        all_passed, results = check_all_gates(gates, project_root, state)
        assert not all_passed
        assert len(results) == 2

    def test_empty_gates(self, project_root: Path, state: StateStore) -> None:
        all_passed, results = check_all_gates([], project_root, state)
        assert all_passed
        assert results == []
