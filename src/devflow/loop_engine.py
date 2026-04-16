"""Loop engine for autonomous workflow execution."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from devflow.backlog import Backlog
from devflow.progress import ProgressLogger
from devflow.vcs import detect_vcs
from devflow.workflow_engine import WorkflowEngine

if TYPE_CHECKING:
    from devflow.vcs import VCSDriver
    from devflow.workflow_parser import Step


@dataclass
class LoopResult:
    """Result of a loop run."""

    status: str  # "complete", "blocked", "max_iterations_reached"
    step: str | None = None
    message: str = ""


class LoopEngine:
    """Autonomous loop engine that drives workflow execution."""

    def __init__(self, project_root: Path, tool: str = "local") -> None:
        self.project_root = project_root
        self.tool = tool
        self.backlog_path = project_root / ".devflow" / "backlog.json"
        self.backlog = Backlog.load(self.backlog_path)
        self.progress = ProgressLogger(project_root)
        self.vcs: VCSDriver = detect_vcs(project_root)

    def _ensure_backlog(self) -> bool:
        """Ensure backlog exists; auto-generate from current workflow if missing."""
        if self.backlog.tasks:
            return True

        engine = WorkflowEngine.from_project(self.project_root)
        if not engine:
            return False

        self.backlog = Backlog.generate_from_workflow(engine.workflow)
        self.backlog.save(self.backlog_path)
        return True

    def _ensure_workflow_engine(self, workflow_id: str, step_id: str) -> WorkflowEngine | None:
        """Ensure a WorkflowEngine is loaded for the given workflow and step."""
        engine = WorkflowEngine.from_workflow(workflow_id, self.project_root)
        if not engine:
            return None

        # Force the current step if needed
        if engine.state.current_step != step_id:
            engine.state.current_step = step_id

        return engine

    def _build_agent_prompt(self, engine: WorkflowEngine, step: Step) -> str:
        """Build the prompt for the agent subprocess."""
        instruction = engine.format_current_instruction()
        recent = self.progress.recent_summary(3)

        parts = [
            instruction,
            "",
            "=" * 50,
            "Historical Progress (last 3 entries)",
            "=" * 50,
            recent or "(no prior progress)",
            "",
            "Complete the current step, then exit. Do not run other commands.",
        ]
        return "\n".join(parts)

    def _spawn_agent(self, prompt: str) -> tuple[bool, str]:
        """Spawn the agent subprocess."""
        if self.tool == "local":
            cmd = [sys.executable, "-m", "devflow.agent_runner"]
            kwargs: dict[str, Any] = {
                "cwd": self.project_root,
                "capture_output": True,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
                "timeout": 300,
                "input": prompt,
            }
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(cmd, **kwargs)
            return result.returncode == 0, result.stdout

        # Future: external CLI tools (claude, amp, etc.)
        return False, f"Unsupported tool: {self.tool}"

    def _checkpoint(self, task_id: str, step_id: str, run_id: str) -> str | None:
        """Save a checkpoint and return its identifier."""
        tag = f"{run_id}-{step_id}"
        checkpoint_path = self.vcs.save_checkpoint(tag)
        if checkpoint_path:
            return checkpoint_path.name
        return None

    def run(self, max_iterations: int = 10) -> LoopResult:
        """Run the autonomous loop."""
        if not self._ensure_backlog():
            return LoopResult(status="blocked", message="No backlog and no workflow found")

        for iteration in range(1, max_iterations + 1):
            task = self.backlog.next_pending()
            if not task:
                return LoopResult(status="complete", message="All tasks completed")

            engine = self._ensure_workflow_engine(task.workflow_id, task.step_id)
            if not engine:
                return LoopResult(
                    status="blocked",
                    step=task.step_id,
                    message=f"Workflow not found: {task.workflow_id}",
                )

            step = engine.get_current_step()
            if not step:
                return LoopResult(
                    status="blocked",
                    step=task.step_id,
                    message="Step not found",
                )

            prompt = self._build_agent_prompt(engine, step)
            success, output = self._spawn_agent(prompt)

            if not success:
                self.progress.log(f"Agent failed for {task.step_id}: {output}")
                return LoopResult(
                    status="blocked",
                    step=task.step_id,
                    message=f"Agent subprocess failed: {output}",
                )

            # Validate gates and advance
            adv_success, next_step, msg = engine.advance()

            # Workflow complete is signaled as adv_success=False with a special message
            is_complete = "workflow complete" in msg.lower()

            if adv_success or is_complete:
                run_id = engine.state.workflow_run_id or "unknown"
                checkpoint_id = self._checkpoint(task.id, step.id, run_id)
                self.backlog.mark_done(task.id, checkpoint_id=checkpoint_id)
                self.backlog.save(self.backlog_path)
                self.progress.log(
                    f"Completed {task.step_id}. Checkpoint: {checkpoint_id or 'none'}"
                )
                if is_complete:
                    return LoopResult(status="complete", message=msg)
                # Continue to next iteration
            else:
                # Check if a fail route was triggered (step changed)
                if next_step and next_step.id != task.step_id:
                    self.progress.log(
                        f"Routed on failure: {task.step_id} -> {next_step.id} — {msg}"
                    )
                    # Do not mark done; loop continues with new step
                    continue

                self.progress.log(f"Blocked at {task.step_id}: {msg}")
                return LoopResult(status="blocked", step=task.step_id, message=msg)

        return LoopResult(
            status="max_iterations_reached",
            step=task.step_id if task else None,
            message=f"Reached max iterations ({max_iterations})",
        )

    def status(self) -> str:
        """Return a human-readable loop status."""
        lines = ["Loop Status", "=" * 30, ""]

        total = len(self.backlog.tasks)
        done = sum(1 for t in self.backlog.tasks if t.passes)
        pending = total - done

        lines.append(f"Source: {self.backlog.source or 'N/A'}")
        lines.append(f"Total tasks: {total}")
        lines.append(f"Completed: {done}")
        lines.append(f"Pending: {pending}")
        lines.append("")

        if pending:
            next_task = self.backlog.next_pending()
            if next_task:
                lines.append(f"Next task: {next_task.id} ({next_task.title})")
        else:
            lines.append("All tasks complete!")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset loop progress (keeps progress.md as history)."""
        self.backlog.reset()
        self.backlog.save(self.backlog_path)

        # Reset workflow state step history and fail counts
        engine = WorkflowEngine.from_project(self.project_root)
        if engine:
            state = engine.state
            first_step = engine.workflow.get_first_step()
            state.current_step = first_step.id if first_step else None
            state.set("step_history", [])
            for step in engine.workflow.steps:
                state.delete(f"{step.id}_fail_count")
