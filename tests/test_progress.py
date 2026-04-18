"""Tests for progress module — append-only logging and summary."""

from pathlib import Path

from devflow.progress import ProgressLogger


class TestProgressLogger:
    def test_log_creates_file(self, tmp_path: Path) -> None:
        logger = ProgressLogger(tmp_path)
        logger.log("step-1 completed")
        assert logger.progress_path.exists()
        content = logger.progress_path.read_text(encoding="utf-8")
        assert "step-1 completed" in content

    def test_log_appends(self, tmp_path: Path) -> None:
        logger = ProgressLogger(tmp_path)
        logger.log("entry-1")
        logger.log("entry-2")
        content = logger.progress_path.read_text(encoding="utf-8")
        assert content.count("## ") == 2
        assert "entry-1" in content
        assert "entry-2" in content

    def test_recent_summary(self, tmp_path: Path) -> None:
        logger = ProgressLogger(tmp_path)
        logger.log("entry-1")
        logger.log("entry-2")
        logger.log("entry-3")
        summary = logger.recent_summary(n=2)
        assert "entry-2" in summary
        assert "entry-3" in summary
        assert "entry-1" not in summary

    def test_recent_summary_empty(self, tmp_path: Path) -> None:
        logger = ProgressLogger(tmp_path)
        assert logger.recent_summary(n=3) == ""
