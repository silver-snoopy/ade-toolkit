"""Integration tests for the full SDLC lifecycle."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ade.circuit_breaker import CircuitBreakerResult, check_circuit_breaker
from ade.config import OrchestrationConfig
from ade.recovery import determine_resume_point
from ade.tasks import (
    InvalidTransitionError,
    TaskStatus,
    create_task,
    increment_iteration,
    load_task,
    update_task_status,
)
from ade.worktrees import create_worktree, list_worktrees, remove_worktree


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Create a minimal git repo with .ade structure."""
    repo = tmp_path / "project"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
    (repo / "README.md").write_text("# Test", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True)
    (repo / ".ade").mkdir()
    return repo


def test_full_lifecycle_happy_path(project: Path) -> None:
    """Simulate a complete 10-phase SDLC lifecycle."""
    ade_dir = project / ".ade"

    # Create task
    state = create_task(ade_dir=ade_dir, description="Add JWT auth")
    task_id = state.task_id
    assert state.status == TaskStatus.INITIATED

    # Phase 0: Intent capture
    update_task_status(ade_dir, task_id, TaskStatus.INTENT_CAPTURE, current_phase=0)

    # Phase 1: Research
    update_task_status(ade_dir, task_id, TaskStatus.RESEARCHING, current_phase=1)

    # Phase 2: Planning
    update_task_status(ade_dir, task_id, TaskStatus.PLANNING, current_phase=2)

    # Phase 3: Design check
    update_task_status(ade_dir, task_id, TaskStatus.DESIGN_CHECK, current_phase=3)
    increment_iteration(ade_dir, task_id, "design_check")
    assert check_circuit_breaker(ade_dir, task_id) == CircuitBreakerResult.OK

    # Phase 4: Implement — create worktree
    wt = create_worktree(project_dir=project, task_id=task_id)
    update_task_status(
        ade_dir,
        task_id,
        TaskStatus.CODING,
        current_phase=4,
        worktree=str(wt.path),
        branch=wt.branch,
    )
    assert wt.path.exists()

    # Phase 5: Quality Gate
    update_task_status(ade_dir, task_id, TaskStatus.QUALITY_GATE, current_phase=5)

    # Phase 6: Review
    update_task_status(ade_dir, task_id, TaskStatus.REVIEWING, current_phase=6)

    # Phase 7: Verify
    update_task_status(ade_dir, task_id, TaskStatus.VERIFYING, current_phase=7)

    # Phase 8: Documentation
    update_task_status(ade_dir, task_id, TaskStatus.DOCUMENTING, current_phase=8)

    # Phase 9: Commit & PR
    update_task_status(ade_dir, task_id, TaskStatus.COMMITTING, current_phase=9)

    # Awaiting merge (merge gate)
    update_task_status(ade_dir, task_id, TaskStatus.AWAITING_MERGE, current_phase=9)

    # Phase 10: Retrospective — cleanup
    remove_worktree(project_dir=project, task_id=task_id)
    update_task_status(ade_dir, task_id, TaskStatus.RETROSPECTIVE, current_phase=10)

    # Complete
    update_task_status(ade_dir, task_id, TaskStatus.COMPLETED, current_phase=10)

    final = load_task(ade_dir, task_id)
    assert final.status == TaskStatus.COMPLETED
    assert "created" in final.timestamps
    assert "completed" in final.timestamps


def test_qa_fix_loop_with_circuit_breaker(project: Path) -> None:
    """Simulate QA failures triggering the circuit breaker."""
    ade_dir = project / ".ade"
    state = create_task(ade_dir=ade_dir, description="Flaky task")
    task_id = state.task_id

    # Simulate 3 QA fix cycles
    for _ in range(3):
        increment_iteration(ade_dir, task_id, "qa_fix")

    # Circuit breaker should trip
    result = check_circuit_breaker(ade_dir, task_id)
    assert result == CircuitBreakerResult.QA_FIX_LIMIT

    # Walk to a valid state before escalation
    update_task_status(ade_dir, task_id, TaskStatus.INTENT_CAPTURE, current_phase=0)
    update_task_status(ade_dir, task_id, TaskStatus.RESEARCHING, current_phase=1)
    update_task_status(ade_dir, task_id, TaskStatus.PLANNING, current_phase=2)
    update_task_status(ade_dir, task_id, TaskStatus.DESIGN_CHECK, current_phase=3)
    update_task_status(ade_dir, task_id, TaskStatus.CODING, current_phase=4)
    update_task_status(ade_dir, task_id, TaskStatus.QUALITY_GATE, current_phase=5)
    update_task_status(ade_dir, task_id, TaskStatus.REVIEWING, current_phase=6)
    # Now HUMAN_ESCALATION is valid from REVIEWING
    update_task_status(ade_dir, task_id, TaskStatus.HUMAN_ESCALATION, current_phase=6)
    final = load_task(ade_dir, task_id)
    assert final.status == TaskStatus.HUMAN_ESCALATION


def test_worktree_isolation(project: Path) -> None:
    """Verify two tasks get separate worktrees."""
    ade_dir = project / ".ade"
    s1 = create_task(ade_dir=ade_dir, description="Task A")
    s2 = create_task(ade_dir=ade_dir, description="Task B")

    wt1 = create_worktree(project_dir=project, task_id=s1.task_id)
    wt2 = create_worktree(project_dir=project, task_id=s2.task_id)

    assert wt1.path != wt2.path
    assert wt1.path.exists()
    assert wt2.path.exists()

    trees = list_worktrees(project_dir=project)
    assert len(trees) == 3  # main + 2 task worktrees

    # Cleanup
    remove_worktree(project_dir=project, task_id=s1.task_id)
    remove_worktree(project_dir=project, task_id=s2.task_id)


def test_full_lifecycle_with_validated_transitions(project: Path) -> None:
    """Happy path with transition validation enforced (10-phase pipeline)."""
    ade_dir = project / ".ade"
    state = create_task(ade_dir=ade_dir, description="Validated lifecycle")
    task_id = state.task_id

    # Each transition must be valid
    for status, phase in [
        (TaskStatus.INTENT_CAPTURE, 0),
        (TaskStatus.RESEARCHING, 1),
        (TaskStatus.PLANNING, 2),
        (TaskStatus.DESIGN_CHECK, 3),
        (TaskStatus.CODING, 4),
        (TaskStatus.QUALITY_GATE, 5),
        (TaskStatus.REVIEWING, 6),
        (TaskStatus.VERIFYING, 7),
        (TaskStatus.DOCUMENTING, 8),
        (TaskStatus.COMMITTING, 9),
        (TaskStatus.AWAITING_MERGE, 9),
        (TaskStatus.RETROSPECTIVE, 10),
        (TaskStatus.COMPLETED, 10),
    ]:
        update_task_status(ade_dir, task_id, status, current_phase=phase)

    final = load_task(ade_dir, task_id)
    assert final.status == TaskStatus.COMPLETED

    # Invalid transition should be rejected
    with pytest.raises(InvalidTransitionError):
        update_task_status(ade_dir, task_id, TaskStatus.PLANNING, current_phase=2)


def test_lifecycle_circuit_breaker_total_limit(project: Path) -> None:
    import json

    ade_dir = project / ".ade"
    state = create_task(ade_dir=ade_dir, description="Total limit test")
    task_id = state.task_id
    # Set iterations via direct JSON edit
    state_path = ade_dir / "tasks" / task_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["iterations"] = {"design_check": 1, "code_review": 2, "qa_fix": 2, "verify_reject": 1}
    state_path.write_text(json.dumps(data), encoding="utf-8")

    config = OrchestrationConfig(max_total_iterations=6)
    result = check_circuit_breaker(ade_dir, task_id, config=config)
    assert result == CircuitBreakerResult.TOTAL_ITERATION_LIMIT


def test_lifecycle_crash_recovery(project: Path) -> None:
    ade_dir = project / ".ade"
    state = create_task(ade_dir=ade_dir, description="Crash test")
    task_id = state.task_id

    # Corrupt the state file
    state_path = ade_dir / "tasks" / task_id / "state.json"
    (ade_dir / "tasks" / task_id / "plan.md").write_text("# Plan", encoding="utf-8")
    state_path.write_text("{corrupt!", encoding="utf-8")

    status, message = determine_resume_point(ade_dir, task_id)
    assert status == TaskStatus.PLANNING


def test_verify_reject_loop(project: Path) -> None:
    """VERIFYING can reject back to REVIEWING."""
    ade_dir = project / ".ade"
    state = create_task(ade_dir=ade_dir, description="Verify reject test")
    task_id = state.task_id

    # Walk to VERIFYING
    for status, phase in [
        (TaskStatus.INTENT_CAPTURE, 0),
        (TaskStatus.RESEARCHING, 1),
        (TaskStatus.PLANNING, 2),
        (TaskStatus.DESIGN_CHECK, 3),
        (TaskStatus.CODING, 4),
        (TaskStatus.QUALITY_GATE, 5),
        (TaskStatus.REVIEWING, 6),
        (TaskStatus.VERIFYING, 7),
    ]:
        update_task_status(ade_dir, task_id, status, current_phase=phase)

    # Reject back to REVIEWING
    update_task_status(ade_dir, task_id, TaskStatus.REVIEWING, current_phase=6)
    increment_iteration(ade_dir, task_id, "verify_reject")

    # Can proceed to VERIFYING again
    update_task_status(ade_dir, task_id, TaskStatus.VERIFYING, current_phase=7)
    final = load_task(ade_dir, task_id)
    assert final.status == TaskStatus.VERIFYING
    assert final.iterations.verify_reject == 1


def test_retrospective_captures_completion(project: Path) -> None:
    """RETROSPECTIVE transitions to COMPLETED."""
    import json

    ade_dir = project / ".ade"
    state = create_task(ade_dir=ade_dir, description="Retro test")
    task_id = state.task_id

    # Set state directly to RETROSPECTIVE for simplicity
    state_path = ade_dir / "tasks" / task_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["status"] = "retrospective"
    data["current_phase"] = 10
    state_path.write_text(json.dumps(data), encoding="utf-8")

    update_task_status(ade_dir, task_id, TaskStatus.COMPLETED, current_phase=10)
    final = load_task(ade_dir, task_id)
    assert final.status == TaskStatus.COMPLETED


def test_exit_codes_defined() -> None:
    from ade.crew.runner import EXIT_ESCALATE, EXIT_FAILURE, EXIT_PARTIAL, EXIT_SUCCESS

    assert EXIT_SUCCESS == 0
    assert EXIT_FAILURE == 1
    assert EXIT_PARTIAL == 2
    assert EXIT_ESCALATE == 3
