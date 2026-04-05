"""Agent factory — builds CrewAI agents from YAML definitions."""

from __future__ import annotations

from pathlib import Path

import yaml
from crewai import Agent

from ade.crew.tools.git import GitCommitTool
from ade.crew.tools.safe_file import SafeFileTool
from ade.crew.tools.safe_shell import SafeShellTool
from ade.crew.tools.search import SearchCodeTool


def load_agent_config(agent_name: str, config_dir: Path) -> dict:
    """Load agent YAML config from .ade/crew/<name>.yaml."""
    config_path = config_dir / f"{agent_name}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Agent config not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_agent(
    agent_name: str,
    config_dir: Path,
    worktree_path: Path,
    plan_files: list[str],
) -> Agent:
    """Create a CrewAI Agent with sandboxed tools."""
    config = load_agent_config(agent_name, config_dir)

    tools = [
        SafeShellTool(worktree_path=worktree_path),
        SafeFileTool(
            worktree_path=worktree_path,
            plan_files=plan_files,
            agent_role=agent_name,
        ),
        SearchCodeTool(worktree_path=worktree_path),
        GitCommitTool(worktree_path=worktree_path),
    ]

    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config.get("backstory", ""),
        tools=tools,
        llm=config.get("model", "ollama/gemma4:31b"),
        verbose=config.get("verbose", False),
        allow_delegation=False,
        max_iter=config.get("max_iter", 10),
    )
