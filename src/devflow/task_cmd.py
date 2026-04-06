"""Task command implementations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import toml
from rich.table import Table

if TYPE_CHECKING:
    from rich.console import Console

    from devflow.config import DevFlowConfig


@dataclass
class Task:
    """Task data structure."""

    id: str
    title: str
    requirement: str
    status: str
    created: str
    completed: str | None = None


def get_state_path(config: DevFlowConfig) -> Path:
    """Get state file path."""
    config_path = Path.cwd() / ".devflow" / "config.toml"
    if config_path.exists():
        return config_path.parent / "state.toml"
    return Path.cwd() / ".devflow" / "state.toml"


def load_tasks(config: DevFlowConfig) -> list[Task]:
    """Load tasks from state file."""
    state_path = get_state_path(config)

    if not state_path.exists():
        return []

    try:
        data = toml.load(state_path)
        tasks_data = data.get("tasks", [])
        return [Task(**task) for task in tasks_data]
    except Exception:
        return []


def save_tasks(config: DevFlowConfig, tasks: list[Task]) -> None:
    """Save tasks to state file."""
    state_path = get_state_path(config)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "requirement": task.requirement,
                "status": task.status,
                "created": task.created,
                "completed": task.completed,
            }
            for task in tasks
        ]
    }

    with open(state_path, "w", encoding="utf-8") as f:
        toml.dump(data, f)


def generate_task_id(tasks: list[Task]) -> str:
    """Generate next task ID."""
    if not tasks:
        return "TASK-001"

    max_num = 0
    for task in tasks:
        match = re.match(r"TASK-(\d+)", task.id.upper())
        if match:
            max_num = max(max_num, int(match.group(1)))

    return f"TASK-{max_num + 1:03d}"


def list_tasks(
    config: DevFlowConfig,
    requirement_filter: str | None,
    status_filter: str | None,
    console: Console,
) -> None:
    """List all tasks."""
    tasks = load_tasks(config)

    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        console.print("Create one with: devflow task new")
        return

    # Filter tasks
    filtered_tasks = tasks
    if requirement_filter:
        filtered_tasks = [t for t in filtered_tasks if t.requirement.upper() == requirement_filter.upper()]
    if status_filter:
        filtered_tasks = [t for t in filtered_tasks if t.status.lower() == status_filter.lower()]

    # Display as table
    table = Table(title="Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Requirement", style="blue")
    table.add_column("Status", style="green")
    table.add_column("Created", style="dim")

    status_colors: dict[str, str] = {
        "backlog": "dim",
        "todo": "white",
        "in_progress": "yellow",
        "review": "blue",
        "done": "bright_green",
    }

    for task in filtered_tasks:
        status_color = status_colors.get(task.status.lower(), "white")

        table.add_row(
            task.id,
            task.title,
            task.requirement,
            f"[{status_color}]{task.status}[/{status_color}]",
            task.created,
        )

    console.print(table)
    console.print(f"\nTotal: {len(filtered_tasks)} tasks")


def create_task(
    config: DevFlowConfig,
    requirement: str,
    title: str,
    console: Console,
) -> None:
    """Create a new task."""
    tasks = load_tasks(config)

    # Verify requirement exists
    req_dir = Path.cwd() / config.paths.docs / "requirements"
    req_file = req_dir / f"{requirement.upper()}.md"

    if not req_file.exists():
        console.print(f"[yellow]Warning: Requirement {requirement} not found.[/yellow]")
        console.print(f"Expected: {req_file}")

    # Create task
    task_id = generate_task_id(tasks)
    task = Task(
        id=task_id,
        title=title,
        requirement=requirement.upper(),
        status="backlog",
        created=datetime.now().strftime("%Y-%m-%d"),
    )

    tasks.append(task)
    save_tasks(config, tasks)

    console.print(f"[green]✓[/green] Created task: {task_id}")
    console.print(f"  Title: {title}")
    console.print(f"  Requirement: {requirement.upper()}")


def complete_task(
    config: DevFlowConfig,
    task_id: str,
    console: Console,
) -> None:
    """Mark a task as done."""
    tasks = load_tasks(config)

    task_id = task_id.upper()
    found = False

    for task in tasks:
        if task.id == task_id:
            task.status = "done"
            task.completed = datetime.now().strftime("%Y-%m-%d")
            found = True
            break

    if not found:
        console.print(f"[red]Task not found: {task_id}[/red]")
        return

    save_tasks(config, tasks)
    console.print(f"[green]✓[/green] Marked {task_id} as done")
