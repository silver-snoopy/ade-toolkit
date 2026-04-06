"""Structured progress logger for CrewAI runner tasks."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


class ProgressLogger:
    """Appends timestamped structured log entries to a task's progress.log file."""

    def __init__(self, task_dir: Path) -> None:
        self._log_path = task_dir / "progress.log"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        *,
        phase: str,
        agent: str,
        step: str,
        file: str,
        status: str,
    ) -> None:
        """Append a structured log entry to the progress file."""
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        line = f"ts={ts} phase={phase} agent={agent} step={step} file={file} status={status}\n"
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(line)
