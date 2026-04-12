"""Parse TOML workflow configurations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml


@dataclass
class FailRoute:
    """A fail route definition for a workflow step.

    Defines where to redirect when a step fails a certain number of times.
    """

    min_fails: int = 1
    max_fails: int | None = None
    target: str = ""


@dataclass
class Step:
    """A workflow step definition."""

    id: str
    name: str = ""
    prompt: str = ""
    prompt_file: str | None = None
    gates: list[str] = field(default_factory=list)
    next_step: str | None = None
    fail_routes: list[FailRoute] = field(default_factory=list)


@dataclass
class Workflow:
    """A complete workflow definition."""

    id: str
    name: str = ""
    description: str = ""
    version: str = "1.0"
    extends: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    steps_dict: dict[str, Step] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        """Build steps dictionary for fast lookup."""
        self.steps_dict = {step.id: step for step in self.steps}

    def get_step(self, step_id: str) -> Step | None:
        """Get step by ID."""
        return self.steps_dict.get(step_id)

    def get_first_step(self) -> Step | None:
        """Get first step in workflow."""
        return self.steps[0] if self.steps else None


def load_prompt(prompt_file: str, workflow_path: Path) -> str:
    """Load prompt from file.

    Args:
        prompt_file: Relative path to prompt file
        workflow_path: Path to workflow TOML file

    Returns:
        Prompt content or empty string if not found
    """
    # Resolve relative to workflow directory
    prompt_path = workflow_path.parent.parent / "prompts" / prompt_file
    if not prompt_path.exists():
        # Try direct relative path
        prompt_path = workflow_path.parent / prompt_file

    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")

    return ""


def parse_workflow(workflow_path: Path) -> Workflow | None:
    """Parse TOML workflow file.

    Args:
        workflow_path: Path to .toml workflow file

    Returns:
        Workflow object or None if parsing fails
    """
    if not workflow_path.exists():
        return None

    try:
        data = toml.load(workflow_path)
    except Exception:
        return None

    # Parse workflow metadata
    workflow_data = data.get("workflow", {})
    workflow = Workflow(
        id=workflow_data.get("id", workflow_path.stem),
        name=workflow_data.get("name", ""),
        description=workflow_data.get("description", ""),
        version=workflow_data.get("version", "1.0"),
        extends=workflow_data.get("extends", []),
    )

    # Parse steps
    steps_data = data.get("steps", [])
    for step_data in steps_data:
        # Parse fail routes for this step
        fail_routes: list[FailRoute] = []
        for fr_data in step_data.get("fail_route", []):
            min_fails = fr_data.get("min_fails", 1)
            max_fails = fr_data.get("max_fails")
            target = fr_data.get("target", "")

            # Validate min_fails >= 1
            if min_fails < 1:
                print(
                    f"Warning: fail_route in step '{step_data.get('id', '')}' "
                    f"has min_fails ({min_fails}) < 1, skipping"
                )
                continue

            # Validate min_fails <= max_fails
            if max_fails is not None and min_fails > max_fails:
                print(
                    f"Warning: fail_route in step '{step_data.get('id', '')}' "
                    f"has min_fails ({min_fails}) > max_fails ({max_fails}), skipping"
                )
                continue

            # Validate target is non-empty
            if not target:
                print(
                    f"Warning: fail_route in step '{step_data.get('id', '')}' "
                    f"has empty target, skipping"
                )
                continue

            fail_routes.append(
                FailRoute(
                    min_fails=min_fails,
                    max_fails=max_fails,
                    target=target,
                )
            )

        step = Step(
            id=step_data.get("id", ""),
            name=step_data.get("name", ""),
            prompt=step_data.get("prompt", ""),
            prompt_file=step_data.get("prompt_file"),
            gates=step_data.get("gates", []),
            next_step=step_data.get("next") or None,
            fail_routes=fail_routes,
        )

        # Load prompt from file if specified
        if step.prompt_file and not step.prompt:
            step.prompt = load_prompt(step.prompt_file, workflow_path)

        workflow.steps.append(step)

    # Rebuild steps dictionary
    workflow.steps_dict = {step.id: step for step in workflow.steps}

    return workflow


def merge_workflows(base: Workflow, override: Workflow) -> Workflow:
    """Merge two workflows, with override taking precedence.

    Args:
        base: Base workflow to extend
        override: Workflow with overrides/additions

    Returns:
        Merged workflow
    """
    # Start with base steps
    merged_steps = {step.id: step for step in base.steps}

    # Apply overrides and additions
    for step in override.steps:
        merged_steps[step.id] = step

    # Create merged workflow
    return Workflow(
        id=override.id,
        name=override.name or base.name,
        description=override.description or base.description,
        version=override.version,
        extends=base.extends + override.extends,
        steps=list(merged_steps.values()),
    )


def load_workflow_with_inheritance(workflow_path: Path, project_root: Path) -> Workflow | None:
    """Load workflow with inheritance resolution.

    Args:
        workflow_path: Path to workflow TOML file
        project_root: Project root directory

    Returns:
        Resolved Workflow or None
    """
    workflow = parse_workflow(workflow_path)
    if not workflow:
        return None

    # Resolve inheritance
    workflows_dir = project_root / ".devflow" / "workflows"
    for parent_id in workflow.extends:
        parent_path = workflows_dir / f"{parent_id}.toml"
        if parent_path.exists():
            parent_workflow = parse_workflow(parent_path)
            if parent_workflow:
                workflow = merge_workflows(parent_workflow, workflow)

    return workflow


def discover_workflows(project_root: Path) -> list[tuple[str, Path]]:
    """Discover all available workflow files.

    Args:
        project_root: Project root directory

    Returns:
        List of (workflow_id, path) tuples
    """
    workflows_dir = project_root / ".devflow" / "workflows"
    if not workflows_dir.exists():
        return []

    workflows = []
    for toml_file in workflows_dir.glob("*.toml"):
        workflows.append((toml_file.stem, toml_file))

    return sorted(workflows, key=lambda x: x[0])
