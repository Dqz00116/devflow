"""Template rendering for DevFlow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from devflow.config import DevFlowConfig


def get_template_dir() -> Path:
    """Get the directory containing templates."""
    return Path(__file__).parent / "templates"


def get_template_env() -> Environment:
    """Get Jinja2 environment for templates."""
    template_dir = get_template_dir()
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template(
    template_name: str, config: DevFlowConfig, extra_vars: dict[str, Any] | None = None
) -> str:
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


# v2 templates - only SKILL.md needs Jinja2 rendering
PROJECT_TEMPLATES: dict[str, Path] = {
    "SKILL.md": Path("SKILL.md"),
}


def get_repo_devflow_dir() -> Path | None:
    """Get the .devflow directory from the DevFlow repository itself (if available).

    When running from the DevFlow source repository, __file__ is at
    src/devflow/template.py, so the repo root is 3 parents up.
    """
    candidate = Path(__file__).parent.parent.parent / ".devflow"
    if candidate.exists() and (candidate / "workflows").exists():
        return candidate
    return None


def get_data_dir() -> Path:
    """Get the directory containing bundled workflow/prompt data."""
    return Path(__file__).parent / "data"


def init_project_templates(project_root: Path, config: DevFlowConfig) -> list[Path]:
    """Initialize all project templates and workflow files."""
    created_files: list[Path] = []

    # Render Jinja2 templates
    for template_name, dest_relative in PROJECT_TEMPLATES.items():
        dest_path = project_root / dest_relative
        if not dest_path.exists():
            copy_template(template_name, dest_path, config)
            created_files.append(dest_path)

    # Prefer the DevFlow repository's own .devflow/ as a template
    repo_devflow = get_repo_devflow_dir()
    if repo_devflow:
        workflows_dir = repo_devflow / "workflows"
        prompts_dir = repo_devflow / "prompts"
    else:
        # Fallback to bundled data when installed as a package
        data_dir = get_data_dir()
        workflows_dir = data_dir / "workflows"
        prompts_dir = data_dir / "prompts"

    if workflows_dir.exists():
        for toml_file in workflows_dir.glob("*.toml"):
            dest_path = project_root / ".devflow" / "workflows" / toml_file.name
            if not dest_path.exists():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(toml_file.read_text(encoding="utf-8"), encoding="utf-8")
                created_files.append(dest_path)

    if prompts_dir.exists():
        for md_file in prompts_dir.glob("*.md"):
            dest_path = project_root / ".devflow" / "prompts" / md_file.name
            if not dest_path.exists():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(md_file.read_text(encoding="utf-8"), encoding="utf-8")
                created_files.append(dest_path)

    return created_files
