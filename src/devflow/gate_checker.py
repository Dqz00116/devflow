"""Gate checking for workflow step advancement."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devflow.state_store import StateStore


def resolve_variables(text: str, state: StateStore) -> str:
    """Resolve state variables in text.

    Args:
        text: Text containing {var_name} placeholders
        state: State store for variable lookup

    Returns:
        Text with variables resolved
    """
    import re

    def replace_var(match: re.Match) -> str:
        var_name = match.group(1)
        value = state.get(var_name)
        return str(value) if value is not None else match.group(0)

    return re.sub(r'\{(\w+)\}', replace_var, text)


def check_file_exists(path_str: str, project_root: Path, state: StateStore | None = None) -> tuple[bool, str]:
    """Check if file exists.

    Args:
        path_str: Relative path from project root
        project_root: Project root directory
        state: Optional state store for variable resolution

    Returns:
        (is_passed, message)
    """
    if state:
        path_str = resolve_variables(path_str, state)

    file_path = project_root / path_str
    if file_path.exists():
        return True, f"File exists: {path_str}"
    return False, f"File not found: {path_str}"


def check_file_exists_pattern(pattern: str, project_root: Path) -> tuple[bool, str]:
    """Check if any file matching pattern exists.

    Args:
        pattern: Glob pattern (e.g., "docs/requirements/REQ-*.md")
        project_root: Project root directory

    Returns:
        (is_passed, message)
    """
    files = list(project_root.glob(pattern))
    if files:
        return True, f"Found {len(files)} file(s) matching: {pattern}"
    return False, f"No files match pattern: {pattern}"


def check_file_contains(path_str: str, content: str, project_root: Path, state: StateStore | None = None) -> tuple[bool, str]:
    """Check if file contains specific content.

    Args:
        path_str: Relative path from project root
        content: Content to search for
        project_root: Project root directory
        state: Optional state store for variable resolution

    Returns:
        (is_passed, message)
    """
    if state:
        path_str = resolve_variables(path_str, state)
        content = resolve_variables(content, state)

    file_path = project_root / path_str
    if not file_path.exists():
        return False, f"File not found: {path_str}"

    try:
        file_content = file_path.read_text(encoding="utf-8")
        if content in file_content:
            return True, f"File contains: {content}"
        return False, f"File missing content: {content}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def check_file_contains_pattern(pattern: str, content: str, project_root: Path) -> tuple[bool, str]:
    """Check if any file matching pattern contains specific content.

    Args:
        pattern: Glob pattern (e.g., "docs/requirements/REQ-*.md")
        content: Content to search for
        project_root: Project root directory

    Returns:
        (is_passed, message)
    """
    files = list(project_root.glob(pattern))
    if not files:
        return False, f"No files match pattern: {pattern}"

    for file_path in files:
        try:
            file_content = file_path.read_text(encoding="utf-8")
            if content in file_content:
                rel_path = file_path.relative_to(project_root)
                return True, f"File {rel_path} contains: {content}"
        except Exception:
            continue

    return False, f"No matching file contains: {content}"


def check_user_approved(item: str, state: StateStore) -> tuple[bool, str]:
    """Check if item is user-approved.

    Args:
        item: Item to check (e.g., "REQ-001")
        state: State store

    Returns:
        (is_passed, message)
    """
    approved_items = state.get("approved_items", [])
    if item in approved_items:
        return True, f"User approved: {item}"
    return False, f"Not user-approved: {item} (run: devflow approve {item})"


def check_command_success(command: str, project_root: Path) -> tuple[bool, str]:
    """Check if command exits successfully.

    WARNING: This executes arbitrary shell commands from workflow TOML files.
    Only use with trusted workflow definitions. Do not load workflows from
    untrusted sources, as they could contain malicious commands.

    Args:
        command: Command to run
        project_root: Project root directory

    Returns:
        (is_passed, message)
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return True, f"Command succeeded: {command}"
        return False, f"Command failed: {command}"
    except subprocess.TimeoutExpired:
        return False, f"Command timed out: {command}"
    except Exception as e:
        return False, f"Command error: {command} - {e}"


def check_state_set(var_name: str, state: StateStore) -> tuple[bool, str]:
    """Check if state variable is set.

    Args:
        var_name: Variable name to check
        state: State store

    Returns:
        (is_passed, message)
    """
    value = state.get(var_name)
    if value is not None and value != "":
        return True, f"State variable set: {var_name}={value}"
    return False, f"State variable not set: {var_name} (run: devflow set {var_name} <value>)"


def check_gate(gate: str, project_root: Path, state: StateStore) -> tuple[bool, str]:
    """Check a single gate condition.

    Args:
        gate: Gate condition string (e.g., "file_exists:docs/REQ.md")
        project_root: Project root directory
        state: State store

    Returns:
        (is_passed, message)
    """
    # Check for unresolved variables - if a variable like {test_command} is not
    # set in state, the gate cannot be evaluated properly
    import re

    unresolved = re.findall(r'\{(\w+)\}', gate)
    if unresolved:
        missing = []
        for var in unresolved:
            if state.get(var) is None:
                missing.append(var)
        if missing:
            return False, f"Unresolved variable(s): {', '.join(missing)} (set in .devflow/config.toml)"

    # file_exists with variable support
    if gate.startswith("file_exists:"):
        path = gate[len("file_exists:"):]
        return check_file_exists(path, project_root, state)

    # file_exists_pattern with glob support
    if gate.startswith("file_exists_pattern:"):
        pattern = gate[len("file_exists_pattern:"):]
        return check_file_exists_pattern(pattern, project_root)

    # file_contains with variable support
    if gate.startswith("file_contains:"):
        rest = gate[len("file_contains:"):]
        if ":" in rest:
            path, content = rest.split(":", 1)
            return check_file_contains(path, content, project_root, state)
        return False, f"Invalid file_contains gate: {gate}"

    # file_contains_pattern with glob support
    if gate.startswith("file_contains_pattern:"):
        rest = gate[len("file_contains_pattern:"):]
        if ":" in rest:
            pattern, content = rest.split(":", 1)
            return check_file_contains_pattern(pattern, content, project_root)
        return False, f"Invalid file_contains_pattern gate: {gate}"

    if gate.startswith("user_approved:"):
        item = gate[len("user_approved:"):]
        # Support variable in approval item
        item = resolve_variables(item, state)
        return check_user_approved(item, state)

    if gate.startswith("command_success:"):
        command = gate[len("command_success:"):]
        return check_command_success(command, project_root)

    if gate.startswith("state_set:"):
        var_name = gate[len("state_set:"):]
        return check_state_set(var_name, state)

    # Unknown gate type, pass with warning
    return True, f"Unknown gate (skipped): {gate}"


def check_all_gates(
    gates: list[str], project_root: Path, state: StateStore
) -> tuple[bool, list[tuple[bool, str]]]:
    """Check all gate conditions.

    Args:
        gates: List of gate condition strings
        project_root: Project root directory
        state: State store

    Returns:
        (all_passed, list of (is_passed, message))
    """
    results = []
    all_passed = True

    for gate in gates:
        is_passed, message = check_gate(gate, project_root, state)
        results.append((is_passed, message))
        if not is_passed:
            all_passed = False

    return all_passed, results
