"""Requirement command implementations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.table import Table

if TYPE_CHECKING:
    from rich.console import Console

    from devflow.config import DevFlowConfig


@dataclass
class Requirement:
    """Requirement data structure."""

    id: str
    title: str
    status: str
    priority: str
    created: str
    content: str = ""

    @classmethod
    def from_file(cls, file_path: Path) -> Requirement | None:
        """Parse requirement from markdown file."""
        if not file_path.exists():
            return None

        content = file_path.read_text(encoding="utf-8")

        # Parse frontmatter
        frontmatter: dict[str, str] = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1].strip()
                for line in fm_text.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        frontmatter[key.strip()] = value.strip().strip('"')
                content = parts[2].strip()

        return cls(
            id=frontmatter.get("id", file_path.stem),
            title=frontmatter.get("title", "Untitled"),
            status=frontmatter.get("status", "draft"),
            priority=frontmatter.get("priority", "medium"),
            created=frontmatter.get("created", ""),
            content=content,
        )

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        return f"""---
id: {self.id}
title: {self.title}
status: {self.status}
priority: {self.priority}
created: {self.created}
---

## Description
{self.content if self.content else "<!-- Describe the requirement here -->"}

## Acceptance Criteria
- [ ] <!-- Add acceptance criteria -->

## Design Document
<!-- Link to design document when created -->
- Design: `docs/superpowers/specs/YYYY-MM-DD-{self.id.lower()}-design.md`

## Tasks
<!-- Tasks will be linked here -->

## Notes
<!-- Additional notes -->
"""


def get_requirements_dir(config: DevFlowConfig) -> Path:
    """Get requirements directory."""
    config_path = Path.cwd() / ".devflow" / "config.toml"
    if config_path.exists():
        return config_path.parent.parent / config.paths.docs / "requirements"
    return Path.cwd() / config.paths.docs / "requirements"


def list_requirements(
    config: DevFlowConfig,
    status_filter: str | None,
    console: Console,
) -> None:
    """List all requirements."""
    req_dir = get_requirements_dir(config)

    if not req_dir.exists():
        console.print(f"[yellow]Requirements directory not found: {req_dir}[/yellow]")
        console.print("Run 'devflow init' to initialize the project.")
        return

    # Find all requirement files
    req_files = list(req_dir.glob("REQ-*.md"))

    if not req_files:
        console.print("[yellow]No requirements found.[/yellow]")
        console.print("Create one with: devflow req new REQ-001")
        return

    # Parse requirements
    requirements: list[Requirement] = []
    for file_path in sorted(req_files):
        req = Requirement.from_file(file_path)
        if req:
            if status_filter and req.status.lower() != status_filter.lower():
                continue
            requirements.append(req)

    # Display as table
    table = Table(title="Requirements")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Priority", style="yellow")
    table.add_column("Created", style="dim")

    status_colors: dict[str, str] = {
        "draft": "dim",
        "analyzing": "blue",
        "analyzed": "cyan",
        "approved": "green",
        "in_progress": "yellow",
        "done": "bright_green",
    }

    priority_colors: dict[str, str] = {
        "low": "dim",
        "medium": "white",
        "high": "yellow",
        "critical": "red",
    }

    for req in requirements:
        status_color = status_colors.get(req.status.lower(), "white")
        priority_color = priority_colors.get(req.priority.lower(), "white")

        table.add_row(
            req.id,
            req.title,
            f"[{status_color}]{req.status}[/{status_color}]",
            f"[{priority_color}]{req.priority}[/{priority_color}]",
            req.created,
        )

    console.print(table)
    console.print(f"\nTotal: {len(requirements)} requirements")


def create_requirement(
    config: DevFlowConfig,
    req_id: str,
    title: str,
    priority: str,
    console: Console,
) -> None:
    """Create a new requirement."""
    req_dir = get_requirements_dir(config)
    req_dir.mkdir(parents=True, exist_ok=True)

    # Validate ID format
    if not re.match(r"^REQ-\d+$", req_id.upper()):
        console.print(f"[red]Invalid requirement ID: {req_id}[/red]")
        console.print("Requirement ID must be in format: REQ-001, REQ-002, etc.")
        return

    req_id = req_id.upper()
    file_path = req_dir / f"{req_id}.md"

    if file_path.exists():
        console.print(f"[yellow]Requirement {req_id} already exists: {file_path}[/yellow]")
        return

    # Create requirement
    req = Requirement(
        id=req_id,
        title=title,
        status="draft",
        priority=priority,
        created=datetime.now().strftime("%Y-%m-%d"),
    )

    file_path.write_text(req.to_markdown(), encoding="utf-8")

    console.print(f"[green]✓[/green] Created requirement: {req_id}")
    console.print(f"  Edit: {file_path}")


def show_requirement(
    config: DevFlowConfig,
    req_id: str,
    console: Console,
) -> None:
    """Show requirement details."""
    req_dir = get_requirements_dir(config)
    file_path = req_dir / f"{req_id.upper()}.md"

    req = Requirement.from_file(file_path)
    if not req:
        console.print(f"[red]Requirement not found: {req_id}[/red]")
        return

    console.print(f"\n[bold cyan]{req.id}:[/bold cyan] {req.title}")
    console.print(f"Status: {req.status}")
    console.print(f"Priority: {req.priority}")
    console.print(f"Created: {req.created}")
    console.print(f"\n{req.content}")


def update_requirement_status(
    config: DevFlowConfig,
    req_id: str,
    new_status: str,
    console: Console,
) -> None:
    """Update requirement status."""
    req_dir = get_requirements_dir(config)
    file_path = req_dir / f"{req_id.upper()}.md"

    if not file_path.exists():
        console.print(f"[red]Requirement not found: {req_id}[/red]")
        return

    # Read and update
    content = file_path.read_text(encoding="utf-8")

    # Simple string replacement for status
    old_pattern = r"status:\s*\w+"
    new_line = f"status: {new_status.lower()}"

    if re.search(old_pattern, content):
        content = re.sub(old_pattern, new_line, content)
        file_path.write_text(content, encoding="utf-8")
        console.print(f"[green]✓[/green] Updated {req_id} status to: {new_status}")
    else:
        console.print(f"[red]Could not update status in {file_path}[/red]")
