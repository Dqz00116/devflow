"""Tests for agent_runner module — subprocess invocation."""

import os
import subprocess
import sys
from pathlib import Path


class TestAgentRunner:
    def test_echoes_prompt(self, tmp_path: Path) -> None:
        prompt = "Hello from test"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        result = subprocess.run(
            [sys.executable, "-m", "devflow.agent_runner"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(tmp_path),
            env=env,
        )
        assert result.returncode == 0
        assert prompt in result.stdout
