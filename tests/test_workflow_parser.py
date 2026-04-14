"""Tests for workflow_parser module — FailRoute parsing and validation."""

import tempfile
import os
from pathlib import Path

import pytest

from devflow.workflow_parser import FailRoute, Step, Workflow, parse_workflow


def _write_toml(content: str) -> Path:
    """Write TOML content to a temp file and return path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


class TestFailRouteDataclass:
    """Test FailRoute dataclass defaults."""

    def test_defaults(self) -> None:
        route = FailRoute()
        assert route.min_fails == 1
        assert route.max_fails is None
        assert route.target == ""

    def test_custom_values(self) -> None:
        route = FailRoute(min_fails=3, max_fails=5, target="other-step")
        assert route.min_fails == 3
        assert route.max_fails == 5
        assert route.target == "other-step"


class TestFailRouteParsing:
    """Test fail_route parsing from TOML."""

    def test_valid_fail_route(self) -> None:
        toml = """
[workflow]
id = "t1"
name = "Test"
version = "1.0"

[[steps]]
id = "s1"
name = "S1"
gates = ["command_success:{test_command}"]
next = "s2"

[[steps.fail_route]]
min_fails = 1
max_fails = 2
target = "s1"

[[steps.fail_route]]
min_fails = 3
target = "s2"

[[steps]]
id = "s2"
name = "S2"
next = ""
"""
        p = _write_toml(toml)
        try:
            w = parse_workflow(p)
            step = w.get_step("s1")
            assert len(step.fail_routes) == 2
            assert step.fail_routes[0].min_fails == 1
            assert step.fail_routes[0].max_fails == 2
            assert step.fail_routes[0].target == "s1"
            assert step.fail_routes[1].min_fails == 3
            assert step.fail_routes[1].max_fails is None
            assert step.fail_routes[1].target == "s2"
        finally:
            os.unlink(p)

    def test_min_fails_less_than_1_rejected(self, caplog) -> None:
        toml = """
[workflow]
id = "t"
name = "T"
version = "1.0"

[[steps]]
id = "s1"
name = "S1"
next = "s2"

[[steps.fail_route]]
min_fails = 0
target = "s1"

[[steps]]
id = "s2"
name = "S2"
next = ""
"""
        p = _write_toml(toml)
        try:
            w = parse_workflow(p)
            assert len(w.get_step("s1").fail_routes) == 0
            assert "min_fails (0) < 1" in caplog.text
        finally:
            os.unlink(p)

    def test_negative_min_fails_rejected(self) -> None:
        toml = """
[workflow]
id = "t"
name = "T"
version = "1.0"

[[steps]]
id = "s1"
name = "S1"
next = "s2"

[[steps.fail_route]]
min_fails = -1
target = "s1"

[[steps]]
id = "s2"
name = "S2"
next = ""
"""
        p = _write_toml(toml)
        try:
            w = parse_workflow(p)
            assert len(w.get_step("s1").fail_routes) == 0
        finally:
            os.unlink(p)

    def test_empty_target_rejected(self, caplog) -> None:
        toml = """
[workflow]
id = "t"
name = "T"
version = "1.0"

[[steps]]
id = "s1"
name = "S1"
next = "s2"

[[steps.fail_route]]
min_fails = 1
target = ""

[[steps]]
id = "s2"
name = "S2"
next = ""
"""
        p = _write_toml(toml)
        try:
            w = parse_workflow(p)
            assert len(w.get_step("s1").fail_routes) == 0
            assert "empty target" in caplog.text
        finally:
            os.unlink(p)

    def test_min_fails_greater_than_max_fails_rejected(self, caplog) -> None:
        toml = """
[workflow]
id = "t"
name = "T"
version = "1.0"

[[steps]]
id = "s1"
name = "S1"
next = "s2"

[[steps.fail_route]]
min_fails = 5
max_fails = 2
target = "s1"

[[steps]]
id = "s2"
name = "S2"
next = ""
"""
        p = _write_toml(toml)
        try:
            w = parse_workflow(p)
            assert len(w.get_step("s1").fail_routes) == 0
            assert "min_fails (5) > max_fails (2)" in caplog.text
        finally:
            os.unlink(p)

    def test_no_fail_routes_backward_compat(self) -> None:
        toml = """
[workflow]
id = "t"
name = "T"
version = "1.0"

[[steps]]
id = "s1"
name = "S1"
gates = []
next = ""
"""
        p = _write_toml(toml)
        try:
            w = parse_workflow(p)
            assert len(w.get_step("s1").fail_routes) == 0
        finally:
            os.unlink(p)

    def test_multiple_fail_routes_on_different_steps(self) -> None:
        toml = """
[workflow]
id = "t"
name = "T"
version = "1.0"

[[steps]]
id = "s1"
name = "S1"
gates = ["command_success:exit 1"]
next = "s2"

[[steps.fail_route]]
min_fails = 1
target = "s1"

[[steps]]
id = "s2"
name = "S2"
gates = ["command_success:exit 1"]
next = ""

[[steps.fail_route]]
min_fails = 1
max_fails = 2
target = "s1"

[[steps.fail_route]]
min_fails = 3
target = "s2"
"""
        p = _write_toml(toml)
        try:
            w = parse_workflow(p)
            assert len(w.get_step("s1").fail_routes) == 1
            assert len(w.get_step("s2").fail_routes) == 2
        finally:
            os.unlink(p)


class TestStepDataclass:
    """Test Step dataclass with fail_routes."""

    def test_step_default_no_fail_routes(self) -> None:
        step = Step(id="s1")
        assert step.fail_routes == []

    def test_step_with_fail_routes(self) -> None:
        step = Step(id="s1", fail_routes=[FailRoute(min_fails=1, target="other")])
        assert len(step.fail_routes) == 1


class TestWorkflowDataclass:
    """Test Workflow dataclass lookups."""

    def test_get_step(self) -> None:
        s1 = Step(id="s1", name="Step 1")
        s2 = Step(id="s2", name="Step 2")
        w = Workflow(id="w", steps=[s1, s2])
        assert w.get_step("s1") is s1
        assert w.get_step("s2") is s2
        assert w.get_step("nonexistent") is None

    def test_get_first_step(self) -> None:
        s1 = Step(id="s1")
        s2 = Step(id="s2")
        w = Workflow(id="w", steps=[s1, s2])
        assert w.get_first_step() is s1

    def test_get_first_step_empty(self) -> None:
        w = Workflow(id="w", steps=[])
        assert w.get_first_step() is None


class TestBundledWorkflows:
    """Test that bundled MODE-A and MODE-B parse correctly."""

    def test_mode_a_parses(self) -> None:
        p = Path("src/devflow/data/workflows/MODE-A.toml")
        w = parse_workflow(p)
        assert w is not None
        assert w.id == "MODE-A"
        assert len(w.steps) == 9

    def test_mode_b_parses_with_fail_routes(self) -> None:
        p = Path("src/devflow/data/workflows/MODE-B.toml")
        w = parse_workflow(p)
        assert w is not None
        assert w.id == "MODE-B"

        # debug-hypothesis has 1 fail_route
        hypo = w.get_step("debug-hypothesis")
        assert len(hypo.fail_routes) == 1
        assert hypo.fail_routes[0].min_fails == 1
        assert hypo.fail_routes[0].target == "debug-root-cause"

        # debug-fix has 2 fail_routes
        fix = w.get_step("debug-fix")
        assert len(fix.fail_routes) == 2
        assert fix.fail_routes[0] == FailRoute(min_fails=1, max_fails=2, target="debug-root-cause")
        assert fix.fail_routes[1] == FailRoute(min_fails=3, target="debug-question")

    def test_mode_b_cross_workflow_reference(self) -> None:
        p = Path("src/devflow/data/workflows/MODE-B.toml")
        w = parse_workflow(p)
        finish = w.get_step("debug-finish")
        assert finish.next_step == "MODE-A:write-plan"

    def test_mode_a_req_approve_has_feat_gate(self) -> None:
        p = Path("src/devflow/data/workflows/MODE-A.toml")
        w = parse_workflow(p)
        approve = w.get_step("req-approve")
        gate_str = str(approve.gates)
        assert "file_exists:docs/features/FEAT" in gate_str

    def test_mode_a_code_review_has_user_approved(self) -> None:
        p = Path("src/devflow/data/workflows/MODE-A.toml")
        w = parse_workflow(p)
        review = w.get_step("code-review")
        gate_str = str(review.gates)
        assert "user_approved:CODE-REVIEW" in gate_str

    def test_mode_a_finish_has_status_done(self) -> None:
        p = Path("src/devflow/data/workflows/MODE-A.toml")
        w = parse_workflow(p)
        finish = w.get_step("finish")
        gate_str = str(finish.gates)
        assert "done" in gate_str
