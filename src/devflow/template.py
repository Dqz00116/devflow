"""Template rendering for DevFlow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from devflow.config import DevFlowConfig


def get_template_dir() -> Path:
    """Get the directory containing templates."""
    # When installed as package
    try:
        import devflow.skills.devflow.templates as templates_pkg
        return Path(templates_pkg.__file__).parent
    except ImportError:
        # During development
        return Path(__file__).parent / "skills" / "devflow" / "templates"


def get_template_env() -> Environment:
    """Get Jinja2 environment for templates."""
    template_dir = get_template_dir()
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template(template_name: str, config: DevFlowConfig, extra_vars: dict[str, Any] | None = None) -> str:
    """Render a template with configuration."""
    env = get_template_env()
    template = env.get_template(template_name)

    context = {
        "project": config.project,
        "commands": config.commands,
        "paths": config.paths,
        "constraints": config.constraints,
        "workflow": config.workflow,
    }

    if extra_vars:
        context.update(extra_vars)

    return template.render(**context)


def copy_template(
    template_name: str,
    dest_path: Path,
    config: DevFlowConfig,
    extra_vars: dict[str, Any] | None = None,
) -> None:
    """Copy and render a template to destination."""
    content = render_template(template_name, config, extra_vars)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(content, encoding="utf-8")


# Template file mapping (template_name -> relative_destination)
PROJECT_TEMPLATES: dict[str, Path] = {
    "WORKFLOW.md": Path("docs") / "WORKFLOW.md",
    "AGENTS.md": Path("AGENTS.md"),
    "REQUIREMENTS.md": Path("docs") / "REQUIREMENTS.md",
    "CLI.md": Path("docs") / "CLI.md",
    "requirements/TEMPLATE.md": Path("docs") / "requirements" / "TEMPLATE.md",
    "features/TEMPLATE.md": Path("docs") / "features" / "TEMPLATE.md",
}


def init_project_templates(project_root: Path, config: DevFlowConfig) -> list[Path]:
    """Initialize all project templates."""
    created_files: list[Path] = []

    for template_name, dest_relative in PROJECT_TEMPLATES.items():
        dest_path = project_root / dest_relative
        if not dest_path.exists():
            copy_template(template_name, dest_path, config)
            created_files.append(dest_path)

    return created_files
