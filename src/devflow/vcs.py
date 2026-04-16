"""VCS abstraction layer for DevFlow checkpointing."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class VCSDriver(ABC):
    """Abstract base class for version control drivers."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def has_uncommitted_changes(self) -> bool: ...

    @abstractmethod
    def get_diff_text(self) -> str:
        """Return diff text for current changes."""
        ...

    @abstractmethod
    def save_checkpoint(self, tag: str) -> Path | None:
        """Save a checkpoint and return the path to the artifact."""
        ...


class GitDriver(VCSDriver):
    """Git VCS driver: generates .diff files instead of committing."""

    def is_available(self) -> bool:
        return (self.project_root / ".git").exists()

    def has_uncommitted_changes(self) -> bool:
        if not self.is_available():
            return False
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode == 0 and bool(result.stdout.strip())

    def get_diff_text(self) -> str:
        if not self.is_available():
            return ""
        result = subprocess.run(
            ["git", "diff"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return result.stdout
        return ""

    def _get_short_sha(self) -> str | None:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
        return None

    def save_checkpoint(self, tag: str) -> Path | None:
        diff_text = self.get_diff_text()
        if not diff_text:
            return None

        sha = self._get_short_sha()
        suffix = f"-{sha}" if sha else ""
        checkpoints_dir = self.project_root / ".devflow" / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        path = checkpoints_dir / f"CHECKPOINT-{tag}{suffix}.diff"
        path.write_text(diff_text, encoding="utf-8")
        return path


class NoVCSDriver(VCSDriver):
    """Fallback driver when no VCS is present: snapshots modified files."""

    def is_available(self) -> bool:
        return True

    def has_uncommitted_changes(self) -> bool:
        # Naive heuristic: any files under src/ or tests/ changed since last checkpoint?
        # For simplicity, always return True so LoopEngine can decide.
        return True

    def _collect_files(self) -> dict[Path, str]:
        """Collect files in project root that look like source code."""
        files: dict[Path, str] = {}
        for pattern in ["src/**/*", "tests/**/*", "docs/**/*", "*.py", "*.md", "*.toml"]:
            for fp in self.project_root.glob(pattern):
                if fp.is_file():
                    try:
                        files[fp.relative_to(self.project_root)] = fp.read_text(encoding="utf-8")
                    except Exception:
                        pass
        return files

    def get_diff_text(self) -> str:
        files = self._collect_files()
        lines = [
            f"--- {p.as_posix()}\n+++ {p.as_posix()}\n{content[:200]}"
            for p, content in files.items()
        ]
        return "\n".join(lines)

    def save_checkpoint(self, tag: str) -> Path | None:
        files = self._collect_files()
        if not files:
            return None

        checkpoints_dir = self.project_root / ".devflow" / "checkpoints"
        checkpoint_dir = checkpoints_dir / f"CHECKPOINT-{tag}"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        for rel_path, content in files.items():
            dest = checkpoint_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        return checkpoint_dir


def detect_vcs(project_root: Path) -> VCSDriver:
    """Auto-detect VCS and return appropriate driver."""
    git = GitDriver(project_root)
    if git.is_available():
        return git
    return NoVCSDriver(project_root)
