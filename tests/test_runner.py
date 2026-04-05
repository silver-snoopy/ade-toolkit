"""Tests for the CrewAI runner orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from ade.crew.runner import (
    EXIT_FAILURE,
    EXIT_PARTIAL,
    EXIT_SUCCESS,
    PHASE_AGENT_MAP,
    _load_plan_files,
    run,
)


@pytest.fixture
def task_env(tmp_path: Path) -> Path:
    """Create a minimal task environment for the runner."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # .ade/config.yaml
    ade_dir = worktree / ".ade"
    ade_dir.mkdir()
    config = {"version": "2.0", "project": {"name": "test"}}
    (ade_dir / "config.yaml").write_text(yaml.dump(config))

    # .ade/crew/<agent>.yaml
    crew_dir = ade_dir / "crew"
    crew_dir.mkdir()
    for agent_name in ["architect", "coder", "tester", "fixer"]:
        agent_config = {
            "role": f"{agent_name.title()} Agent",
            "goal": f"Perform {agent_name} tasks",
            "model": "ollama/gemma4:31b",
        }
        (crew_dir / f"{agent_name}.yaml").write_text(yaml.dump(agent_config))

    # .ade/tasks/test-123/plan.md
    task_dir = ade_dir / "tasks" / "test-123"
    task_dir.mkdir(parents=True)
    plan = """# Plan

## Files

- Create: `src/foo.py`
- Create: `src/bar.py`

## Steps

1. Implement foo
"""
    (task_dir / "plan.md").write_text(plan)

    return worktree


def test_load_plan_files(task_env: Path) -> None:
    task_dir = task_env / ".ade" / "tasks" / "test-123"
    files = _load_plan_files(task_dir)
    assert "src/foo.py" in files
    assert "src/bar.py" in files


def test_load_plan_files_missing(tmp_path: Path) -> None:
    files = _load_plan_files(tmp_path)
    assert files == []


def test_phase_agent_mapping() -> None:
    assert PHASE_AGENT_MAP["stubs"] == "architect"
    assert PHASE_AGENT_MAP["code"] == "coder"
    assert PHASE_AGENT_MAP["test"] == "tester"
    assert PHASE_AGENT_MAP["fix"] == "fixer"


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_run_success(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    task_env: Path,
) -> None:
    mock_create_agent.return_value = MagicMock()
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance

    result = run("code", "test-123", str(task_env))
    assert result == EXIT_SUCCESS
    mock_health.assert_called_once()
    mock_create_agent.assert_called_once()
    mock_crew_instance.kickoff.assert_called_once()


@patch("ade.crew.runner.check_ollama_health", return_value=False)
def test_run_ollama_not_running(mock_health: MagicMock, task_env: Path) -> None:
    result = run("code", "test-123", str(task_env))
    assert result == EXIT_FAILURE


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_run_agent_failure(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    task_env: Path,
) -> None:
    mock_create_agent.return_value = MagicMock()
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.side_effect = RuntimeError("Agent crashed")
    mock_crew.return_value = mock_crew_instance

    result = run("code", "test-123", str(task_env))
    assert result == EXIT_FAILURE


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_run_max_iterations(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    task_env: Path,
) -> None:
    mock_create_agent.return_value = MagicMock()
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.side_effect = RuntimeError("Max iterations reached")
    mock_crew.return_value = mock_crew_instance

    result = run("code", "test-123", str(task_env))
    assert result == EXIT_PARTIAL


def test_run_invalid_phase(task_env: Path) -> None:
    task_dir = task_env / ".ade" / "tasks" / "test-123"
    task_dir.mkdir(parents=True, exist_ok=True)
    result = run("invalid", "test-123", str(task_env))
    assert result == EXIT_FAILURE


@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_run_writes_progress_log(mock_health: MagicMock, task_env: Path) -> None:
    """Verify progress log entries are written during a run."""
    with (
        patch("ade.crew.runner.create_agent") as mock_create,
        patch("ade.crew.runner.Task"),
        patch("ade.crew.runner.Crew") as mock_crew,
    ):
        mock_create.return_value = MagicMock()
        mock_crew.return_value = MagicMock()

        run("code", "test-123", str(task_env))

    log_path = task_env / ".ade" / "tasks" / "test-123" / "progress.log"
    assert log_path.exists()
    content = log_path.read_text()
    assert "checking ollama" in content
    assert "creating coder agent" in content
    assert "running crew" in content
