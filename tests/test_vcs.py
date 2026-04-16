"""Tests for vcs module — VCS abstraction and checkpoint generation."""

import subprocess
from pathlib import Path

import pytest

from devflow.vcs import GitDriver, NoVCSDriver, detect_vcs


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Initialize a temporary Git repository."""
    repo = tmp_path / "git_repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "file.txt").write_text("hello")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


class TestGitDriver:
    def test_is_available(self, git_repo: Path) -> None:
        driver = GitDriver(git_repo)
        assert driver.is_available() is True

    def test_has_uncommitted_changes_true(self, git_repo: Path) -> None:
        driver = GitDriver(git_repo)
        (git_repo / "file.txt").write_text("modified")
        assert driver.has_uncommitted_changes() is True

    def test_has_uncommitted_changes_false(self, git_repo: Path) -> None:
        driver = GitDriver(git_repo)
        assert driver.has_uncommitted_changes() is False

    def test_get_diff_text(self, git_repo: Path) -> None:
        driver = GitDriver(git_repo)
        (git_repo / "file.txt").write_text("modified")
        diff = driver.get_diff_text()
        assert "modified" in diff

    def test_save_checkpoint(self, git_repo: Path) -> None:
        driver = GitDriver(git_repo)
        (git_repo / "file.txt").write_text("modified")
        path = driver.save_checkpoint("test-step")
        assert path is not None
        assert path.suffix == ".diff"
        assert "CHECKPOINT-test-step" in path.name
        content = path.read_text(encoding="utf-8")
        assert "modified" in content


class TestNoVCSDriver:
    def test_is_available(self, tmp_path: Path) -> None:
        driver = NoVCSDriver(tmp_path)
        assert driver.is_available() is True

    def test_save_checkpoint(self, tmp_path: Path) -> None:
        driver = NoVCSDriver(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        path = driver.save_checkpoint("test-step")
        assert path is not None
        assert (path / "src" / "main.py").exists()
        assert (path / "src" / "main.py").read_text() == "print('hello')"


class TestDetectVCS:
    def test_detects_git(self, git_repo: Path) -> None:
        driver = detect_vcs(git_repo)
        assert isinstance(driver, GitDriver)

    def test_falls_back_to_no_vcs(self, tmp_path: Path) -> None:
        driver = detect_vcs(tmp_path)
        assert isinstance(driver, NoVCSDriver)
