"""Tests for state_store module — delete method and persistence."""

import tempfile
from pathlib import Path

import pytest

from devflow.state_store import StateStore


@pytest.fixture
def state() -> StateStore:
    """Create a StateStore in a temp directory."""
    tmpdir = tempfile.mkdtemp()
    state = StateStore(Path(tmpdir) / "state.toml")
    yield state
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestStateStoreSetGet:
    """Test basic set/get operations."""

    def test_set_and_get(self, state: StateStore) -> None:
        state.set("key1", "value1")
        assert state.get("key1") == "value1"

    def test_get_default(self, state: StateStore) -> None:
        assert state.get("missing") is None
        assert state.get("missing", 42) == 42

    def test_set_integer(self, state: StateStore) -> None:
        state.set("count", 5)
        assert state.get("count") == 5

    def test_set_list(self, state: StateStore) -> None:
        state.set("items", ["a", "b"])
        assert state.get("items") == ["a", "b"]


class TestStateStoreDelete:
    """Test delete method."""

    def test_delete_existing_key(self, state: StateStore) -> None:
        state.set("my_key", 42)
        assert state.get("my_key") == 42
        state.delete("my_key")
        assert state.get("my_key") is None

    def test_delete_nonexistent_key_no_error(self, state: StateStore) -> None:
        # Should not raise
        state.delete("nonexistent")

    def test_delete_persists_across_reload(self, state: StateStore) -> None:
        state.set("temp_key", "hello")
        state.delete("temp_key")
        # Reload from same path
        state2 = StateStore(state.state_path)
        assert state2.get("temp_key") is None

    def test_delete_then_set(self, state: StateStore) -> None:
        state.set("key", "first")
        state.delete("key")
        state.set("key", "second")
        assert state.get("key") == "second"


class TestStateStoreCurrentStep:
    """Test current_step property."""

    def test_current_step_default_none(self, state: StateStore) -> None:
        assert state.current_step is None

    def test_set_current_step(self, state: StateStore) -> None:
        state.current_step = "step-1"
        assert state.current_step == "step-1"

    def test_clear_current_step(self, state: StateStore) -> None:
        state.current_step = "step-1"
        state.current_step = None
        assert state.current_step is None


class TestStateStoreCurrentWorkflow:
    """Test current_workflow property."""

    def test_current_workflow_default_none(self, state: StateStore) -> None:
        assert state.current_workflow is None

    def test_set_current_workflow(self, state: StateStore) -> None:
        state.current_workflow = "MODE-A"
        assert state.current_workflow == "MODE-A"


class TestStateStoreWorkflowRunId:
    """Test workflow_run_id property."""

    def test_workflow_run_id_auto_generated(self, state: StateStore) -> None:
        run_id = state.workflow_run_id
        assert run_id is not None
        assert len(run_id) == 8

    def test_workflow_run_id_stable(self, state: StateStore) -> None:
        id1 = state.workflow_run_id
        id2 = state.workflow_run_id
        assert id1 == id2

    def test_reset_run_id(self, state: StateStore) -> None:
        old_id = state.workflow_run_id
        new_id = state.reset_run_id()
        assert new_id != old_id
        assert state.workflow_run_id == new_id
