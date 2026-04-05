"""Task lifecycle manager — create, read, update, list ADE tasks."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger("ade.tasks")


class TaskStatus(StrEnum):
    INITIATED = "initiated"
    PLANNING = "planning"
    DESIGN_CHECK = "design_check"
    CODING = "coding"
    QUALITY_GATE = "quality_gate"
    REVIEWING = "reviewing"
    FINALIZING = "finalizing"
    AWAITING_MERGE = "awaiting_merge"
    COMPLETED = "completed"
    FAILED = "failed"
    HUMAN_ESCALATION = "human_escalation"


class IterationCounts(BaseModel):
    design_check: int = Field(default=0, ge=0)
    code_review: int = Field(default=0, ge=0)
    qa_fix: int = Field(default=0, ge=0)


class TaskState(BaseModel):
    task_id: str
    description: str
    status: TaskStatus = TaskStatus.INITIATED
    current_phase: int = 0
    iterations: IterationCounts = Field(default_factory=IterationCounts)
    timestamps: dict[str, str] = Field(default_factory=dict)
    worktree: str | None = None
    branch: str | None = None
    files_modified: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_invariants(self) -> TaskState:
        if not self.task_id:
            raise ValueError("task_id must be non-empty")
        if (self.worktree is None) != (self.branch is None):
            raise ValueError("worktree and branch must both be set or both be None")
        return self


class InvalidTransitionError(ValueError):
    """Raised when a state transition is not allowed."""


VALID_TRANSITIONS: MappingProxyType[TaskStatus, frozenset[TaskStatus]] = MappingProxyType(
    {
        TaskStatus.INITIATED: frozenset({TaskStatus.PLANNING, TaskStatus.FAILED}),
        TaskStatus.PLANNING: frozenset({TaskStatus.DESIGN_CHECK, TaskStatus.FAILED}),
        TaskStatus.DESIGN_CHECK: frozenset(
            {TaskStatus.DESIGN_CHECK, TaskStatus.CODING, TaskStatus.FAILED}
        ),
        TaskStatus.CODING: frozenset({TaskStatus.QUALITY_GATE, TaskStatus.FAILED}),
        TaskStatus.QUALITY_GATE: frozenset(
            {TaskStatus.QUALITY_GATE, TaskStatus.REVIEWING, TaskStatus.FAILED}
        ),
        TaskStatus.REVIEWING: frozenset(
            {
                TaskStatus.QUALITY_GATE,
                TaskStatus.HUMAN_ESCALATION,
                TaskStatus.FINALIZING,
                TaskStatus.FAILED,
            }
        ),
        TaskStatus.FINALIZING: frozenset({TaskStatus.AWAITING_MERGE, TaskStatus.FAILED}),
        TaskStatus.AWAITING_MERGE: frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED}),
        TaskStatus.HUMAN_ESCALATION: frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED}),
        TaskStatus.COMPLETED: frozenset(),
        TaskStatus.FAILED: frozenset(),
    }
)


def _task_dir(ade_dir: Path, task_id: str) -> Path:
    return ade_dir / "tasks" / task_id


def _state_path(ade_dir: Path, task_id: str) -> Path:
    return _task_dir(ade_dir, task_id) / "state.json"


def _save_state(ade_dir: Path, state: TaskState) -> None:
    path = _state_path(ade_dir, state.task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    os.replace(str(tmp), str(path))


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def create_task(ade_dir: Path, description: str) -> TaskState:
    """Create a new task with a unique ID and persist its initial state."""
    task_id = uuid.uuid4().hex[:8]
    state = TaskState(
        task_id=task_id,
        description=description,
        timestamps={"created": _now_iso()},
    )
    _save_state(ade_dir, state)
    return state


def load_task(ade_dir: Path, task_id: str) -> TaskState:
    """Load task state from disk."""
    path = _state_path(ade_dir, task_id)
    if not path.exists():
        raise FileNotFoundError(f"Task not found: {task_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return TaskState.model_validate(data)


def update_task_status(
    ade_dir: Path,
    task_id: str,
    status: TaskStatus,
    current_phase: int,
    worktree: str | None = None,
    branch: str | None = None,
) -> TaskState:
    """Update a task's status, phase, and optional worktree info."""
    state = load_task(ade_dir, task_id)
    allowed = VALID_TRANSITIONS.get(state.status, set())
    if status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from {state.status.value} to {status.value}"
        )
    state.status = status
    state.current_phase = current_phase
    state.timestamps[status.value] = _now_iso()
    if worktree is not None:
        state.worktree = worktree
    if branch is not None:
        state.branch = branch
    _save_state(ade_dir, state)
    return state


def increment_iteration(
    ade_dir: Path,
    task_id: str,
    counter: str,
) -> TaskState:
    """Increment an iteration counter (design_check, code_review, qa_fix)."""
    state = load_task(ade_dir, task_id)
    if counter not in ("design_check", "code_review", "qa_fix"):
        raise ValueError(f"Invalid counter: {counter}")
    current = getattr(state.iterations, counter)
    setattr(state.iterations, counter, current + 1)
    _save_state(ade_dir, state)
    return state


def list_tasks(ade_dir: Path) -> list[TaskState]:
    """List all tasks with valid state.json files."""
    tasks_dir = ade_dir / "tasks"
    if not tasks_dir.exists():
        return []
    results = []
    for entry in sorted(tasks_dir.iterdir()):
        state_file = entry / "state.json"
        if entry.is_dir() and state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                results.append(TaskState.model_validate(data))
            except json.JSONDecodeError as exc:
                logger.warning("Skipping task %s: corrupted state.json: %s", entry.name, exc)
            except (ValueError, KeyError, TypeError) as exc:
                logger.warning("Skipping task %s: invalid state: %s", entry.name, exc)
    return results
