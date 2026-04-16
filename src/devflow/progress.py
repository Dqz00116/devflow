"""Progress logging for Ralph Loop integration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class ProgressLogger:
    """Append-only progress logger for loop iterations."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.progress_path = project_root / ".devflow" / "progress.md"

    def log(self, message: str) -> None:
        """Append a progress entry."""
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        entry = f"## {timestamp} — {message}\n\n"
        with self.progress_path.open("a", encoding="utf-8") as f:
            f.write(entry)

    def recent_summary(self, n: int = 5) -> str:
        """Return the last n progress entries as a single string."""
        if not self.progress_path.exists():
            return ""

        content = self.progress_path.read_text(encoding="utf-8")
        # Split by "## " headers, but keep the markers
        raw_entries = [e.strip() for e in content.split("## ") if e.strip()]
        entries = [f"## {e}" for e in raw_entries]
        recent = entries[-n:] if entries else []
        return "\n\n".join(recent)
