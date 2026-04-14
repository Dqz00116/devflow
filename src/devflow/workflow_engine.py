"""Workflow engine for progressive disclosure."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from devflow.gate_checker import check_all_gates, resolve_variables
from devflow.state_store import StateStore
from devflow.workflow_parser import FailRoute, Step, Workflow, discover_workflows, load_workflow_with_inheritance

if TYPE_CHECKING:
    pass


class WorkflowEngine:
    """Orchestrates workflow progression."""

    def __init__(
        self, workflow: Workflow, workflow_path: Path, state: StateStore, project_root: Path
    ):
        self.workflow = workflow
        self.workflow_path = workflow_path
        self.state = state
        self.project_root = project_root
        self.workflow_id = workflow.id
        # Stored results from last advance() for format_done_result()
        self._last_results: tuple[bool, list[tuple[bool, str]]] = (False, [])
        self._last_routed_step: Step | None = None
        self._last_fail_count: int = 0

    @classmethod
    def discover_workflows(cls, project_root: Path | None = None) -> list[tuple[str, Path]]:
        """Discover all available workflow files.

        Args:
            project_root: Project root (default: cwd)

        Returns:
            List of (workflow_id, path) tuples
        """
        if project_root is None:
            project_root = Path.cwd()

        return discover_workflows(project_root)

    @classmethod
    def from_workflow(cls, workflow_id: str, project_root: Path | None = None) -> WorkflowEngine | None:
        """Create WorkflowEngine for specific workflow.

        Args:
            workflow_id: Workflow ID (e.g., "MODE-A")
            project_root: Project root (default: cwd)

        Returns:
            WorkflowEngine instance or None if not found
        """
        if project_root is None:
            project_root = Path.cwd()

        workflows_dir = project_root / ".devflow" / "workflows"
        workflow_path = workflows_dir / f"{workflow_id}.toml"

        if not workflow_path.exists():
            return None

        workflow = load_workflow_with_inheritance(workflow_path, project_root)
        if not workflow:
            return None

        state = StateStore.from_project(project_root)
        # Reset step if switching workflows
        if state.current_workflow != workflow_id:
            state.current_step = None
        state.current_workflow = workflow_id

        return cls(workflow, workflow_path, state, project_root)

    @classmethod
    def from_project(cls, project_root: Path | None = None) -> WorkflowEngine | None:
        """Create WorkflowEngine from project (uses saved workflow or first available).

        Args:
            project_root: Project root (default: cwd)

        Returns:
            WorkflowEngine instance or None if no workflows found
        """
        if project_root is None:
            project_root = Path.cwd()

        state = StateStore.from_project(project_root)

        # Check if workflow is already selected
        saved_workflow = state.current_workflow
        if saved_workflow:
            engine = cls.from_workflow(saved_workflow, project_root)
            if engine:
                return engine

        # Use first available workflow
        workflows = cls.discover_workflows(project_root)
        if workflows:
            workflow_id, _ = workflows[0]
            state.current_workflow = workflow_id
            return cls.from_workflow(workflow_id, project_root)

        return None

    def _resolve_step_variables(self, step: Step) -> tuple[str, list[str]]:
        """Resolve all variables in step prompt and gates.

        Uses unified resolve_variables() from gate_checker for consistency.
        Also resolves config variables ({test_command}, {lint_command}, etc.)
        from the project configuration.

        Returns:
            (resolved_prompt, resolved_gates)
        """
        # Load config variables into state for resolution
        self._inject_config_variables()

        prompt = resolve_variables(step.prompt, self.state)
        gates = [resolve_variables(g, self.state) for g in step.gates]
        return prompt, gates

    def _inject_config_variables(self) -> None:
        """Inject project config values as state variables for resolution."""
        # Ensure workflow_run_id is populated in state data
        _ = self.state.workflow_run_id

        from devflow.config import DevFlowConfig

        # Find config relative to project root (not cwd)
        config_path = self.project_root / ".devflow" / "config.toml"
        if not config_path.exists():
            # Fall back to find_config which searches from cwd
            config_path = DevFlowConfig.find_config()
            if not config_path.exists():
                return

        config = DevFlowConfig.load(config_path)

        # Map config commands to state variables (only if not already set by user)
        config_vars = {
            "test_command": config.commands.test,
            "lint_command": config.commands.lint,
            "build_command": config.commands.build,
            "test_unit_command": config.commands.test_unit,
            "test_integration_command": config.commands.test_integration,
        }

        for key, value in config_vars.items():
            if value and self.state.get(key) is None:
                self.state.set(key, value)

    def _reset_fail_count(self, step_id: str) -> None:
        """Reset the failure count for a step by deleting it from state.

        Args:
            step_id: The step ID to reset failures for
        """
        key = f"{step_id}_fail_count"
        self.state.delete(key)

    def _push_step_history(self, step_id: str) -> None:
        """Push a step ID onto the step history stack."""
        history = self.state.get("step_history", [])
        if not isinstance(history, list):
            history = []
        history.append(step_id)
        self.state.set("step_history", history)

    def _resolve_target(self, target: str) -> tuple[WorkflowEngine | None, str | None, str]:
        """Resolve a step target, potentially cross-workflow.

        If target contains ':', it is treated as 'workflow_id:step_id' (cross-workflow).
        Otherwise, it is a step in the current workflow.

        Args:
            target: Step ID or 'workflow_id:step_id' cross-workflow reference

        Returns:
            (engine, step_id, message) — engine and step_id are None on error
        """
        if ":" in target:
            workflow_id, step_id = target.split(":", 1)
            target_engine = WorkflowEngine.from_workflow(workflow_id, self.project_root)
            if target_engine is None:
                return None, None, f"Target workflow not found: {workflow_id}"
            target_step = target_engine.workflow.get_step(step_id)
            if target_step is None:
                return None, None, f"Step '{step_id}' not found in workflow '{workflow_id}'"
            return target_engine, step_id, f"Cross-workflow target: {workflow_id}:{step_id}"
        else:
            # Same-workflow target — validate step exists
            if self.workflow.get_step(target) is None:
                return None, None, f"Step '{target}' not found in workflow '{self.workflow_id}'"
            return self, target, ""

    def _switch_to_workflow(self, target_engine: WorkflowEngine) -> None:
        """Switch this engine to a different workflow.

        Args:
            target_engine: Engine for the target workflow
        """
        self.workflow = target_engine.workflow
        self.workflow_path = target_engine.workflow_path
        self.workflow_id = target_engine.workflow_id
        self.state.current_workflow = target_engine.workflow_id

    def get_current_step(self) -> Step | None:
        """Get current step.

        Returns:
            Current Step or None
        """
        current_step_id = self.state.current_step

        if current_step_id is None:
            # First time, get first step
            first_step = self.workflow.get_first_step()
            if first_step:
                self.state.current_step = first_step.id
                return first_step
            return None

        return self.workflow.get_step(current_step_id)

    def check_done(self) -> tuple[bool, list[tuple[bool, str]]]:
        """Check if current step is done.

        Returns:
            (all_passed, list of (is_passed, message))
        """
        current_step = self.get_current_step()
        if not current_step:
            return False, [(False, "No current step")]

        if not current_step.gates:
            # No gates, always done
            return True, []

        # Resolve variables in gates before checking
        self._inject_config_variables()
        resolved_gates = [resolve_variables(g, self.state) for g in current_step.gates]

        return check_all_gates(resolved_gates, self.project_root, self.state)

    def advance(self) -> tuple[bool, Step | None, str]:
        """Advance to next step if current is done, or route on failure.

        When gates pass: advance to next_step (with cross-workflow support).
        When gates fail: check fail_routes and route if a match is found.

        Also stores results for format_done_result() to display.

        Returns:
            (success, next_step, message)
        """
        current_step = self.get_current_step()
        if not current_step:
            self._last_results = (False, [])
            return False, None, "No current step"

        # Check gates
        all_passed, results = self.check_done()
        self._last_results = (all_passed, results)

        if all_passed:
            # Reset fail count on success
            self._reset_fail_count(current_step.id)

            # Find next step
            if not current_step.next_step:
                return False, None, "Workflow complete!"

            # Resolve target (may be cross-workflow)
            target_engine, target_step_id, resolve_msg = self._resolve_target(current_step.next_step)
            if target_engine is None:
                return False, None, resolve_msg

            target_step = target_engine.workflow.get_step(target_step_id)
            if target_step is None:
                return False, None, f"Next step not found: {current_step.next_step}"

            # Handle cross-workflow switch
            if target_engine is not self:
                self._switch_to_workflow(target_engine)
                self.state.set("step_history", [])

            # Update history and state
            self._push_step_history(current_step.id)
            self.state.current_step = target_step.id

            return True, target_step, f"Advanced to: {target_step.name}"

        else:
            # Gates failed — compute tentative fail count before persisting
            key = f"{current_step.id}_fail_count"
            fail_count = self.state.get(key, 0)
            if not isinstance(fail_count, int):
                fail_count = 0
            fail_count += 1

            # Check fail routes (ordered) against tentative count
            for route in current_step.fail_routes:
                max_fails = route.max_fails if route.max_fails is not None else float("inf")
                if route.min_fails <= fail_count <= max_fails:
                    # Match found — resolve target first
                    target_engine, target_step_id, resolve_msg = self._resolve_target(route.target)
                    if target_engine is None:
                        # Target not found — print warning and fall through
                        print(f"Warning: {resolve_msg}")
                        continue

                    target_step = target_engine.workflow.get_step(target_step_id)
                    if target_step is None:
                        # Step not found — print warning and fall through
                        print(f"Warning: Step '{target_step_id}' not found in workflow")
                        continue

                    # Route is valid — persist the fail count (do NOT reset;
                    # count persists across visits so escalation thresholds work)
                    self.state.set(key, fail_count)

                    # Handle cross-workflow switch
                    if target_engine is not self:
                        self._switch_to_workflow(target_engine)
                        self.state.set("step_history", [])

                    # Update history and state
                    self._push_step_history(current_step.id)
                    self.state.current_step = target_step.id

                    # Store routing info for format_done_result
                    self._last_routed_step = target_step

                    return True, target_step, f"Routed on failure: {current_step.name} -> {target_step.name}"

            # No fail_route matched — persist the incremented fail count
            self.state.set(key, fail_count)
            self._last_routed_step = None
            self._last_fail_count = fail_count

            failed = [msg for passed, msg in results if not passed]
            return False, current_step, "Gates not satisfied:\n  - " + "\n  - ".join(failed)

    def go_back(self) -> tuple[bool, Step | None, str]:
        """Go back to the previous step using the step history stack.

        Returns:
            (success, previous_step, message)
        """
        current_step = self.get_current_step()
        if not current_step:
            return False, None, "No current step"

        history = self.state.get("step_history", [])
        if not isinstance(history, list) or not history:
            return False, current_step, "Already at the first step"

        prev_step_id = history.pop()
        self.state.set("step_history", history)

        prev_step = self.workflow.get_step(prev_step_id)
        if prev_step is None:
            return False, current_step, "Already at the first step"

        self.state.current_step = prev_step.id
        return True, prev_step, f"Returned to: {prev_step.name}"

    def format_current_instruction(self) -> str:
        """Format current step instruction for display.

        Returns:
            Formatted instruction string
        """
        step = self.get_current_step()
        if not step:
            return "No workflow steps defined."

        # Use unified variable resolution
        prompt, gates = self._resolve_step_variables(step)

        lines = [
            "=" * 50,
            f"  Workflow: {self.workflow_id}",
            f"  Current Step: {step.id}",
            f"  Name: {step.name}",
            "=" * 50,
            "",
            prompt,
            "",
        ]

        if gates:
            lines.extend([
                "Gate Conditions:",
            ])
            for gate in gates:
                lines.append(f"  - {gate}")
            lines.append("")

        if step.fail_routes:
            lines.append("On Failure:")
            for route in step.fail_routes:
                max_label = f"-{route.max_fails}" if route.max_fails is not None else "+"
                lines.append(f"  - Fails {route.min_fails}{max_label} times → {route.target}")
            lines.append("")

        lines.append("Run when done: devflow done")

        return "\n".join(lines)

    def format_done_result(self) -> str:
        """Format done check result.

        Uses stored results from the last advance() call.

        Returns:
            Formatted result string
        """
        all_passed, results = getattr(self, "_last_results", (False, []))
        routed_step = getattr(self, "_last_routed_step", None)
        fail_count = getattr(self, "_last_fail_count", 0)

        lines = [
            "Checking Gate conditions...",
            "",
        ]

        if all_passed:
            lines.append("✓ All conditions satisfied")
            lines.append("")
        else:
            lines.append(f"✗ Step not complete (attempt {fail_count})")
            lines.append("")
            for passed, msg in results:
                if not passed:
                    lines.append(f"  ✗ {msg}")

            if routed_step:
                lines.append(f"→ Routing to: {routed_step.name}")
                lines.append("  (Run devflow current for new instructions)")
            else:
                lines.append("")
                lines.append("Fix and run again: devflow done")

        return "\n".join(lines)

    def format_status(self) -> str:
        """Format workflow status.

        Returns:
            Formatted status string
        """
        lines = [
            "Workflow Status",
            "=" * 30,
            "",
            f"Workflow: {self.workflow_id}",
            "",
        ]

        current_step = self.get_current_step()
        if current_step:
            lines.append(f"Current Step: {current_step.id} ({current_step.name})")
        else:
            lines.append("Current Step: None")

        lines.append(f"Total Steps: {len(self.workflow.steps)}")
        lines.append("")

        if self.workflow.steps:
            lines.append("Step List:")
            for i, step in enumerate(self.workflow.steps, 1):
                marker = "→" if step.id == self.state.current_step else " "
                suffix = " [has fail routes]" if step.fail_routes else ""
                lines.append(f"{marker} {i}. {step.id}: {step.name}{suffix}")

        return "\n".join(lines)
