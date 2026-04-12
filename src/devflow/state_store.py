"""State persistence for workflow."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import toml


class StateStore:
    """Simple key-value state store using TOML."""

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load state from file."""
        if self.state_path.exists():
            try:
                self._data = toml.load(self.state_path)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def save(self) -> None:
        """Save state to file."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            toml.dump(self._data, f)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value and save."""
        self._data[key] = value
        self.save()

    def delete(self, key: str) -> None:
        """Delete a key from state."""
        if key in self._data:
            del self._data[key]
            self.save()

    @property
    def current_step(self) -> str | None:
        """Get current step ID."""
        return self._data.get("current_step")

    @current_step.setter
    def current_step(self, step_id: str | None) -> None:
        """Set current step ID."""
        if step_id:
            self._data["current_step"] = step_id
        elif "current_step" in self._data:
            del self._data["current_step"]
        self.save()

    @property
    def current_workflow(self) -> str | None:
        """Get current workflow ID."""
        return self._data.get("current_workflow")

    @current_workflow.setter
    def current_workflow(self, workflow_id: str | None) -> None:
        """Set current workflow ID."""
        if workflow_id:
            self._data["current_workflow"] = workflow_id
        elif "current_workflow" in self._data:
            del self._data["current_workflow"]
        self.save()

    @property
    def workflow_run_id(self) -> str:
        """Get or generate workflow run ID."""
        run_id = self._data.get("workflow_run_id")
        if not run_id:
            # Generate short unique ID (8 chars)
            run_id = uuid.uuid4().hex[:8]
            self._data["workflow_run_id"] = run_id
            self.save()
        return run_id

    def reset_run_id(self) -> str:
        """Generate new workflow run ID."""
        run_id = uuid.uuid4().hex[:8]
        self._data["workflow_run_id"] = run_id
        self.save()
        return run_id

    @classmethod
    def from_project(cls, project_root: Path | None = None) -> StateStore:
        """Create StateStore from project root.

        Args:
            project_root: Project root directory (default: cwd)

        Returns:
            StateStore instance
        """
        if project_root is None:
            project_root = Path.cwd()
        state_path = project_root / ".devflow" / "state.toml"
        return cls(state_path)
