"""Crash recovery — infer task state from artifacts when state.json is corrupt."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ade.tasks import TaskStatus, load_task

logger = logging.getLogger("ade.recovery")


def infer_phase_from_artifacts(task_dir: Path) -> TaskStatus:
    """Infer the last completed phase from task artifacts on disk."""
    if (task_dir / "retro.json").exists():
        return TaskStatus.COMPLETED
    if (task_dir / "verification").is_dir():
        return TaskStatus.VERIFYING
    if (task_dir / "qa-report.json").exists():
        return TaskStatus.QUALITY_GATE
    if (task_dir / "plan.md").exists():
        return TaskStatus.PLANNING
    if (task_dir / "intent.md").exists():
        return TaskStatus.INTENT_CAPTURE
    return TaskStatus.INITIATED


def determine_resume_point(ade_dir: Path, task_id: str) -> tuple[TaskStatus, str]:
    """Determine where to resume a task from.

    Returns (status, human_readable_message).
    Tries loading state.json first; falls back to artifact inference.
    """
    try:
        state = load_task(ade_dir, task_id)
        return state.status, f"Task {task_id} is at phase: {state.status.value}"
    except FileNotFoundError:
        return TaskStatus.INITIATED, f"Task {task_id} not found — may need to be recreated"
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Corrupt state for task %s, inferring from artifacts: %s", task_id, exc)
        task_dir = ade_dir / "tasks" / task_id
        inferred = infer_phase_from_artifacts(task_dir)
        return inferred, (
            f"Task {task_id} has corrupt state. "
            f"Inferred from artifacts: last completed phase was {inferred.value}"
        )
