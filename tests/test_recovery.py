from __future__ import annotations

from pathlib import Path

from ade.tasks import TaskStatus, create_task
from ade.recovery import determine_resume_point, infer_phase_from_artifacts


def test_infer_from_plan_md(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "abc123"
    task_dir.mkdir(parents=True)
    (task_dir / "plan.md").write_text("# Plan", encoding="utf-8")
    assert infer_phase_from_artifacts(task_dir) == TaskStatus.PLANNING


def test_infer_from_qa_report(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "abc123"
    task_dir.mkdir(parents=True)
    (task_dir / "qa-report.json").write_text("{}", encoding="utf-8")
    assert infer_phase_from_artifacts(task_dir) == TaskStatus.QUALITY_GATE


def test_infer_no_artifacts(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "abc123"
    task_dir.mkdir(parents=True)
    assert infer_phase_from_artifacts(task_dir) == TaskStatus.INITIATED


def test_determine_resume_with_valid_state(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    status, message = determine_resume_point(ade_dir=ade_dir, task_id=state.task_id)
    assert status == TaskStatus.INITIATED
    assert message  # Non-empty


def test_determine_resume_with_corrupt_state_and_artifacts(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    # Corrupt the state file
    state_path = ade_dir / "tasks" / state.task_id / "state.json"
    state_path.write_text("{broken", encoding="utf-8")
    # Add a plan artifact
    (ade_dir / "tasks" / state.task_id / "plan.md").write_text("# Plan", encoding="utf-8")
    status, message = determine_resume_point(ade_dir=ade_dir, task_id=state.task_id)
    assert status == TaskStatus.PLANNING
    assert "corrupt" in message.lower() or "artifact" in message.lower()
