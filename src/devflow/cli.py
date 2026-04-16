"""Main CLI entry point for DevFlow v2.0 - Progressive Workflow."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console

from devflow import __version__
from devflow.config import DevFlowConfig
from devflow.state_store import StateStore
from devflow.workflow_engine import WorkflowEngine

if TYPE_CHECKING:
    pass

console = Console()


def ensure_workflow(workflow_id: str | None = None) -> WorkflowEngine | None:
    """Ensure workflow exists and return engine.

    Args:
        workflow_id: Specific workflow ID to use, or None to use saved/first

    Returns:
        WorkflowEngine instance or None
    """
    project_root = Path.cwd()

    if workflow_id:
        engine = WorkflowEngine.from_workflow(workflow_id, project_root)
        if not engine:
            console.print(f"[red]Error: Workflow '{workflow_id}' not found.[/red]")
            return None
        return engine

    # Try to get saved workflow or first available
    engine = WorkflowEngine.from_project(project_root)
    if not engine:
        console.print("[red]Error: No workflows found.[/red]")
        console.print("Expected: .devflow/workflows/*.toml")
        console.print("")
        console.print("Create a workflow file or run:")
        console.print("  devflow list-workflows")
        return None

    return engine


@click.group()
@click.version_option(version=__version__, prog_name="devflow")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.pass_context
def cli(ctx: click.Context, config: Path | None) -> None:
    """DevFlow - AI Agent Development Workflow CLI.

    A universal development workflow tool for AI-assisted software development.
    """
    ctx.ensure_object(dict)

    # Load configuration
    if config:
        ctx.obj["config"] = DevFlowConfig.load(config)
    else:
        ctx.obj["config"] = DevFlowConfig.load()


@cli.command()
@click.option(
    "--language",
    "-l",
    type=click.Choice(["python", "javascript", "typescript", "go", "rust", "dotnet", "other"]),
    prompt="Project language",
    help="Primary programming language",
)
@click.option(
    "--name",
    "-n",
    prompt="Project name",
    help="Project name",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing configuration",
)
@click.pass_context
def init(
    ctx: click.Context,
    language: str,
    name: str,
    force: bool,
) -> None:
    """Initialize a new DevFlow project."""
    from devflow.init_cmd import init_project

    config = ctx.obj["config"]
    init_project(config, language, name, force, console)


@cli.group()
def req() -> None:
    """[Legacy] Manage requirements. Prefer workflow commands (current/done)."""
    pass


@req.command(name="list")
@click.option(
    "--status",
    "-s",
    help="Filter by status",
)
@click.pass_context
def req_list(ctx: click.Context, status: str | None) -> None:
    """List all requirements."""
    from devflow.req_cmd import list_requirements

    config = ctx.obj["config"]
    list_requirements(config, status, console)


@req.command(name="new")
@click.argument("req_id")
@click.option(
    "--title",
    "-t",
    prompt="Requirement title",
    help="Requirement title",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["low", "medium", "high", "critical"]),
    default="medium",
    help="Requirement priority",
)
@click.pass_context
def req_new(
    ctx: click.Context,
    req_id: str,
    title: str,
    priority: str,
) -> None:
    """Create a new requirement."""
    from devflow.req_cmd import create_requirement

    config = ctx.obj["config"]
    create_requirement(config, req_id, title, priority, console)


@req.command(name="show")
@click.argument("req_id")
@click.pass_context
def req_show(ctx: click.Context, req_id: str) -> None:
    """Show requirement details."""
    from devflow.req_cmd import show_requirement

    config = ctx.obj["config"]
    show_requirement(config, req_id, console)


@req.command(name="status")
@click.argument("req_id")
@click.argument("new_status")
@click.pass_context
def req_status(ctx: click.Context, req_id: str, new_status: str) -> None:
    """Update requirement status."""
    from devflow.req_cmd import update_requirement_status

    config = ctx.obj["config"]
    update_requirement_status(config, req_id, new_status, console)


@cli.group()
def task() -> None:
    """[Legacy] Manage tasks. Prefer workflow commands (current/done)."""
    pass


@task.command(name="list")
@click.option(
    "--requirement",
    "-r",
    help="Filter by requirement ID",
)
@click.option(
    "--status",
    "-s",
    help="Filter by status",
)
@click.pass_context
def task_list(
    ctx: click.Context,
    requirement: str | None,
    status: str | None,
) -> None:
    """List all tasks."""
    from devflow.task_cmd import list_tasks

    config = ctx.obj["config"]
    list_tasks(config, requirement, status, console)


@task.command(name="new")
@click.option(
    "--requirement",
    "-r",
    required=True,
    prompt="Related requirement ID",
    help="Related requirement ID",
)
@click.option(
    "--title",
    "-t",
    required=True,
    prompt="Task title",
    help="Task title",
)
@click.pass_context
def task_new(
    ctx: click.Context,
    requirement: str,
    title: str,
) -> None:
    """Create a new task."""
    from devflow.task_cmd import create_task

    config = ctx.obj["config"]
    create_task(config, requirement, title, console)


@task.command(name="done")
@click.argument("task_id")
@click.pass_context
def task_done(ctx: click.Context, task_id: str) -> None:
    """Mark a task as done."""
    from devflow.task_cmd import complete_task

    config = ctx.obj["config"]
    complete_task(config, task_id, console)


@cli.group()
def feat() -> None:
    """[Legacy] Manage features. Prefer workflow commands (current/done)."""
    pass


@feat.command(name="list")
@click.option(
    "--status",
    "-s",
    help="Filter by status",
)
@click.option(
    "--requirement",
    "-r",
    help="Filter by requirement ID",
)
@click.pass_context
def feat_list(
    ctx: click.Context,
    status: str | None,
    requirement: str | None,
) -> None:
    """List all features."""
    from devflow.feat_cmd import list_features

    config = ctx.obj["config"]
    list_features(config, status, requirement, console)


@feat.command(name="new")
@click.argument("feat_id")
@click.option(
    "--title",
    "-t",
    prompt="Feature title",
    help="Feature title",
)
@click.option(
    "--requirement",
    "-r",
    required=True,
    prompt="Related requirement ID",
    help="Related requirement ID",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["low", "medium", "high", "critical"]),
    default="medium",
    help="Feature priority",
)
@click.pass_context
def feat_new(
    ctx: click.Context,
    feat_id: str,
    title: str,
    requirement: str,
    priority: str,
) -> None:
    """Create a new feature."""
    from devflow.feat_cmd import create_feature

    config = ctx.obj["config"]
    create_feature(config, feat_id, title, requirement, priority, console)


@feat.command(name="show")
@click.argument("feat_id")
@click.pass_context
def feat_show(ctx: click.Context, feat_id: str) -> None:
    """Show feature details."""
    from devflow.feat_cmd import show_feature

    config = ctx.obj["config"]
    show_feature(config, feat_id, console)


@feat.command(name="status")
@click.argument("feat_id")
@click.argument("new_status")
@click.pass_context
def feat_status(ctx: click.Context, feat_id: str, new_status: str) -> None:
    """Update feature status."""
    from devflow.feat_cmd import update_feature_status

    config = ctx.obj["config"]
    update_feature_status(config, feat_id, new_status, console)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show project status overview."""
    from devflow.status_cmd import show_status

    config = ctx.obj["config"]
    show_status(config, console)


@cli.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate project configuration and workflow compliance."""
    config = ctx.obj["config"]
    config_path = DevFlowConfig.find_config()

    if not config_path.exists():
        console.print("[red]Error: No DevFlow configuration found.[/red]")
        console.print("Run 'devflow init' to initialize the project.")
        sys.exit(1)

    console.print(f"[green]✓[/green] Configuration found: {config_path}")
    console.print(f"[green]✓[/green] Project: {config.project.name}")
    console.print(f"[green]✓[/green] Language: {config.project.language}")

    # Check v2 required structure
    project_root = config_path.parent.parent
    workflows_dir = project_root / ".devflow" / "workflows"
    agents_file = project_root / "AGENTS.md"

    all_valid = True

    # Check workflow directory
    if workflows_dir.exists():
        toml_files = list(workflows_dir.glob("*.toml"))
        if toml_files:
            console.print(f"[green]✓[/green] Workflows: {len(toml_files)} found")
        else:
            console.print("[red]✗[/red] No workflow TOML files found in .devflow/workflows/")
            all_valid = False
    else:
        console.print("[red]✗[/red] .devflow/workflows/ directory missing")
        all_valid = False

    # Check AGENTS.md
    if agents_file.exists():
        console.print("[green]✓[/green] AGENTS.md")
    else:
        console.print("[yellow]✗[/yellow] AGENTS.md (missing, recommended)")
        # Not critical for v2

    # Check config has test command
    if config.commands.test:
        console.print(f"[green]✓[/green] Test command: {config.commands.test}")
    else:
        console.print(
            "[yellow]✗[/yellow] Test command not configured (set in .devflow/config.toml)"
        )

    if all_valid:
        console.print("\n[green]All validations passed![/green]")
    else:
        console.print(
            "\n[yellow]Some issues found. Run 'devflow init' to create missing files.[/yellow]"
        )


# ============================================================================
# Workflow v2 Commands - Progressive Disclosure
# ============================================================================

@cli.command()
@click.option("--workflow", "-w", help="Workflow ID to use")
def current(workflow: str | None) -> None:
    """Get current step instruction.

    This is the primary command for AI agents.
    Run this first to know what to do.
    """
    engine = ensure_workflow(workflow)
    if not engine:
        return

    instruction = engine.format_current_instruction()
    console.print(instruction, markup=False)


@cli.command()
def done() -> None:
    """Mark current step done and advance.

    Checks gate conditions and advances to next step if all pass.
    On failure, checks fail_routes and reroutes if applicable.
    """
    engine = ensure_workflow()
    if not engine:
        return

    # advance() checks gates and handles both pass (advance) and fail (route/retry)
    success, next_step, message = engine.advance()

    if "complete" in message.lower():
        console.print(engine.format_done_result(), markup=False)
        console.print("")
        console.print("[green]Workflow complete![/green]")
    elif success and next_step:
        console.print(engine.format_done_result(), markup=False)
        console.print("")
        console.print(engine.format_current_instruction(), markup=False)
    else:
        # Gates failed, no route matched
        console.print(engine.format_done_result(), markup=False)


@cli.command("workflow-status")
def workflow_status() -> None:
    """Show workflow status."""
    engine = ensure_workflow()
    if not engine:
        return

    console.print(engine.format_status(), markup=False)


@cli.command("list-workflows")
def list_workflows() -> None:
    """List all available workflows."""
    workflows = WorkflowEngine.discover_workflows()

    if not workflows:
        console.print("[yellow]No workflows found.[/yellow]")
        console.print("")
        console.print("Create workflow files in .devflow/workflows/*.toml")
        return

    console.print("[bold]Available Workflows:[/bold]")
    console.print("")

    state = StateStore.from_project()
    current_workflow = state.current_workflow

    for i, (workflow_id, path) in enumerate(workflows, 1):
        marker = "→" if workflow_id == current_workflow else " "
        console.print(f"{marker} {i}. [cyan]{workflow_id}[/cyan]")
        console.print(f"   Path: {path}")
        console.print("")

    console.print("Use [bold]devflow select-workflow <id>[/bold] to choose")


@cli.command("select-workflow")
@click.argument("workflow_id")
def select_workflow(workflow_id: str) -> None:
    """Select and start a workflow.

    Args:
        workflow_id: Workflow ID to select (e.g., MODE-A, MODE-B)
    """
    engine = WorkflowEngine.from_workflow(workflow_id, Path.cwd())

    if not engine:
        console.print(f"[red]Error: Workflow '{workflow_id}' not found.[/red]")
        console.print("")
        console.print("Run [bold]devflow list-workflows[/bold] to see available workflows")
        return

    console.print(f"[green]Selected workflow: {workflow_id}[/green]")
    console.print("")
    console.print(engine.format_current_instruction(), markup=False)


@cli.command()
@click.argument("item")
def approve(item: str) -> None:
    """Mark an item as user-approved.

    Args:
        item: Item to approve (e.g., REQ-001, DESIGN-001)
    """
    state = StateStore.from_project()
    approved_items = state.get("approved_items", [])
    if item not in approved_items:
        approved_items.append(item)
        state.set("approved_items", approved_items)
    console.print(f"[green]Approved: {item}[/green]")


@cli.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str) -> None:
    """Set a state variable.

    Args:
        key: Variable name
        value: Variable value
    """
    state = StateStore.from_project()
    state.set(key, value)
    console.print(f"[green]Set: {key}={value}[/green]")


@cli.command()
def back() -> None:
    """Go back to the previous step."""
    engine = ensure_workflow()
    if not engine:
        return

    success, prev_step, message = engine.go_back()
    if success and prev_step:
        console.print(f"[yellow]{message}[/yellow]")
        console.print("")
        console.print(engine.format_current_instruction(), markup=False)
    else:
        console.print(f"[yellow]{message}[/yellow]")


# ============================================================================
# Ralph Loop Commands
# ============================================================================

@cli.command()
@click.option("--tool", default="local", help="Agent tool to use (local)")
@click.option("--max-iterations", default=10, help="Maximum loop iterations")
@click.pass_context
def run(ctx: click.Context, tool: str, max_iterations: int) -> None:
    """Start the autonomous loop."""
    from devflow.loop_engine import LoopEngine

    project_root = Path.cwd()
    loop = LoopEngine(project_root, tool=tool)
    result = loop.run(max_iterations=max_iterations)

    if result.status == "complete":
        console.print("[green]Workflow complete![/green]")
    elif result.status == "blocked":
        console.print(f"[yellow]Blocked at step: {result.step or 'unknown'}[/yellow]")
        console.print(f"[yellow]{result.message}[/yellow]")
    elif result.status == "max_iterations_reached":
        console.print(f"[yellow]Max iterations reached ({max_iterations})[/yellow]")
        console.print(f"[yellow]Last step: {result.step or 'unknown'}[/yellow]")


@cli.command("loop-status")
def loop_status() -> None:
    """Show loop status and remaining tasks."""
    from devflow.loop_engine import LoopEngine

    project_root = Path.cwd()
    loop = LoopEngine(project_root)
    console.print(loop.status(), markup=False)


@cli.command("sync-backlog")
@click.pass_context
def sync_backlog(ctx: click.Context) -> None:
    """Generate backlog from the current workflow."""
    from devflow.backlog import Backlog

    engine = ensure_workflow()
    if not engine:
        return

    project_root = Path.cwd()
    backlog = Backlog.generate_from_workflow(engine.workflow)
    backlog_path = project_root / ".devflow" / "backlog.json"
    backlog.save(backlog_path)
    console.print(f"[green]Backlog synced: {backlog_path}[/green]")
    console.print(f"[green]Tasks: {len(backlog.tasks)}[/green]")


@cli.command("loop-reset")
def loop_reset() -> None:
    """Reset loop progress (keeps progress.md as history)."""
    from devflow.loop_engine import LoopEngine

    project_root = Path.cwd()
    loop = LoopEngine(project_root)
    loop.reset()
    console.print("[green]Loop progress reset.[/green]")
    console.print("[yellow]Note: progress.md history is preserved.[/yellow]")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
