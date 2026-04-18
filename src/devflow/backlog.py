"""Backlog management for Ralph Loop integration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devflow.workflow_parser import Workflow


@dataclass
class Task:
    """A single task in the backlog."""

    id: str
    workflow_id: str
    step_id: str
    title: str
    passes: bool = False
    checkpoint_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class Backlog:
    """Backlog of tasks for loop execution."""

    source: str
    tasks: list[Task] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> Backlog:
        """Load backlog from JSON file."""
        if not path.exists():
            return cls(source="")

        data = json.loads(path.read_text(encoding="utf-8"))
        tasks = [Task(**t) for t in data.get("tasks", [])]
        return cls(source=data.get("source", ""), tasks=tasks)

    def save(self, path: Path) -> None:
        """Save backlog to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "source": self.source,
            "tasks": [asdict(t) for t in self.tasks],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def generate_from_workflow(cls, workflow: Workflow) -> Backlog:
        """Generate a backlog from a workflow definition."""
        tasks: list[Task] = []
        for step in workflow.steps:
            tasks.append(
                Task(
                    id=step.id,
                    workflow_id=workflow.id,
                    step_id=step.id,
                    title=step.name or step.id,
                    passes=False,
                    checkpoint_id=None,
                    metadata={},
                )
            )
        return cls(source=workflow.id, tasks=tasks)

    def next_pending(self) -> Task | None:
        """Return the first task that has not passed."""
        for task in self.tasks:
            if not task.passes:
                return task
        return None

    def mark_done(self, task_id: str, checkpoint_id: str | None = None) -> None:
        """Mark a task as done."""
        for task in self.tasks:
            if task.id == task_id:
                task.passes = True
                task.checkpoint_id = checkpoint_id
                break

    def reset(self) -> None:
        """Reset all tasks to pending."""
        for task in self.tasks:
            task.passes = False
            task.checkpoint_id = None
