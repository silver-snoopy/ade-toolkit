"""Integration tests for the full CrewAI runner pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from ade.crew.runner import EXIT_FAILURE, EXIT_PARTIAL, EXIT_SUCCESS, run


@pytest.fixture
def project_env(tmp_path: Path) -> Path:
    """Set up a complete fake project with .ade directory structure."""
    project = tmp_path / "project"
    project.mkdir()

    # .ade/config.yaml
    ade_dir = project / ".ade"
    ade_dir.mkdir()
    config = {
        "version": "2.0",
        "project": {"name": "test-project", "languages": ["python"]},
        "models": {"primary": {"name": "gemma4:31b", "provider": "ollama"}},
    }
    (ade_dir / "config.yaml").write_text(yaml.dump(config))

    # .ade/crew/*.yaml for all agent types
    crew_dir = ade_dir / "crew"
    crew_dir.mkdir()
    agents = {
        "architect": {
            "role": "Software Architect",
            "goal": "Design module structure",
            "model": "ollama/gemma4:31b",
        },
        "coder": {
            "role": "Senior Developer",
            "goal": "Write production code",
            "model": "ollama/gemma4:31b",
        },
        "tester": {
            "role": "QA Engineer",
            "goal": "Write tests",
            "model": "ollama/qwen2.5-coder:14b",
        },
        "fixer": {
            "role": "Bug Fixer",
            "goal": "Fix failing tests",
            "model": "ollama/gemma4:31b",
        },
    }
    for name, cfg in agents.items():
        (crew_dir / f"{name}.yaml").write_text(yaml.dump(cfg))

    # .ade/tasks/task-001/plan.md
    task_dir = ade_dir / "tasks" / "task-001"
    task_dir.mkdir(parents=True)
    plan = """# Implementation Plan

## Files

- Create: `src/auth/tokens.py`
- Create: `src/auth/handler.py`
- Create: `tests/test_auth.py`

## Steps

1. Create token generation module
2. Create auth handler
3. Write tests
"""
    (task_dir / "plan.md").write_text(plan)

    return project


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_full_pipeline_code_phase(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    project_env: Path,
) -> None:
    """Full pipeline: health check -> agent creation -> crew execution -> success."""
    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance

    result = run("code", "task-001", str(project_env))

    assert result == EXIT_SUCCESS
    mock_health.assert_called_once()
    mock_create_agent.assert_called_once()
    # Verify agent was created with correct params
    call_kwargs = mock_create_agent.call_args.kwargs
    assert call_kwargs["agent_name"] == "coder"
    assert call_kwargs["worktree_path"] == project_env
    assert call_kwargs["config_dir"] == project_env / ".ade" / "crew"
    assert "src/auth/tokens.py" in call_kwargs["plan_files"]
    assert "src/auth/handler.py" in call_kwargs["plan_files"]
    assert "tests/test_auth.py" in call_kwargs["plan_files"]
    # Verify crew was kicked off
    mock_crew_instance.kickoff.assert_called_once()
    # Verify progress log was written
    log_path = project_env / ".ade" / "tasks" / "task-001" / "progress.log"
    assert log_path.exists()
    content = log_path.read_text()
    assert "complete" in content


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_full_pipeline_stubs_phase(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    project_env: Path,
) -> None:
    """Stubs phase uses architect agent."""
    mock_create_agent.return_value = MagicMock()
    mock_crew.return_value = MagicMock()

    result = run("stubs", "task-001", str(project_env))

    assert result == EXIT_SUCCESS
    assert mock_create_agent.call_args.kwargs["agent_name"] == "architect"


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_full_pipeline_test_phase(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    project_env: Path,
) -> None:
    """Test phase uses tester agent."""
    mock_create_agent.return_value = MagicMock()
    mock_crew.return_value = MagicMock()

    result = run("test", "task-001", str(project_env))

    assert result == EXIT_SUCCESS
    assert mock_create_agent.call_args.kwargs["agent_name"] == "tester"


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_full_pipeline_fix_phase(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    project_env: Path,
) -> None:
    """Fix phase uses fixer agent."""
    mock_create_agent.return_value = MagicMock()
    mock_crew.return_value = MagicMock()

    result = run("fix", "task-001", str(project_env))

    assert result == EXIT_SUCCESS
    assert mock_create_agent.call_args.kwargs["agent_name"] == "fixer"


@patch("ade.crew.runner.check_ollama_health", return_value=False)
def test_pipeline_ollama_not_running(mock_health: MagicMock, project_env: Path) -> None:
    """Pipeline fails when Ollama is not running."""
    result = run("code", "task-001", str(project_env))
    assert result == EXIT_FAILURE
    # Verify progress log shows the failure
    log_path = project_env / ".ade" / "tasks" / "task-001" / "progress.log"
    assert log_path.exists()
    content = log_path.read_text()
    assert "ollama not running" in content


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_pipeline_max_iterations(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    project_env: Path,
) -> None:
    """Max iterations returns EXIT_PARTIAL."""
    mock_create_agent.return_value = MagicMock()
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.side_effect = RuntimeError("Max iterations reached for agent")
    mock_crew.return_value = mock_crew_instance

    result = run("code", "task-001", str(project_env))
    assert result == EXIT_PARTIAL


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_pipeline_progress_log_records_all_steps(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    project_env: Path,
) -> None:
    """Verify all progress steps are logged during a successful run."""
    mock_create_agent.return_value = MagicMock()
    mock_crew.return_value = MagicMock()

    run("code", "task-001", str(project_env))

    log_path = project_env / ".ade" / "tasks" / "task-001" / "progress.log"
    content = log_path.read_text()
    lines = content.strip().splitlines()

    # Should have at least 4 log entries: checking ollama, creating agent, running crew, complete
    assert len(lines) >= 4
    assert any("checking ollama" in line for line in lines)
    assert any("creating coder agent" in line for line in lines)
    assert any("running crew" in line for line in lines)
    assert any("complete" in line for line in lines)


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_pipeline_crew_receives_correct_task_description(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task_cls: MagicMock,
    mock_crew: MagicMock,
    project_env: Path,
) -> None:
    """Verify CrewAI Task is created with the correct phase description."""
    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent
    mock_crew.return_value = MagicMock()

    run("code", "task-001", str(project_env))

    # The Task constructor should be called with the phase description
    mock_task_cls.assert_called_once()
    task_kwargs = mock_task_cls.call_args.kwargs
    assert "Implement the code" in task_kwargs["description"]
    assert task_kwargs["agent"] is mock_agent


@patch("ade.crew.runner.Crew")
@patch("ade.crew.runner.Task")
@patch("ade.crew.runner.create_agent")
@patch("ade.crew.runner.check_ollama_health", return_value=True)
def test_pipeline_generic_error_returns_failure(
    mock_health: MagicMock,
    mock_create_agent: MagicMock,
    mock_task: MagicMock,
    mock_crew: MagicMock,
    project_env: Path,
) -> None:
    """A non-max-iterations error returns EXIT_FAILURE."""
    mock_create_agent.return_value = MagicMock()
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.side_effect = ConnectionError("Connection refused")
    mock_crew.return_value = mock_crew_instance

    result = run("code", "task-001", str(project_env))
    assert result == EXIT_FAILURE
    # Verify the error is logged
    log_path = project_env / ".ade" / "tasks" / "task-001" / "progress.log"
    content = log_path.read_text()
    assert "Connection refused" in content
