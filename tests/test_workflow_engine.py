"""Tests for workflow_engine module — advance, fail routes, cross-workflow, format methods."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from devflow.state_store import StateStore
from devflow.workflow_engine import WorkflowEngine

# Enable shell command execution for workflow engine tests
os.environ["DEVFLOW_ALLOW_SHELL"] = "1"


@pytest.fixture
def project_root() -> Path:
    """Create a temp project root with MODE-A and MODE-B workflows."""
    tmpdir = tempfile.mkdtemp()
    root = Path(tmpdir)

    # Create directory structure
    (root / ".devflow" / "workflows").mkdir(parents=True)
    (root / ".devflow" / "prompts").mkdir(parents=True)
    for d in [
        "debug", "features", "requirements", "evidence", "completion",
        "superpowers/specs", "superpowers/plans",
    ]:
        (root / "docs" / d).mkdir(parents=True)

    # Copy workflow files
    src_data = Path("src/devflow/data/workflows")
    shutil.copy2(src_data / "MODE-A.toml", root / ".devflow" / "workflows" / "MODE-A.toml")
    shutil.copy2(src_data / "MODE-B.toml", root / ".devflow" / "workflows" / "MODE-B.toml")

    # Create config
    (root / ".devflow" / "config.toml").write_text(
        '[project]\nname = "test"\nlanguage = "python"\n'
        '[commands]\ntest = "echo ok"\ntest_unit = "echo ok"\ntest_integration = "echo ok"\n'
    )

    yield root
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def project_root_failing_test() -> Path:
    """Project root with a test command that always fails."""
    tmpdir = tempfile.mkdtemp()
    root = Path(tmpdir)

    (root / ".devflow" / "workflows").mkdir(parents=True)
    (root / ".devflow" / "prompts").mkdir(parents=True)
    for d in [
        "debug", "features", "requirements", "evidence", "completion",
        "superpowers/specs", "superpowers/plans",
    ]:
        (root / "docs" / d).mkdir(parents=True)

    src_data = Path("src/devflow/data/workflows")
    shutil.copy2(src_data / "MODE-A.toml", root / ".devflow" / "workflows" / "MODE-A.toml")
    shutil.copy2(src_data / "MODE-B.toml", root / ".devflow" / "workflows" / "MODE-B.toml")

    (root / ".devflow" / "config.toml").write_text(
        '[project]\nname = "test"\nlanguage = "python"\n'
        '[commands]\ntest = "exit 1"\n'
    )

    yield root
    shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Basic advance and gate pass
# ---------------------------------------------------------------------------


class TestBasicAdvance:
    """Test basic workflow progression with gate pass."""

    def test_first_step_is_req_create(self, project_root: Path) -> None:
        engine = WorkflowEngine.from_workflow("MODE-A", project_root)
        step = engine.get_current_step()
        assert step is not None
        assert step.id == "req-create"

    def test_advance_on_gate_pass(self, project_root: Path) -> None:
        engine = WorkflowEngine.from_workflow("MODE-A", project_root)
        run_id = engine.state.workflow_run_id

        # Create REQ file to pass gate
        (project_root / "docs" / "requirements" / f"REQ-{run_id}.md").write_text("status: draft")
        success, next_step, msg = engine.advance()
        assert success
        assert next_step is not None
        assert next_step.id == "req-approve"

    def test_advance_stays_on_gate_fail(self, project_root: Path) -> None:
        engine = WorkflowEngine.from_workflow("MODE-A", project_root)
        # No REQ file created -> gate fails
        success, next_step, msg = engine.advance()
        assert not success
        assert next_step is not None
        assert next_step.id == "req-create"  # stays


class TestModeAGateDense:
    """Test MODE-A enhanced gates: FEAT, user_approved, status:done."""

    def test_req_approve_needs_feat_file(self, project_root: Path) -> None:
        engine = WorkflowEngine.from_workflow("MODE-A", project_root)
        run_id = engine.state.workflow_run_id

        # Create REQ with approved status but NO FEAT file
        (project_root / "docs" / "requirements" / f"REQ-{run_id}.md").write_text("status: approved")
        engine.advance()  # -> req-approve

        # Should fail (missing FEAT)
        all_passed, results = engine.check_done()
        assert not all_passed
        assert any("FEAT" in msg for _, msg in results)

    def test_req_approve_passes_with_feat(self, project_root: Path) -> None:
        engine = WorkflowEngine.from_workflow("MODE-A", project_root)
        run_id = engine.state.workflow_run_id

        (project_root / "docs" / "requirements" / f"REQ-{run_id}.md").write_text("status: approved")
        engine.advance()  # -> req-approve
        (project_root / "docs" / "features" / f"FEAT-{run_id}.md").write_text("# Feature")

        success, next_step, msg = engine.advance()
        assert success
        assert next_step is not None
        assert next_step.id == "brainstorm"

    def test_code_review_needs_user_approved(self, project_root: Path) -> None:
        engine = WorkflowEngine.from_workflow("MODE-A", project_root)
        run_id = engine.state.workflow_run_id

        # Navigate to code-review
        (project_root / "docs" / "requirements" / f"REQ-{run_id}.md").write_text("status: approved")
        (project_root / "docs" / "features" / f"FEAT-{run_id}.md").write_text("F")
        engine.advance()  # -> req-approve
        engine.advance()  # -> brainstorm
        (project_root / "docs" / "superpowers" / "specs" / f"DESIGN-{run_id}.md").write_text("D")
        engine.advance()  # -> write-plan
        (project_root / "docs" / "superpowers" / "plans" / f"PLAN-{run_id}.md").write_text("P")
        engine.advance()  # -> implement-tdd
        engine.advance()  # -> code-review (test passes with echo ok)

        # Should fail without approval
        success, _, _ = engine.advance()
        assert not success

    def test_code_review_passes_with_approval(self, project_root: Path) -> None:
        engine = WorkflowEngine.from_workflow("MODE-A", project_root)
        run_id = engine.state.workflow_run_id

        # Navigate to code-review
        (project_root / "docs" / "requirements" / f"REQ-{run_id}.md").write_text("status: approved")
        (project_root / "docs" / "features" / f"FEAT-{run_id}.md").write_text("F")
        engine.advance()  # -> req-approve
        engine.advance()  # -> brainstorm
        (project_root / "docs" / "superpowers" / "specs" / f"DESIGN-{run_id}.md").write_text("D")
        engine.advance()  # -> write-plan
        (project_root / "docs" / "superpowers" / "plans" / f"PLAN-{run_id}.md").write_text("P")
        engine.advance()  # -> implement-tdd
        engine.advance()  # -> code-review

        engine.state.set("approved_items", [f"CODE-REVIEW-{run_id}"])
        success, next_step, msg = engine.advance()
        assert success
        assert next_step is not None
        assert next_step.id == "test-run"

    def test_finish_needs_req_status_done(self, project_root: Path) -> None:
        engine = WorkflowEngine.from_workflow("MODE-A", project_root)
        run_id = engine.state.workflow_run_id

        # Navigate through to finish
        (project_root / "docs" / "requirements" / f"REQ-{run_id}.md").write_text("status: approved")
        (project_root / "docs" / "features" / f"FEAT-{run_id}.md").write_text("F")
        engine.advance()  # -> req-approve
        engine.advance()  # -> brainstorm
        (project_root / "docs" / "superpowers" / "specs" / f"DESIGN-{run_id}.md").write_text("D")
        engine.advance()  # -> write-plan
        (project_root / "docs" / "superpowers" / "plans" / f"PLAN-{run_id}.md").write_text("P")
        engine.advance()  # -> implement-tdd
        engine.advance()  # -> code-review
        engine.state.set("approved_items", [f"CODE-REVIEW-{run_id}"])
        engine.advance()  # -> test-run
        engine.advance()  # -> verify
        (project_root / "docs" / "evidence" / f"EVIDENCE-{run_id}.md").write_text("E")
        engine.advance()  # -> finish

        # Create COMPLETION but REQ still has "status: approved"
        (project_root / "docs" / "completion" / f"COMPLETION-{run_id}.md").write_text("C")
        success, _, _ = engine.advance()
        assert not success  # missing status: done

        # Update REQ to status: done
        (project_root / "docs" / "requirements" / f"REQ-{run_id}.md").write_text("status: done")
        success, _, msg = engine.advance()
        assert "complete" in msg.lower()


# ---------------------------------------------------------------------------
# Fail route routing and escalation
# ---------------------------------------------------------------------------


class TestFailRouteRouting:
    """Test fail_route automatic routing on gate failure."""

    def test_debug_hypothesis_fail_routes_to_root_cause(
        self, project_root_failing_test: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root_failing_test)
        run_id = engine.state.workflow_run_id

        # Navigate to debug-hypothesis
        (project_root_failing_test / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()  # -> debug-pattern
        (project_root_failing_test / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        engine.advance()  # -> debug-hypothesis

        # Gate fails (no HYPOTHESIS file) -> fail_route to debug-root-cause
        success, next_step, msg = engine.advance()
        assert success
        assert next_step is not None
        assert next_step.id == "debug-root-cause"
        assert "Routed on failure" in msg

    def test_fail_count_persists_after_route(
        self, project_root_failing_test: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root_failing_test)
        run_id = engine.state.workflow_run_id

        (project_root_failing_test / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()
        (project_root_failing_test / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        engine.advance()

        # Advance with fail route
        engine.advance()
        fc = engine.state.get("debug-hypothesis_fail_count", 0)
        assert fc == 1  # Persists, not reset

    def test_debug_fix_escalation(
        self, project_root_failing_test: Path
    ) -> None:
        """Fail 1-2 → root-cause, fail 3+ → debug-question."""
        engine = WorkflowEngine.from_workflow("MODE-B", project_root_failing_test)
        run_id = engine.state.workflow_run_id

        # Navigate to debug-fix
        (project_root_failing_test / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()
        (project_root_failing_test / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        engine.advance()
        (project_root_failing_test / "docs" / "debug" / f"HYPOTHESIS-{run_id}.md").write_text("H")
        engine.advance()  # -> debug-fix

        # Fail 1: should route to debug-root-cause
        success, next_step, msg = engine.advance()
        assert success
        assert next_step is not None
        assert next_step.id == "debug-root-cause"
        assert engine.state.get("debug-fix_fail_count", 0) == 1

        # Jump back to debug-fix
        engine.state.current_step = "debug-fix"

        # Fail 2: still routes to debug-root-cause
        success, next_step, msg = engine.advance()
        assert success
        assert next_step is not None
        assert next_step.id == "debug-root-cause"
        assert engine.state.get("debug-fix_fail_count", 0) == 2

        # Jump back to debug-fix
        engine.state.current_step = "debug-fix"

        # Fail 3: ESCALATE to debug-question
        success, next_step, msg = engine.advance()
        assert success
        assert next_step is not None
        assert next_step.id == "debug-question"
        assert engine.state.get("debug-fix_fail_count", 0) == 3

    def test_no_fail_route_stays_on_step(
        self, project_root_failing_test: Path
    ) -> None:
        """Steps without fail_routes stay on current step when gates fail."""
        engine = WorkflowEngine.from_workflow("MODE-B", project_root_failing_test)

        # debug-root-cause has no fail_routes
        success, next_step, msg = engine.advance()
        assert not success
        assert next_step is not None
        assert next_step.id == "debug-root-cause"

    def test_fail_count_resets_on_gate_pass(
        self, project_root: Path
    ) -> None:
        """Fail count resets when gates pass."""
        engine = WorkflowEngine.from_workflow("MODE-B", project_root)
        run_id = engine.state.workflow_run_id

        # Fail once on debug-root-cause
        success, _, _ = engine.advance()
        assert not success
        fc = engine.state.get("debug-root-cause_fail_count", 0)
        assert fc == 1

        # Create the file and pass
        (project_root / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        success, _, _ = engine.advance()
        assert success
        fc = engine.state.get("debug-root-cause_fail_count", 0)
        assert fc == 0  # Reset on pass


# ---------------------------------------------------------------------------
# Cross-workflow transitions
# ---------------------------------------------------------------------------


class TestCrossWorkflowTransition:
    """Test cross-workflow MODE-B -> MODE-A transition."""

    def test_debug_finish_transitions_to_mode_a(
        self, project_root: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root)
        run_id = engine.state.workflow_run_id

        # Walk through MODE-B to debug-finish
        (project_root / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()
        (project_root / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        engine.advance()
        (project_root / "docs" / "debug" / f"HYPOTHESIS-{run_id}.md").write_text("H")
        engine.advance()  # -> debug-fix
        (project_root / "docs" / "debug" / f"VERIFICATION-{run_id}.md").write_text("V")
        engine.advance()  # -> debug-verify
        (project_root / "docs" / "debug" / f"COMPLETION-{run_id}.md").write_text("C")
        engine.advance()  # -> debug-finish

        # Advance from debug-finish -> cross-workflow to MODE-A:write-plan
        success, next_step, msg = engine.advance()
        assert success
        assert next_step is not None
        assert next_step.id == "write-plan"

    def test_cross_workflow_switches_workflow_id(
        self, project_root: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root)
        run_id = engine.state.workflow_run_id

        (project_root / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()
        (project_root / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        engine.advance()
        (project_root / "docs" / "debug" / f"HYPOTHESIS-{run_id}.md").write_text("H")
        engine.advance()
        (project_root / "docs" / "debug" / f"VERIFICATION-{run_id}.md").write_text("V")
        engine.advance()
        (project_root / "docs" / "debug" / f"COMPLETION-{run_id}.md").write_text("C")
        engine.advance()  # -> debug-finish

        engine.advance()  # cross-workflow

        assert engine.workflow_id == "MODE-A"
        assert engine.state.current_workflow == "MODE-A"

    def test_cross_workflow_preserves_run_id(
        self, project_root: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root)
        run_id = engine.state.workflow_run_id

        (project_root / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()
        (project_root / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        engine.advance()
        (project_root / "docs" / "debug" / f"HYPOTHESIS-{run_id}.md").write_text("H")
        engine.advance()
        (project_root / "docs" / "debug" / f"VERIFICATION-{run_id}.md").write_text("V")
        engine.advance()
        (project_root / "docs" / "debug" / f"COMPLETION-{run_id}.md").write_text("C")
        engine.advance()
        engine.advance()  # cross-workflow

        assert engine.state.workflow_run_id == run_id

    def test_mode_a_continues_after_cross_workflow(
        self, project_root: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root)
        run_id = engine.state.workflow_run_id

        (project_root / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()
        (project_root / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        engine.advance()
        (project_root / "docs" / "debug" / f"HYPOTHESIS-{run_id}.md").write_text("H")
        engine.advance()
        (project_root / "docs" / "debug" / f"VERIFICATION-{run_id}.md").write_text("V")
        engine.advance()
        (project_root / "docs" / "debug" / f"COMPLETION-{run_id}.md").write_text("C")
        engine.advance()
        engine.advance()  # cross-workflow -> MODE-A:write-plan

        # Continue in MODE-A
        (project_root / "docs" / "superpowers" / "plans" / f"PLAN-{run_id}.md").write_text("Plan")
        success, next_step, msg = engine.advance()
        assert success
        assert next_step is not None
        assert next_step.id == "implement-tdd"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_bad_fail_route_target_prints_warning(
        self, capsys,
    ) -> None:
        """Non-existent fail_route target prints warning and stays on step."""
        tmpdir = tempfile.mkdtemp()
        root = Path(tmpdir)
        (root / ".devflow" / "workflows").mkdir(parents=True)
        (root / ".devflow" / "prompts").mkdir(parents=True)
        (root / "docs" / "debug").mkdir(parents=True)

        (root / ".devflow" / "workflows" / "BAD.toml").write_text(
            '[workflow]\nid = "BAD"\nname = "Bad"\nversion = "1.0"\n\n'
            '[[steps]]\nid = "s1"\nname = "S1"\ngates = ["command_success:exit 1"]\nnext = "s2"\n\n'
            '[[steps.fail_route]]\nmin_fails = 1\ntarget = "nonexistent-step"\n\n'
            '[[steps]]\nid = "s2"\nname = "S2"\nnext = ""\n'
        )
        (root / ".devflow" / "config.toml").write_text(
            '[project]\nname = "test"\nlanguage = "python"\n[commands]\ntest = "echo ok"\n'
        )

        engine = WorkflowEngine.from_workflow("BAD", root)
        success, next_step, msg = engine.advance()
        assert not success
        captured = capsys.readouterr()
        assert "Warning" in captured.out

        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_nonexistent_cross_workflow_target(
        self,
    ) -> None:
        """Cross-workflow reference to non-existent workflow fails gracefully."""
        tmpdir = tempfile.mkdtemp()
        root = Path(tmpdir)
        (root / ".devflow" / "workflows").mkdir(parents=True)
        (root / ".devflow" / "prompts").mkdir(parents=True)

        (root / ".devflow" / "workflows" / "CROSS.toml").write_text(
            '[workflow]\nid = "CROSS"\nname = "Cross"\nversion = "1.0"\n\n'
            '[[steps]]\nid = "cs1"\nname = "CS1"\ngates = []\nnext = "NONEXISTENT:s1"\n'
        )

        engine = WorkflowEngine.from_workflow("CROSS", root)
        success, next_step, msg = engine.advance()
        assert not success
        assert "not found" in msg.lower()

        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_go_back(self) -> None:
        """go_back returns to previous step."""
        tmpdir = tempfile.mkdtemp()
        root = Path(tmpdir)
        (root / ".devflow" / "workflows").mkdir(parents=True)
        (root / ".devflow" / "prompts").mkdir(parents=True)

        (root / ".devflow" / "workflows" / "BACK.toml").write_text(
            '[workflow]\nid = "BACK"\nname = "Back"\nversion = "1.0"\n\n'
            '[[steps]]\nid = "b1"\nname = "B1"\ngates = []\nnext = "b2"\n\n'
            '[[steps]]\nid = "b2"\nname = "B2"\ngates = []\nnext = "b3"\n\n'
            '[[steps]]\nid = "b3"\nname = "B3"\ngates = []\nnext = ""\n'
        )

        engine = WorkflowEngine.from_workflow("BACK", root)
        engine.advance()  # b1 -> b2
        assert engine.get_current_step().id == "b2"

        success, prev_step, msg = engine.go_back()
        assert success
        assert prev_step is not None
        assert prev_step.id == "b1"

        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_go_back_at_first_step(self) -> None:
        """go_back at first step fails gracefully."""
        tmpdir = tempfile.mkdtemp()
        root = Path(tmpdir)
        (root / ".devflow" / "workflows").mkdir(parents=True)
        (root / ".devflow" / "prompts").mkdir(parents=True)

        (root / ".devflow" / "workflows" / "SIMPLE.toml").write_text(
            '[workflow]\nid = "SIMPLE"\nname = "Simple"\nversion = "1.0"\n\n'
            '[[steps]]\nid = "s1"\nname = "S1"\ngates = []\nnext = ""\n'
        )

        engine = WorkflowEngine.from_workflow("SIMPLE", root)
        success, _, _ = engine.go_back()
        assert not success

        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_type_safe_fail_count(self) -> None:
        """Corrupted state (non-int fail count) is handled gracefully."""
        tmpdir = tempfile.mkdtemp()
        root = Path(tmpdir)
        (root / ".devflow" / "workflows").mkdir(parents=True)
        (root / ".devflow" / "prompts").mkdir(parents=True)
        (root / "docs" / "debug").mkdir(parents=True)

        (root / ".devflow" / "workflows" / "SIMPLE.toml").write_text(
            '[workflow]\nid = "SIMPLE"\nname = "Simple"\nversion = "1.0"\n\n'
            '[[steps]]\nid = "s1"\nname = "S1"\ngates = ["command_success:exit 1"]\nnext = ""\n'
        )
        (root / ".devflow" / "config.toml").write_text(
            '[project]\nname = "test"\nlanguage = "python"\n[commands]\ntest = "echo ok"\n'
        )

        engine = WorkflowEngine.from_workflow("SIMPLE", root)
        # Corrupt the fail count
        engine.state.set("s1_fail_count", "not_a_number")

        # The engine's advance() computes the count with type guard
        # After advancing, count should be corrected to 1
        engine.advance()
        count = engine.state.get("s1_fail_count", 0)
        assert isinstance(count, int)
        assert count >= 1

        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_resolve_target_validates_same_workflow_step(self) -> None:
        """_resolve_target validates step exists in same workflow."""
        tmpdir = tempfile.mkdtemp()
        root = Path(tmpdir)
        (root / ".devflow" / "workflows").mkdir(parents=True)
        (root / ".devflow" / "prompts").mkdir(parents=True)

        (root / ".devflow" / "workflows" / "SIMPLE.toml").write_text(
            '[workflow]\nid = "SIMPLE"\nname = "Simple"\nversion = "1.0"\n\n'
            '[[steps]]\nid = "s1"\nname = "S1"\ngates = []\nnext = "nonexistent"\n'
        )

        engine = WorkflowEngine.from_workflow("SIMPLE", root)
        target_engine, step_id, msg = engine._resolve_target("nonexistent")
        assert target_engine is None
        assert "not found" in msg.lower()

        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Format and display methods
# ---------------------------------------------------------------------------


class TestFormatMethods:
    """Test format_current_instruction, format_done_result, format_status."""

    def test_format_current_instruction_shows_fail_routes(
        self, project_root_failing_test: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root_failing_test)
        run_id = engine.state.workflow_run_id

        # Navigate to debug-fix
        (project_root_failing_test / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()
        (project_root_failing_test / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        engine.advance()
        (project_root_failing_test / "docs" / "debug" / f"HYPOTHESIS-{run_id}.md").write_text("H")
        engine.advance()  # -> debug-fix

        instruction = engine.format_current_instruction()
        assert "On Failure:" in instruction
        assert "debug-root-cause" in instruction
        assert "debug-question" in instruction

    def test_format_done_result_shows_routing(
        self, project_root_failing_test: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root_failing_test)
        run_id = engine.state.workflow_run_id

        (project_root_failing_test / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()
        (project_root_failing_test / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        engine.advance()
        (project_root_failing_test / "docs" / "debug" / f"HYPOTHESIS-{run_id}.md").write_text("H")
        engine.advance()

        engine.advance()  # fails, routes to debug-root-cause
        result = engine.format_done_result()
        assert "Routing to:" in result
        assert "Run devflow current" in result

    def test_format_done_result_shows_retry_on_no_route(
        self, project_root_failing_test: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root_failing_test)

        # debug-root-cause has no fail_routes
        engine.advance()  # fails
        result = engine.format_done_result()
        assert "attempt" in result.lower() or "Fix and run again" in result

    def test_format_status_shows_has_fail_routes(
        self, project_root: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root)
        status = engine.format_status()
        assert "[has fail routes]" in status
        assert "debug-hypothesis" in status or "debug-fix" in status

    def test_format_done_result_shows_pass(
        self, project_root: Path
    ) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root)
        run_id = engine.state.workflow_run_id

        (project_root / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()  # passes

        result = engine.format_done_result()
        assert "All conditions satisfied" in result


# ---------------------------------------------------------------------------
# Config variable injection
# ---------------------------------------------------------------------------


class TestConfigInjection:
    """Test config variable injection from project root."""

    def test_test_command_injected(self, project_root: Path) -> None:
        engine = WorkflowEngine.from_workflow("MODE-B", project_root)
        run_id = engine.state.workflow_run_id

        # Navigate to debug-fix which uses command_success:{test_command}
        (project_root / "docs" / "debug" / f"ROOT-CAUSE-{run_id}.md").write_text("RC")
        engine.advance()
        (project_root / "docs" / "debug" / f"PATTERN-{run_id}.md").write_text("P")
        engine.advance()
        (project_root / "docs" / "debug" / f"HYPOTHESIS-{run_id}.md").write_text("H")
        engine.advance()  # -> debug-fix

        # Gate should pass (test = "echo ok")
        all_passed, results = engine.check_done()
        assert all_passed

    def test_config_variables_in_state(self, project_root: Path) -> None:
        engine = WorkflowEngine.from_workflow("MODE-A", project_root)
        # Trigger injection by checking done
        engine.check_done()
        assert engine.state.get("test_command") == "echo ok"

    def test_config_from_project_root_not_cwd(self) -> None:
        """Config is loaded from project root, not cwd."""
        tmpdir = tempfile.mkdtemp()
        root = Path(tmpdir)
        (root / ".devflow" / "workflows").mkdir(parents=True)
        (root / ".devflow" / "prompts").mkdir(parents=True)
        (root / "docs" / "debug").mkdir(parents=True)

        (root / ".devflow" / "workflows" / "MODE-B.toml").write_text(
            Path("src/devflow/data/workflows/MODE-B.toml").read_text()
        )
        (root / ".devflow" / "config.toml").write_text(
            '[project]\nname = "test"\nlanguage = "python"\n[commands]\ntest = "echo from_project"\n'
        )

        engine = WorkflowEngine.from_workflow("MODE-B", root)
        engine.check_done()
        assert engine.state.get("test_command") == "echo from_project"

        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Surjection verification
# ---------------------------------------------------------------------------


class TestSurjection:
    """Verify original workflow elements are mapped in TOML."""

    def test_mode_a_surjection(self) -> None:
        from devflow.workflow_parser import parse_workflow

        w = parse_workflow(Path("src/devflow/data/workflows/MODE-A.toml"))
        s = {step.id: step for step in w.steps}

        # REQ creation
        assert "file_exists:docs/requirements/REQ" in str(s["req-create"].gates)
        # REQ approval with status check
        assert "file_contains:docs/requirements/REQ" in str(s["req-approve"].gates)
        assert "approved" in str(s["req-approve"].gates)
        # FEAT gate
        assert "file_exists:docs/features/FEAT" in str(s["req-approve"].gates)
        # Code review gate
        assert "user_approved:CODE-REVIEW" in str(s["code-review"].gates)
        # Test run gates
        assert "command_success:{test_command}" in str(s["test-run"].gates)
        # Finish gate with status: done
        gate_str = str(s["finish"].gates)
        assert "file_contains:docs/requirements/REQ" in gate_str
        assert "done" in gate_str

    def test_mode_b_surjection(self) -> None:
        from devflow.workflow_parser import parse_workflow

        w = parse_workflow(Path("src/devflow/data/workflows/MODE-B.toml"))
        s = {step.id: step for step in w.steps}

        # P3->P1 hypothesis fail
        assert any(
            r.target == "debug-root-cause"
            for r in s["debug-hypothesis"].fail_routes
        )
        # P4->P1 fix fails <3
        assert any(
            r.target == "debug-root-cause" and r.min_fails == 1 and r.max_fails == 2
            for r in s["debug-fix"].fail_routes
        )
        # P4->P4.5 fix fails >=3
        assert any(
            r.target == "debug-question" and r.min_fails == 3
            for r in s["debug-fix"].fail_routes
        )
        # P4.5 gate and next
        assert "user_approved:ARCHITECTURE-REVIEW" in str(s["debug-question"].gates)
        assert s["debug-question"].next_step == "debug-root-cause"
        # Post-debug -> MODE-A
        assert s["debug-finish"].next_step == "MODE-A:write-plan"
