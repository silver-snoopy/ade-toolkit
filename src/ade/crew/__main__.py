"""Entry point for ``python -m ade.crew``."""

from __future__ import annotations

import sys

import click

from ade.crew.runner import run


@click.group()
def cli() -> None:
    """ADE CrewAI runner — execute local LLM agents."""


@cli.command(name="run")
@click.option(
    "--phase",
    required=True,
    type=click.Choice(
        [
            "stubs",
            "code",
            "test",
            "fix",
            "research",
            "review_logic",
            "review_conventions",
            "review_security",
        ]
    ),
)
@click.option("--task-id", required=True)
@click.option("--worktree", required=True)
@click.option("--config", default=".ade/config.yaml")
@click.option("--main-project-dir", default=None, help="Path to main project (for plan file copy)")
def run_cmd(
    phase: str, task_id: str, worktree: str, config: str, main_project_dir: str | None
) -> None:
    """Run a CrewAI agent phase."""
    exit_code = run(phase, task_id, worktree, config, main_project_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
