"""Local agent runner for LoopEngine subprocess mode.

Reads a prompt from stdin, prints it back to stdout, and exits.
This serves as the subprocess boundary for --tool local in Phase 1 MVP.
Future iterations can replace this with structured action parsing or
external CLI invocation.
"""

from __future__ import annotations

import sys


def main() -> None:
    """Run the local agent."""
    prompt = sys.stdin.read()
    # Phase 1 MVP: echo the prompt back so the caller can inspect it.
    # The actual step execution is expected to happen before/after spawning
    # or via a more sophisticated agent protocol in later phases.
    sys.stdout.write(prompt)
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
