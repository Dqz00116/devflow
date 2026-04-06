"""Main CLI entry point for DevFlow."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from devflow import __version__
from devflow.config import DevFlowConfig

console = Console()


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
    """Manage requirements."""
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
    """Manage tasks."""
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
    """Manage features."""
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

    # Check required files
    project_root = config_path.parent.parent
    required_files = [
        project_root / "docs" / "WORKFLOW.md",
        project_root / "AGENTS.md",
        project_root / "docs" / "REQUIREMENTS.md",
    ]

    all_valid = True
    for file_path in required_files:
        if file_path.exists():
            console.print(f"[green]✓[/green] {file_path.name}")
        else:
            console.print(f"[red]✗[/red] {file_path.name} (missing)")
            all_valid = False

    if all_valid:
        console.print("\n[green]All validations passed![/green]")
    else:
        console.print("\n[yellow]Some files are missing. Run 'devflow init' to create them.[/yellow]")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
