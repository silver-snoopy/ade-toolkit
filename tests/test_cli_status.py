from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app
from ade.tasks import TaskStatus, create_task, update_task_status

runner = CliRunner()


def test_status_no_ade_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["status", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No .ade directory" in result.stdout or "No active tasks" in result.stdout


def test_status_no_tasks(tmp_path: Path) -> None:
    (tmp_path / ".ade" / "tasks").mkdir(parents=True)
    result = runner.invoke(app, ["status", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No active tasks" in result.stdout


def test_status_shows_task(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Add JWT auth")
    # Walk to CODING via valid transitions
    update_task_status(
        ade_dir=ade_dir, task_id=state.task_id, status=TaskStatus.PLANNING, current_phase=1
    )
    update_task_status(
        ade_dir=ade_dir, task_id=state.task_id, status=TaskStatus.DESIGN_CHECK, current_phase=1
    )
    update_task_status(
        ade_dir=ade_dir,
        task_id=state.task_id,
        status=TaskStatus.CODING,
        current_phase=2,
    )
    result = runner.invoke(app, ["status", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert state.task_id in result.stdout
    assert "Add JWT auth" in result.stdout
    assert "coding" in result.stdout.lower()


def test_status_shows_iterations(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Fix bug")
    # Simulate some iterations
    from ade.tasks import increment_iteration

    increment_iteration(ade_dir=ade_dir, task_id=state.task_id, counter="qa_fix")
    increment_iteration(ade_dir=ade_dir, task_id=state.task_id, counter="qa_fix")
    result = runner.invoke(app, ["status", "--project-dir", str(tmp_path)])
    assert "qa_fix: 2" in result.stdout or "QA fix: 2" in result.stdout


def test_status_shows_completed_tasks(tmp_path: Path) -> None:
    import json

    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Done task")
    # Write COMPLETED status directly to state.json for test setup
    state_path = ade_dir / "tasks" / state.task_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["status"] = "completed"
    data["current_phase"] = 6
    state_path.write_text(json.dumps(data), encoding="utf-8")
    result = runner.invoke(app, ["status", "--project-dir", str(tmp_path)])
    assert "completed" in result.stdout.lower()
