"""Tests for agent factory — loading CrewAI agents from YAML definitions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from ade.crew.agents import create_agent, load_agent_config


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory with agent YAML files."""
    crew_dir = tmp_path / "crew"
    crew_dir.mkdir()

    coder_config = {
        "role": "Senior Python Developer",
        "goal": "Write clean, tested Python code",
        "backstory": "Expert Python developer with 10 years of experience",
        "model": "ollama/gemma4:31b",
        "verbose": False,
        "max_iter": 10,
    }
    (crew_dir / "coder.yaml").write_text(yaml.dump(coder_config))

    tester_config = {
        "role": "QA Engineer",
        "goal": "Write comprehensive test suites",
        "model": "ollama/qwen2.5-coder:14b",
        "max_iter": 8,
    }
    (crew_dir / "tester.yaml").write_text(yaml.dump(tester_config))

    return crew_dir


def test_load_agent_config(config_dir: Path) -> None:
    config = load_agent_config("coder", config_dir)
    assert config["role"] == "Senior Python Developer"
    assert config["goal"] == "Write clean, tested Python code"
    assert config["model"] == "ollama/gemma4:31b"


def test_load_agent_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Agent config not found"):
        load_agent_config("nonexistent", tmp_path)


@patch("ade.crew.agents.Agent")
def test_create_agent_returns_agent(mock_agent_class: MagicMock, config_dir: Path) -> None:
    mock_agent_class.return_value = MagicMock()
    agent = create_agent(
        "coder",
        config_dir,
        worktree_path=Path("/tmp/worktree"),
        plan_files=["src/foo.py"],
    )
    mock_agent_class.assert_called_once()
    call_kwargs = mock_agent_class.call_args.kwargs
    assert call_kwargs["role"] == "Senior Python Developer"
    assert call_kwargs["llm"] == "ollama/gemma4:31b"
    assert call_kwargs["allow_delegation"] is False
    assert len(call_kwargs["tools"]) == 4  # Shell, File, Search, Git
    assert agent is mock_agent_class.return_value


@patch("ade.crew.agents.Agent")
def test_create_agent_uses_correct_tools(mock_agent_class: MagicMock, config_dir: Path) -> None:
    mock_agent_class.return_value = MagicMock()
    create_agent(
        "coder",
        config_dir,
        worktree_path=Path("/tmp/worktree"),
        plan_files=["src/foo.py"],
    )
    call_kwargs = mock_agent_class.call_args.kwargs
    tool_types = [type(t).__name__ for t in call_kwargs["tools"]]
    assert "SafeShellTool" in tool_types
    assert "SafeFileTool" in tool_types
    assert "SearchCodeTool" in tool_types
    assert "GitCommitTool" in tool_types


@patch("ade.crew.agents.Agent")
def test_create_agent_tester_role(mock_agent_class: MagicMock, config_dir: Path) -> None:
    mock_agent_class.return_value = MagicMock()
    create_agent(
        "tester",
        config_dir,
        worktree_path=Path("/tmp/worktree"),
        plan_files=["src/foo.py"],
    )
    call_kwargs = mock_agent_class.call_args.kwargs
    assert call_kwargs["role"] == "QA Engineer"
    assert call_kwargs["llm"] == "ollama/qwen2.5-coder:14b"
    # Verify SafeFileTool has tester role
    file_tool = [t for t in call_kwargs["tools"] if type(t).__name__ == "SafeFileTool"][0]
    assert file_tool.agent_role == "tester"


@patch("ade.crew.agents.Agent")
def test_create_agent_defaults(mock_agent_class: MagicMock, config_dir: Path) -> None:
    """Config without backstory/verbose uses sensible defaults."""
    mock_agent_class.return_value = MagicMock()
    create_agent(
        "tester",
        config_dir,
        worktree_path=Path("/tmp/worktree"),
        plan_files=[],
    )
    call_kwargs = mock_agent_class.call_args.kwargs
    assert call_kwargs["backstory"] == ""
    assert call_kwargs["verbose"] is False
    assert call_kwargs["max_iter"] == 8
