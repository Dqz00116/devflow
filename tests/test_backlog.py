"""Tests for backlog module — task management and auto-generation."""

from pathlib import Path

from devflow.backlog import Backlog, Task
from devflow.workflow_parser import Step, Workflow


class TestBacklogGeneration:
    def test_generate_from_workflow(self) -> None:
        workflow = Workflow(
            id="MODE-A",
            steps=[
                Step(id="step-1", name="First Step"),
                Step(id="step-2", name="Second Step"),
            ],
        )
        backlog = Backlog.generate_from_workflow(workflow)
        assert backlog.source == "MODE-A"
        assert len(backlog.tasks) == 2
        assert backlog.tasks[0].id == "step-1"
        assert backlog.tasks[0].title == "First Step"
        assert backlog.tasks[1].id == "step-2"

    def test_next_pending(self) -> None:
        backlog = Backlog(
            source="MODE-A",
            tasks=[
                Task(id="s1", workflow_id="MODE-A", step_id="s1", title="S1", passes=True),
                Task(id="s2", workflow_id="MODE-A", step_id="s2", title="S2", passes=False),
            ],
        )
        pending = backlog.next_pending()
        assert pending is not None
        assert pending.id == "s2"

    def test_next_pending_none(self) -> None:
        backlog = Backlog(
            source="MODE-A",
            tasks=[
                Task(id="s1", workflow_id="MODE-A", step_id="s1", title="S1", passes=True),
            ],
        )
        assert backlog.next_pending() is None

    def test_mark_done(self) -> None:
        backlog = Backlog(
            source="MODE-A",
            tasks=[
                Task(id="s1", workflow_id="MODE-A", step_id="s1", title="S1", passes=False),
            ],
        )
        backlog.mark_done("s1", checkpoint_id="abc123")
        assert backlog.tasks[0].passes is True
        assert backlog.tasks[0].checkpoint_id == "abc123"

    def test_save_and_load(self, tmp_path: Path) -> None:
        path = tmp_path / "backlog.json"
        backlog = Backlog(
            source="MODE-A",
            tasks=[
                Task(id="s1", workflow_id="MODE-A", step_id="s1", title="S1"),
            ],
        )
        backlog.save(path)
        loaded = Backlog.load(path)
        assert loaded.source == "MODE-A"
        assert len(loaded.tasks) == 1
        assert loaded.tasks[0].id == "s1"

    def test_reset(self) -> None:
        backlog = Backlog(
            source="MODE-A",
            tasks=[
                Task(
                    id="s1",
                    workflow_id="MODE-A",
                    step_id="s1",
                    title="S1",
                    passes=True,
                    checkpoint_id="abc",
                ),
            ],
        )
        backlog.reset()
        assert backlog.tasks[0].passes is False
        assert backlog.tasks[0].checkpoint_id is None
