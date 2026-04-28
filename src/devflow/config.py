"""Configuration management for DevFlow."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml


@dataclass
class ProjectConfig:
    """Project-level configuration."""

    name: str = ""
    language: str = "python"
    stack: str = ""
    version: str = "0.1.6"


@dataclass
class CommandConfig:
    """Command configuration for the project."""

    build: str = ""
    test: str = ""
    lint: str = ""
    test_unit: str = ""
    test_integration: str = ""


@dataclass
class PathConfig:
    """Path configuration for the project."""

    src: str = "src"
    tests: str = "tests"
    docs: str = "docs"


@dataclass
class ConstraintConfig:
    """Project constraints configuration."""

    zero_warnings: bool = True
    zero_mocks: bool = False
    nullable: bool = True


@dataclass
class WorkflowConfig:
    """Workflow configuration."""

    stages: list[str] = field(
        default_factory=lambda: [
            "backlog",
            "analyzing",
            "analyzed",
            "approved",
            "in_progress",
            "done",
        ]
    )


@dataclass
class DevFlowConfig:
    """Main configuration class for DevFlow."""

    project: ProjectConfig = field(default_factory=ProjectConfig)
    commands: CommandConfig = field(default_factory=CommandConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    constraints: ConstraintConfig = field(default_factory=ConstraintConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)

    @classmethod
    def load(cls, path: Path | None = None) -> DevFlowConfig:
        """Load configuration from TOML file."""
        if path is None:
            path = cls.find_config()

        if not path.exists():
            return cls()

        data = toml.load(path)
        return cls._from_dict(data)

    @classmethod
    def load_global(cls) -> DevFlowConfig:
        """Load global configuration."""
        global_path = cls.global_config_path()
        if global_path.exists():
            data = toml.load(global_path)
            return cls._from_dict(data)
        return cls()

    @classmethod
    def find_config(cls) -> Path:
        """Find the nearest devflow.toml configuration file."""
        cwd = Path.cwd()
        for path in [cwd, *cwd.parents]:
            config_path = path / ".devflow" / "config.toml"
            if config_path.exists():
                return config_path
        return cwd / ".devflow" / "config.toml"

    @staticmethod
    def global_config_path() -> Path:
        """Get the path to the global configuration file."""
        system = platform.system()
        if system == "Windows":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif system == "Darwin":
            base = Path.home() / "Library" / "Application Support"
        else:  # Linux and other Unix
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "devflow" / "config.toml"

    def save(self, path: Path | None = None) -> None:
        """Save configuration to TOML file."""
        if path is None:
            path = self.find_config()

        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._to_dict()
        with open(path, "w", encoding="utf-8") as f:
            toml.dump(data, f)

    def save_global(self) -> None:
        """Save configuration to global config file."""
        global_path = self.global_config_path()
        global_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._to_dict()
        with open(global_path, "w", encoding="utf-8") as f:
            toml.dump(data, f)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return self._to_dict()

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> DevFlowConfig:
        """Create configuration from dictionary."""
        config = cls()

        if "project" in data:
            config.project = ProjectConfig(**data["project"])
        if "commands" in data:
            config.commands = CommandConfig(**data["commands"])
        if "paths" in data:
            config.paths = PathConfig(**data["paths"])
        if "constraints" in data:
            config.constraints = ConstraintConfig(**data["constraints"])
        if "workflow" in data:
            workflow_data = data["workflow"].copy()
            if "stages" in workflow_data:
                config.workflow = WorkflowConfig(stages=workflow_data["stages"])
            else:
                config.workflow = WorkflowConfig()

        return config

    def _to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "project": {
                "name": self.project.name,
                "language": self.project.language,
                "stack": self.project.stack,
                "version": self.project.version,
            },
            "commands": {
                "build": self.commands.build,
                "test": self.commands.test,
                "lint": self.commands.lint,
                "test_unit": self.commands.test_unit,
                "test_integration": self.commands.test_integration,
            },
            "paths": {
                "src": self.paths.src,
                "tests": self.paths.tests,
                "docs": self.paths.docs,
            },
            "constraints": {
                "zero_warnings": self.constraints.zero_warnings,
                "zero_mocks": self.constraints.zero_mocks,
                "nullable": self.constraints.nullable,
            },
            "workflow": {
                "stages": self.workflow.stages,
            },
        }


# Preset configurations for common languages
LANGUAGE_PRESETS: dict[str, dict[str, Any]] = {
    "python": {
        "commands": {
            "build": "python -m build",
            "test": "pytest",
            "lint": "ruff check .",
            "test_unit": "pytest tests/unit -v",
            "test_integration": "pytest tests/integration -v",
        },
        "paths": {
            "src": "src",
            "tests": "tests",
            "docs": "docs",
        },
        "constraints": {
            "zero_warnings": True,
            "zero_mocks": False,
            "nullable": True,
        },
    },
    "javascript": {
        "commands": {
            "build": "npm run build",
            "test": "npm test",
            "lint": "npm run lint",
            "test_unit": "npm run test:unit",
            "test_integration": "npm run test:integration",
        },
        "paths": {
            "src": "src",
            "tests": "tests",
            "docs": "docs",
        },
        "constraints": {
            "zero_warnings": True,
            "zero_mocks": False,
            "nullable": False,
        },
    },
    "typescript": {
        "commands": {
            "build": "npm run build",
            "test": "npm test",
            "lint": "npm run lint",
            "test_unit": "npm run test:unit",
            "test_integration": "npm run test:integration",
        },
        "paths": {
            "src": "src",
            "tests": "tests",
            "docs": "docs",
        },
        "constraints": {
            "zero_warnings": True,
            "zero_mocks": False,
            "nullable": True,
        },
    },
    "go": {
        "commands": {
            "build": "go build ./...",
            "test": "go test ./...",
            "lint": "golangci-lint run",
            "test_unit": "go test -short ./...",
            "test_integration": "go test -run Integration ./...",
        },
        "paths": {
            "src": ".",
            "tests": ".",
            "docs": "docs",
        },
        "constraints": {
            "zero_warnings": True,
            "zero_mocks": False,
            "nullable": False,
        },
    },
    "rust": {
        "commands": {
            "build": "cargo build --release",
            "test": "cargo test",
            "lint": "cargo clippy",
            "test_unit": "cargo test --lib",
            "test_integration": "cargo test --test integration",
        },
        "paths": {
            "src": "src",
            "tests": "tests",
            "docs": "docs",
        },
        "constraints": {
            "zero_warnings": True,
            "zero_mocks": False,
            "nullable": False,
        },
    },
    "dotnet": {
        "commands": {
            "build": "dotnet build",
            "test": "dotnet test",
            "lint": "dotnet format --verify-no-changes",
            "test_unit": "dotnet test tests/Unit",
            "test_integration": "dotnet test tests/Integration",
        },
        "paths": {
            "src": "src",
            "tests": "tests",
            "docs": "docs",
        },
        "constraints": {
            "zero_warnings": True,
            "zero_mocks": True,
            "nullable": True,
        },
    },
}


def get_preset(language: str) -> dict[str, Any]:
    """Get preset configuration for a language."""
    return LANGUAGE_PRESETS.get(language, LANGUAGE_PRESETS["python"]).copy()
