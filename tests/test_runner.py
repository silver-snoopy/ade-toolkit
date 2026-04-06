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
    _check_worktree_changes,
    _load_plan_files,
    _setup_worktree_task_dir,
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
    for agent_name in ["architect", "coder", "tester", "fixer", "researcher", "reviewer"]:
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


def test_load_plan_files_table_format(tmp_path: Path) -> None:
    """Bug 1: Table-format plans should also be parsed correctly."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    plan = """# Test Plan
## Files Summary
### New Files (2)
| File | Phase | Purpose |
|------|-------|---------|
| `packages/shared/src/types/intelligence.ts` | 1 | Shared types |
| `packages/backend/src/services/test-service.ts` | 2 | Test service |
"""
    (task_dir / "plan.md").write_text(plan)
    files = _load_plan_files(task_dir)
    assert "packages/shared/src/types/intelligence.ts" in files
    assert "packages/backend/src/services/test-service.ts" in files


def test_load_plan_files_deduplicates(tmp_path: Path) -> None:
    """Duplicate file references should be deduplicated."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    plan = """# Plan
- Create: `src/foo.py`
| `src/foo.py` | also mentioned here |
"""
    (task_dir / "plan.md").write_text(plan)
    files = _load_plan_files(task_dir)
    assert files.count("src/foo.py") == 1


def test_phase_agent_mapping() -> None:
    assert PHASE_AGENT_MAP["stubs"] == "architect"
    assert PHASE_AGENT_MAP["code"] == "coder"
    assert PHASE_AGENT_MAP["test"] == "tester"
    assert PHASE_AGENT_MAP["fix"] == "fixer"
    assert PHASE_AGENT_MAP["research"] == "researcher"
    assert PHASE_AGENT_MAP["review_logic"] == "reviewer"
    assert PHASE_AGENT_MAP["review_conventions"] == "reviewer"
    assert PHASE_AGENT_MAP["review_security"] == "reviewer"


@patch("ade.crew.runner._check_worktree_changes", return_value=True)
@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.ensure_model_available", return_value=True)
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_run_success(
    mock_health: MagicMock,
    mock_model: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    mock_changes: MagicMock,
    task_env: Path,
) -> None:
    mock_create_agent.return_value = MagicMock()
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance

    result = run("code", "test-123", str(task_env))
    assert result == EXIT_SUCCESS
    mock_health.assert_called_once()
    mock_model.assert_called_once()
    mock_create_agent.assert_called_once()
    mock_crew_instance.kickoff.assert_called_once()


@patch("ade.crew.runner.check_ollama_health", return_value=False)
def test_run_ollama_not_running(mock_health: MagicMock, task_env: Path) -> None:
    result = run("code", "test-123", str(task_env))
    assert result == EXIT_FAILURE
    # Handoff report should exist
    handoffs = list((task_env / ".ade" / "tasks" / "test-123" / "handoffs").glob("*.json"))
    assert len(handoffs) == 1
    import json

    data = json.loads(handoffs[0].read_text())
    assert data["status"] == "ollama_down"


@patch("ade.crew.runner.ensure_model_available", return_value=False)
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_run_model_not_found(
    mock_health: MagicMock, mock_model: MagicMock, task_env: Path
) -> None:
    result = run("code", "test-123", str(task_env))
    assert result == EXIT_FAILURE
    import json

    handoffs = list((task_env / ".ade" / "tasks" / "test-123" / "handoffs").glob("*.json"))
    assert len(handoffs) == 1
    data = json.loads(handoffs[0].read_text())
    assert data["status"] == "model_not_found"


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.ensure_model_available", return_value=True)
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_run_agent_failure(
    mock_health: MagicMock,
    mock_model: MagicMock,
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
@patch("ade.crew.runner.ensure_model_available", return_value=True)
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_run_max_iterations(
    mock_health: MagicMock,
    mock_model: MagicMock,
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


@patch("ade.crew.runner._check_worktree_changes", return_value=True)
@patch("ade.crew.runner.ensure_model_available", return_value=True)
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_run_writes_progress_log(
    mock_health: MagicMock, mock_model: MagicMock, mock_changes: MagicMock, task_env: Path
) -> None:
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
    assert "checking model" in content
    assert "creating coder agent" in content
    assert "running crew" in content


@patch("ade.crew.runner._check_worktree_changes", return_value=True)
@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.ensure_model_available", return_value=True)
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_run_success_writes_handoff_report(
    mock_health: MagicMock,
    mock_model: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    mock_changes: MagicMock,
    task_env: Path,
) -> None:
    """Successful runs should also write a handoff report."""
    import json

    mock_create_agent.return_value = MagicMock()
    mock_crew.return_value = MagicMock()

    run("code", "test-123", str(task_env))

    handoffs = list((task_env / ".ade" / "tasks" / "test-123" / "handoffs").glob("*.json"))
    assert len(handoffs) == 1
    data = json.loads(handoffs[0].read_text())
    assert data["status"] == "success"
    assert data["phase"] == "code"
    assert data["agent_name"] == "coder"


def test_load_plan_files_falls_back_to_implementation_plan(tmp_path: Path) -> None:
    """Bug 9: When plan.md has few files, try implementation-plan.md."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    # plan.md with only 2 files
    (task_dir / "plan.md").write_text("""# Plan
| `src/a.ts` | Purpose |
| `src/b.ts` | Purpose |
""")
    # implementation-plan.md with many files
    (task_dir / "implementation-plan.md").write_text("""# Detailed Plan
| `packages/shared/src/types/a.ts` | Types |
| `packages/backend/src/services/b.ts` | Service |
| `packages/backend/src/routes/c.ts` | Routes |
| `packages/backend/src/db/d.ts` | Queries |
| `packages/frontend/src/components/e.tsx` | UI |
| `packages/frontend/src/hooks/f.ts` | Hooks |
""")
    files = _load_plan_files(task_dir)
    # Should use implementation-plan.md since plan.md has < 5 files
    assert len(files) == 6
    assert "packages/shared/src/types/a.ts" in files


def test_check_worktree_changes_ignores_ade_dir(tmp_path: Path) -> None:
    """Bug 8: .ade/ files should not count as agent output."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="?? .ade/\n?? .ade/crew/architect.yaml\n"
        )
        assert _check_worktree_changes(tmp_path) is False


def test_check_worktree_changes_detects_source_files(tmp_path: Path) -> None:
    """Source file changes should be detected even alongside .ade/ changes."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="?? .ade/\n?? src/new-file.ts\n"
        )
        assert _check_worktree_changes(tmp_path) is True


def test_check_worktree_changes_empty(tmp_path: Path) -> None:
    """No changes at all should return False."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="")
        assert _check_worktree_changes(tmp_path) is False


def test_setup_worktree_copies_crew_configs(tmp_path: Path) -> None:
    """Bug 7: Crew YAML configs must be copied to worktree."""
    # Set up main project .ade structure
    main = tmp_path / "main"
    main_ade = main / ".ade"
    (main_ade / "crew").mkdir(parents=True)
    (main_ade / "crew" / "architect.yaml").write_text("model: ollama/gemma4:31b")
    (main_ade / "crew" / "coder.yaml").write_text("model: ollama/gemma4:31b")
    (main_ade / "config.yaml").write_text("version: '3.0'")

    # Task files
    main_task = main_ade / "tasks" / "my-task"
    main_task.mkdir(parents=True)
    (main_task / "plan.md").write_text("# Plan")
    (main_task / "implementation-plan.md").write_text("# Impl Plan")
    (main_task / "intent.md").write_text("# Intent")

    # Worktree task dir (empty — fresh worktree)
    worktree_task = tmp_path / "worktree" / ".ade" / "tasks" / "my-task"

    _setup_worktree_task_dir(worktree_task, "my-task", main)

    # Verify crew configs copied
    worktree_ade = tmp_path / "worktree" / ".ade"
    assert (worktree_ade / "crew" / "architect.yaml").exists()
    assert (worktree_ade / "crew" / "coder.yaml").exists()
    assert (worktree_ade / "config.yaml").exists()

    # Verify all .md files copied
    assert (worktree_task / "plan.md").exists()
    assert (worktree_task / "implementation-plan.md").exists()
    assert (worktree_task / "intent.md").exists()
