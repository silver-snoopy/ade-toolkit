from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app
from ade.tasks import create_task

runner = CliRunner()


def test_cli_resume_shows_status(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test task")
    result = runner.invoke(app, ["resume", state.task_id, "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert state.task_id in result.stdout
    assert "initiated" in result.stdout.lower()


def test_cli_resume_nonexistent_task(tmp_path: Path) -> None:
    (tmp_path / ".ade").mkdir()
    result = runner.invoke(app, ["resume", "nonexistent", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0 or result.exit_code == 1
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()
