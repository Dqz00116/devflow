"""Status command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table

from devflow.req_cmd import Requirement, get_requirements_dir
from devflow.task_cmd import load_tasks

if TYPE_CHECKING:
    from rich.console import Console

    from devflow.config import DevFlowConfig


def show_status(config: DevFlowConfig, console: Console) -> None:
    """Show project status overview."""
    project_root = Path.cwd()
    config_path = project_root / ".devflow" / "config.toml"

    # Check if initialized
    if not config_path.exists():
        console.print("[red]Error: DevFlow not initialized.[/red]")
        console.print("Run 'devflow init' to initialize the project.")
        return

    # Project info
    console.print()
    console.print(Panel.fit(
        f"[bold]{config.project.name}[/bold]\n"
        f"Language: {config.project.language}\n"
        f"Version: {config.project.version}",
        title="Project",
        border_style="blue",
    ))

    # Requirements summary
    req_dir = get_requirements_dir(config)
    requirements: list[Requirement] = []
    if req_dir.exists():
        for file_path in req_dir.glob("REQ-*.md"):
            req = Requirement.from_file(file_path)
            if req:
                requirements.append(req)

    # Tasks summary
    tasks = load_tasks(config)

    # Status table
    table = Table(title="Status Overview")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="white")
    table.add_column("Breakdown", style="dim")

    # Requirements by status
    req_statuses: dict[str, int] = {}
    for req in requirements:
        req_statuses[req.status] = req_statuses.get(req.status, 0) + 1

    req_breakdown = ", ".join(
        f"{status}: {count}" for status, count in sorted(req_statuses.items())
    ) if req_statuses else "None"

    table.add_row(
        "Requirements",
        str(len(requirements)),
        req_breakdown,
    )

    # Tasks by status
    task_statuses: dict[str, int] = {}
    for task in tasks:
        task_statuses[task.status] = task_statuses.get(task.status, 0) + 1

    task_breakdown = ", ".join(
        f"{status}: {count}" for status, count in sorted(task_statuses.items())
    ) if task_statuses else "None"

    table.add_row(
        "Tasks",
        str(len(tasks)),
        task_breakdown,
    )

    console.print()
    console.print(table)

    # Recent activity (last 5 tasks)
    if tasks:
        console.print("\n[bold]Recent Tasks:[/bold]")
        recent_tasks = sorted(tasks, key=lambda t: t.created, reverse=True)[:5]
        for task in recent_tasks:
            status_color = {
                "done": "green",
                "in_progress": "yellow",
                "backlog": "dim",
            }.get(task.status, "white")
            console.print(
                f"  [{status_color}]{task.id}[/{status_color}] {task.title} "
                f"([dim]{task.requirement}[/dim])"
            )

    # Workflow stage hint
    console.print("\n[bold]Workflow Stage:[/bold]")
    if not requirements:
        console.print("  [yellow]→ Create your first requirement:[/yellow] devflow req new REQ-001")
    elif any(r.status == "draft" for r in requirements):
        console.print("  [yellow]→ Move requirement to analyzing:[/yellow] devflow req status REQ-001 analyzing")
    elif any(r.status == "analyzing" for r in requirements):
        console.print("  [yellow]→ Complete analysis and approve:[/yellow] devflow req status REQ-001 approved")
    elif any(r.status == "approved" for r in requirements):
        console.print("  [yellow]→ Create tasks for approved requirements:[/yellow] devflow task new -r REQ-001")
    elif any(t.status != "done" for t in tasks):
        console.print("  [yellow]→ Complete in-progress tasks:[/yellow] devflow task done TASK-001")
    else:
        console.print("  [green]✓ All caught up![/green]")
