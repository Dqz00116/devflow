"""Initialize command implementation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.panel import Panel

from devflow.config import DevFlowConfig, get_preset
from devflow.template import init_project_templates

if TYPE_CHECKING:
    from rich.console import Console


def init_project(
    config: DevFlowConfig,
    language: str,
    name: str,
    force: bool,
    console: Console,
) -> None:
    """Initialize a new DevFlow project."""
    project_root = Path.cwd()
    devflow_dir = project_root / ".devflow"
    config_path = devflow_dir / "config.toml"

    # Check if already initialized
    if config_path.exists() and not force:
        console.print(f"[yellow]Project already initialized at {config_path}[/yellow]")
        console.print("Use --force to overwrite.")
        return

    # Update config
    config.project.name = name
    config.project.language = language

    # Apply preset for the language
    if language != "other":
        preset = get_preset(language)
        if "commands" in preset:
            for key, value in preset["commands"].items():
                if value:
                    setattr(config.commands, key, value)
        if "paths" in preset:
            for key, value in preset["paths"].items():
                if value:
                    setattr(config.paths, key, value)
        if "constraints" in preset:
            for key, value in preset["constraints"].items():
                setattr(config.constraints, key, value)

    # Set default stack description
    default_stacks: dict[str, str] = {
        "python": "Python 3.x",
        "javascript": "Node.js + JavaScript",
        "typescript": "Node.js + TypeScript",
        "go": "Go",
        "rust": "Rust",
        "dotnet": ".NET",
        "other": "Custom Stack",
    }
    config.project.stack = default_stacks.get(language, "Custom Stack")

    # Create directories
    dirs_to_create = [
        devflow_dir,
        project_root / config.paths.docs,
        project_root / config.paths.docs / "requirements",
        project_root / config.paths.docs / "features",
        project_root / config.paths.docs / "superpowers" / "specs",
        project_root / config.paths.docs / "superpowers" / "plans",
        project_root / config.paths.src,
        project_root / config.paths.tests,
    ]

    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Save configuration
    config.save(config_path)

    # Create templates
    created_files = init_project_templates(project_root, config)

    # Display summary
    console.print()
    console.print(Panel.fit(
        f"[green]✓[/green] Initialized DevFlow project: [bold]{name}[/bold]\n"
        f"[green]✓[/green] Language: {language}\n"
        f"[green]✓[/green] Config: {config_path}",
        title="DevFlow Initialization",
        border_style="green",
    ))

    if created_files:
        console.print("\n[bold]Created files:[/bold]")
        for file_path in created_files:
            console.print(f"  [green]✓[/green] {file_path.relative_to(project_root)}")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Review and customize AGENTS.md")
    console.print("  2. Create your first requirement: devflow req new REQ-001")
    console.print("  3. Follow the workflow in docs/WORKFLOW.md")
