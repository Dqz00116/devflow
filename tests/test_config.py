"""Tests for config module."""

import tempfile
from pathlib import Path

import pytest

from devflow.config import CommandConfig, DevFlowConfig, ProjectConfig, get_preset


class TestProjectConfig:
    """Test ProjectConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ProjectConfig()
        assert config.name == ""
        assert config.language == "python"
        assert config.stack == ""
        assert config.version == "0.1.0"


class TestDevFlowConfig:
    """Test DevFlowConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = DevFlowConfig()
        assert config.project.language == "python"
        assert config.commands.build == ""
        assert config.paths.src == "src"

    def test_save_and_load(self) -> None:
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            # Create and save config
            config = DevFlowConfig()
            config.project.name = "test-project"
            config.project.language = "python"
            config.commands.test = "pytest"
            config.save(config_path)

            # Load config
            loaded = DevFlowConfig.load(config_path)
            assert loaded.project.name == "test-project"
            assert loaded.project.language == "python"
            assert loaded.commands.test == "pytest"

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        config = DevFlowConfig()
        config.project.name = "test"
        data = config.to_dict()

        assert data["project"]["name"] == "test"
        assert "commands" in data
        assert "paths" in data


class TestLanguagePresets:
    """Test language presets."""

    def test_python_preset(self) -> None:
        """Test Python preset."""
        preset = get_preset("python")
        assert "commands" in preset
        assert preset["commands"]["test"] == "pytest"

    def test_javascript_preset(self) -> None:
        """Test JavaScript preset."""
        preset = get_preset("javascript")
        assert preset["commands"]["build"] == "npm run build"

    def test_go_preset(self) -> None:
        """Test Go preset."""
        preset = get_preset("go")
        assert preset["commands"]["build"] == "go build ./..."

    def test_unknown_preset_defaults_to_python(self) -> None:
        """Test unknown language defaults to Python."""
        preset = get_preset("unknown")
        assert preset["commands"]["test"] == "pytest"
