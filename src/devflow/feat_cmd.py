"""Feature command implementations."""

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
class Feature:
    """Feature data structure."""

    id: str
    title: str
    status: str
    priority: str
    requirement: str
    created: str
    content: str = ""

    @classmethod
    def from_file(cls, file_path: Path) -> Feature | None:
        """Parse feature from markdown file."""
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
            status=frontmatter.get("status", "planned"),
            priority=frontmatter.get("priority", "medium"),
            requirement=frontmatter.get("requirement", ""),
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
requirement: {self.requirement}
created: {self.created}
---

## Description
{self.content if self.content else "<!-- Describe the feature implementation here -->"}

## Implementation

### File Structure
```
<!-- Add file structure -->
```

### Code

```
<!-- Add key code snippets -->
```

## Tests

```
<!-- Add test examples -->
```

## Notes
<!-- Additional implementation notes -->
"""


def get_features_dir(config: DevFlowConfig) -> Path:
    """Get features directory."""
    config_path = Path.cwd() / ".devflow" / "config.toml"
    if config_path.exists():
        return config_path.parent.parent / config.paths.docs / "features"
    return Path.cwd() / config.paths.docs / "features"


def list_features(
    config: DevFlowConfig,
    status_filter: str | None,
    req_filter: str | None,
    console: Console,
) -> None:
    """List all features."""
    feat_dir = get_features_dir(config)

    if not feat_dir.exists():
        console.print(f"[yellow]Features directory not found: {feat_dir}[/yellow]")
        console.print("Run 'devflow init' to initialize the project.")
        return

    # Find all feature files
    feat_files = list(feat_dir.glob("FEAT-*.md"))

    if not feat_files:
        console.print("[yellow]No features found.[/yellow]")
        console.print("Create one with: devflow feat new FEAT-001")
        return

    # Parse features
    features: list[Feature] = []
    for file_path in sorted(feat_files):
        feat = Feature.from_file(file_path)
        if feat:
            if status_filter and feat.status.lower() != status_filter.lower():
                continue
            if req_filter and feat.requirement.upper() != req_filter.upper():
                continue
            features.append(feat)

    # Display as table
    table = Table(title="Features")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Priority", style="yellow")
    table.add_column("Requirement", style="blue")
    table.add_column("Created", style="dim")

    status_colors: dict[str, str] = {
        "planned": "dim",
        "in_progress": "blue",
        "implemented": "green",
        "testing": "yellow",
        "done": "bright_green",
    }

    priority_colors: dict[str, str] = {
        "low": "dim",
        "medium": "white",
        "high": "yellow",
        "critical": "red",
    }

    for feat in features:
        status_color = status_colors.get(feat.status.lower(), "white")
        priority_color = priority_colors.get(feat.priority.lower(), "white")

        table.add_row(
            feat.id,
            feat.title,
            f"[{status_color}]{feat.status}[/{status_color}]",
            f"[{priority_color}]{feat.priority}[/{priority_color}]",
            feat.requirement,
            feat.created,
        )

    console.print(table)
    console.print(f"\nTotal: {len(features)} features")


def create_feature(
    config: DevFlowConfig,
    feat_id: str,
    title: str,
    requirement: str,
    priority: str,
    console: Console,
) -> None:
    """Create a new feature."""
    feat_dir = get_features_dir(config)
    feat_dir.mkdir(parents=True, exist_ok=True)

    # Validate ID format
    if not re.match(r"^FEAT-\d+$", feat_id.upper()):
        console.print(f"[red]Invalid feature ID: {feat_id}[/red]")
        console.print("Feature ID must be in format: FEAT-001, FEAT-002, etc.")
        return

    feat_id = feat_id.upper()
    file_path = feat_dir / f"{feat_id}.md"

    if file_path.exists():
        console.print(f"[yellow]Feature {feat_id} already exists: {file_path}[/yellow]")
        return

    # Create feature
    feat = Feature(
        id=feat_id,
        title=title,
        status="planned",
        priority=priority,
        requirement=requirement.upper(),
        created=datetime.now().strftime("%Y-%m-%d"),
    )

    file_path.write_text(feat.to_markdown(), encoding="utf-8")

    console.print(f"[green]✓[/green] Created feature: {feat_id}")
    console.print(f"  Edit: {file_path}")


def show_feature(
    config: DevFlowConfig,
    feat_id: str,
    console: Console,
) -> None:
    """Show feature details."""
    feat_dir = get_features_dir(config)
    file_path = feat_dir / f"{feat_id.upper()}.md"

    feat = Feature.from_file(file_path)
    if not feat:
        console.print(f"[red]Feature not found: {feat_id}[/red]")
        return

    console.print(f"\n[bold cyan]{feat.id}:[/bold cyan] {feat.title}")
    console.print(f"Status: {feat.status}")
    console.print(f"Priority: {feat.priority}")
    console.print(f"Requirement: {feat.requirement}")
    console.print(f"Created: {feat.created}")
    console.print(f"\n{feat.content[:500]}..." if len(feat.content) > 500 else f"\n{feat.content}")


def update_feature_status(
    config: DevFlowConfig,
    feat_id: str,
    new_status: str,
    console: Console,
) -> None:
    """Update feature status."""
    feat_dir = get_features_dir(config)
    file_path = feat_dir / f"{feat_id.upper()}.md"

    if not file_path.exists():
        console.print(f"[red]Feature not found: {feat_id}[/red]")
        return

    # Read and update
    content = file_path.read_text(encoding="utf-8")

    # Simple string replacement for status
    old_pattern = r"status:\s*\w+"
    new_line = f"status: {new_status.lower()}"

    if re.search(old_pattern, content):
        content = re.sub(old_pattern, new_line, content)
        file_path.write_text(content, encoding="utf-8")
        console.print(f"[green]✓[/green] Updated {feat_id} status to: {new_status}")
    else:
        console.print(f"[red]Could not update status in {file_path}[/red]")
