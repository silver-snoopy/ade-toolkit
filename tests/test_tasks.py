from __future__ import annotations

from pathlib import Path

import logging

import pytest
from pydantic import ValidationError

from ade.tasks import (
    InvalidTransitionError,
    IterationCounts,
    TaskState,
    TaskStatus,
    VALID_TRANSITIONS,
    create_task,
    increment_iteration,
    list_tasks,
    load_task,
    update_task_status,
)


def test_task_status_values() -> None:
    assert TaskStatus.INITIATED == "initiated"
    assert TaskStatus.PLANNING == "planning"
    assert TaskStatus.DESIGN_CHECK == "design_check"
    assert TaskStatus.CODING == "coding"
    assert TaskStatus.QUALITY_GATE == "quality_gate"
    assert TaskStatus.REVIEWING == "reviewing"
    assert TaskStatus.FINALIZING == "finalizing"
    assert TaskStatus.AWAITING_MERGE == "awaiting_merge"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.FAILED == "failed"
    assert TaskStatus.HUMAN_ESCALATION == "human_escalation"


def test_create_task(tmp_path: Path) -> None:
    state = create_task(
        ade_dir=tmp_path,
        description="Add JWT authentication",
    )
    assert state.task_id  # Non-empty
    assert state.description == "Add JWT authentication"
    assert state.status == TaskStatus.INITIATED
    assert state.current_phase == 0
    assert state.iterations.design_check == 0
    assert state.iterations.code_review == 0
    assert state.iterations.qa_fix == 0
    # state.json should exist on disk
    state_path = tmp_path / "tasks" / state.task_id / "state.json"
    assert state_path.exists()


def test_load_task(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test task")
    loaded = load_task(ade_dir=tmp_path, task_id=state.task_id)
    assert loaded.task_id == state.task_id
    assert loaded.description == state.description
    assert loaded.status == TaskStatus.INITIATED


def test_load_task_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Task not found"):
        load_task(ade_dir=tmp_path, task_id="nonexistent")


def test_update_task_status(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test task")
    updated = update_task_status(
        ade_dir=tmp_path,
        task_id=state.task_id,
        status=TaskStatus.PLANNING,
        current_phase=1,
    )
    assert updated.status == TaskStatus.PLANNING
    assert updated.current_phase == 1
    # Verify persisted
    reloaded = load_task(ade_dir=tmp_path, task_id=state.task_id)
    assert reloaded.status == TaskStatus.PLANNING


def test_update_task_with_worktree(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test task")
    # Walk to CODING via valid transitions
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.PLANNING, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.DESIGN_CHECK, current_phase=1)
    updated = update_task_status(
        ade_dir=tmp_path,
        task_id=state.task_id,
        status=TaskStatus.CODING,
        current_phase=2,
        worktree=".ade/worktrees/abc123",
        branch="ade/abc123",
    )
    assert updated.worktree == ".ade/worktrees/abc123"
    assert updated.branch == "ade/abc123"


def test_update_task_adds_timestamp(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test task")
    updated = update_task_status(
        ade_dir=tmp_path,
        task_id=state.task_id,
        status=TaskStatus.PLANNING,
        current_phase=1,
    )
    assert "planning" in updated.timestamps
    assert updated.timestamps["created"]  # From creation


def test_increment_iteration(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test task")
    updated = increment_iteration(
        ade_dir=tmp_path,
        task_id=state.task_id,
        counter="qa_fix",
    )
    assert updated.iterations.qa_fix == 1
    updated2 = increment_iteration(
        ade_dir=tmp_path,
        task_id=state.task_id,
        counter="qa_fix",
    )
    assert updated2.iterations.qa_fix == 2


def test_increment_iteration_invalid_counter(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test task")
    with pytest.raises(ValueError, match="Invalid counter"):
        increment_iteration(ade_dir=tmp_path, task_id=state.task_id, counter="bogus")


def test_list_tasks_empty(tmp_path: Path) -> None:
    assert list_tasks(ade_dir=tmp_path) == []


def test_list_tasks_multiple(tmp_path: Path) -> None:
    create_task(ade_dir=tmp_path, description="Task A")
    create_task(ade_dir=tmp_path, description="Task B")
    tasks = list_tasks(ade_dir=tmp_path)
    assert len(tasks) == 2
    descriptions = {t.description for t in tasks}
    assert descriptions == {"Task A", "Task B"}


def test_list_tasks_ignores_invalid_dirs(tmp_path: Path) -> None:
    """Dirs without state.json are silently skipped."""
    create_task(ade_dir=tmp_path, description="Valid task")
    (tmp_path / "tasks" / "garbage").mkdir(parents=True)
    tasks = list_tasks(ade_dir=tmp_path)
    assert len(tasks) == 1


def test_save_state_no_tmp_remnant(tmp_path: Path) -> None:
    """After save, no .json.tmp file should remain."""
    state = create_task(ade_dir=tmp_path, description="Test task")
    task_dir = tmp_path / "tasks" / state.task_id
    tmp_files = list(task_dir.glob("*.tmp"))
    assert tmp_files == []


def test_task_state_rejects_worktree_without_branch() -> None:
    with pytest.raises(ValidationError, match="worktree.*branch|branch.*worktree"):
        TaskState(task_id="abc", description="x", worktree="/some/path")


def test_task_state_rejects_branch_without_worktree() -> None:
    with pytest.raises(ValidationError, match="worktree.*branch|branch.*worktree"):
        TaskState(task_id="abc", description="x", branch="ade/abc")


def test_task_state_rejects_empty_task_id() -> None:
    with pytest.raises(ValidationError, match="task_id"):
        TaskState(task_id="", description="x")


def test_iteration_counts_rejects_negative() -> None:
    with pytest.raises(ValidationError):
        IterationCounts(design_check=-1)


def test_list_tasks_warns_on_corrupt_json(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Corrupt state.json should log a warning, not silently skip."""
    create_task(ade_dir=tmp_path, description="Valid task")
    # Create corrupt task
    corrupt_dir = tmp_path / "tasks" / "corrupt1"
    corrupt_dir.mkdir(parents=True)
    (corrupt_dir / "state.json").write_text("{broken json", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="ade.tasks"):
        tasks = list_tasks(ade_dir=tmp_path)

    assert len(tasks) == 1  # Only valid task returned
    assert "corrupt1" in caplog.text  # Warning mentions the bad task dir


def test_valid_transition_initiated_to_planning(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test")
    updated = update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                                  status=TaskStatus.PLANNING, current_phase=1)
    assert updated.status == TaskStatus.PLANNING


def test_valid_transition_design_check_self_loop(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test")
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.PLANNING, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.DESIGN_CHECK, current_phase=1)
    # Self-loop should be allowed
    updated = update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                                  status=TaskStatus.DESIGN_CHECK, current_phase=1)
    assert updated.status == TaskStatus.DESIGN_CHECK


def test_valid_transition_reviewing_to_quality_gate(tmp_path: Path) -> None:
    """Review loop: REVIEWING → QUALITY_GATE is valid."""
    state = create_task(ade_dir=tmp_path, description="Test")
    # Walk to REVIEWING
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.PLANNING, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.DESIGN_CHECK, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.CODING, current_phase=2)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.QUALITY_GATE, current_phase=3)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.REVIEWING, current_phase=4)
    # Loop back to QA
    updated = update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                                  status=TaskStatus.QUALITY_GATE, current_phase=3)
    assert updated.status == TaskStatus.QUALITY_GATE


def test_invalid_transition_completed_to_planning(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test")
    # Walk to COMPLETED
    for s, p in [
        (TaskStatus.PLANNING, 1), (TaskStatus.DESIGN_CHECK, 1),
        (TaskStatus.CODING, 2), (TaskStatus.QUALITY_GATE, 3),
        (TaskStatus.REVIEWING, 4), (TaskStatus.FINALIZING, 5),
        (TaskStatus.AWAITING_MERGE, 6), (TaskStatus.COMPLETED, 6),
    ]:
        update_task_status(ade_dir=tmp_path, task_id=state.task_id, status=s, current_phase=p)
    with pytest.raises(InvalidTransitionError):
        update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                           status=TaskStatus.PLANNING, current_phase=1)


def test_invalid_transition_coding_to_reviewing(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test")
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.PLANNING, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.DESIGN_CHECK, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.CODING, current_phase=2)
    with pytest.raises(InvalidTransitionError):
        update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                           status=TaskStatus.REVIEWING, current_phase=4)


@pytest.mark.parametrize("status", [
    s for s in TaskStatus if s not in (TaskStatus.COMPLETED, TaskStatus.FAILED)
])
def test_any_state_to_failed(tmp_path: Path, status: TaskStatus) -> None:
    """Every non-terminal state can transition to FAILED."""
    import json
    state = create_task(ade_dir=tmp_path, description="Test")
    # Directly set the status in the JSON to avoid transition validation
    state_path = tmp_path / "tasks" / state.task_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["status"] = status.value
    state_path.write_text(json.dumps(data), encoding="utf-8")
    updated = update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                                  status=TaskStatus.FAILED, current_phase=0)
    assert updated.status == TaskStatus.FAILED


def test_terminal_states_reject_all_transitions(tmp_path: Path) -> None:
    import json
    for terminal in (TaskStatus.COMPLETED, TaskStatus.FAILED):
        state = create_task(ade_dir=tmp_path, description=f"Test {terminal}")
        # Set terminal state directly
        state_path = tmp_path / "tasks" / state.task_id / "state.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data["status"] = terminal.value
        state_path.write_text(json.dumps(data), encoding="utf-8")
        for target in TaskStatus:
            with pytest.raises(InvalidTransitionError):
                update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                                    status=target, current_phase=0)


def test_valid_transitions_covers_all_statuses() -> None:
    for status in TaskStatus:
        assert status in VALID_TRANSITIONS, f"{status} missing from VALID_TRANSITIONS"
