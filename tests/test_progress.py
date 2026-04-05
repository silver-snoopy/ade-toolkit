from __future__ import annotations

from pathlib import Path

from ade.crew.progress import ProgressLogger


def test_progress_creates_log_file(tmp_path: Path) -> None:
    logger = ProgressLogger(task_dir=tmp_path)
    logger.log(phase="code", agent="coder", step="1/4", file="src/foo.py", status="writing")
    assert (tmp_path / "progress.log").exists()


def test_progress_log_format(tmp_path: Path) -> None:
    logger = ProgressLogger(task_dir=tmp_path)
    logger.log(phase="code", agent="coder", step="1/4", file="src/foo.py", status="writing")
    content = (tmp_path / "progress.log").read_text()
    assert "phase=code" in content
    assert "agent=coder" in content
    assert "step=1/4" in content
    assert "status=writing" in content


def test_progress_appends_entries(tmp_path: Path) -> None:
    logger = ProgressLogger(task_dir=tmp_path)
    logger.log(phase="code", agent="coder", step="1/4", file="a.py", status="writing")
    logger.log(phase="code", agent="coder", step="1/4", file="a.py", status="complete")
    lines = (tmp_path / "progress.log").read_text().strip().splitlines()
    assert len(lines) == 2
