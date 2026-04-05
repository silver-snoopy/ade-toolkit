"""Entry point for ``python -m ade.crew``."""

from __future__ import annotations

import sys

import click

from ade.crew.runner import run


@click.group()
def cli() -> None:
    """ADE CrewAI runner — execute local LLM agents."""


@cli.command()
@click.option(
    "--phase",
    required=True,
    type=click.Choice(["stubs", "code", "test", "fix"]),
)
@click.option("--task-id", required=True)
@click.option("--worktree", required=True)
@click.option("--config", default=".ade/config.yaml")
def run_cmd(phase: str, task_id: str, worktree: str, config: str) -> None:
    """Run a CrewAI agent phase."""
    exit_code = run(phase, task_id, worktree, config)
    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
