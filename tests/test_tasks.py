from __future__ import annotations

from pathlib import Path

import pytest

from ade.tasks import (
    TaskStatus,
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
