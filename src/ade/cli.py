"""ADE CLI — scaffolding tool for Agentic Development Environment."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from jinja2 import Environment, PackageLoader
from rich import print as rprint
from rich.table import Table

from ade.detect import detect_project, normalize_language

app = typer.Typer(
    name="ade",
    help="ADE — Agentic Development Environment toolkit",
    no_args_is_help=True,
)

ADE_SECTION_MARKER = "## ADE — Agentic Development Environment"


def _get_template_env() -> Environment:
    return Environment(
        loader=PackageLoader("ade", "templates"),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _write_file(path: Path, content: str) -> None:
    """Write content to file, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _render_and_write(env: Environment, template_name: str, dest: Path, context: dict) -> None:
    """Render a Jinja2 template and write to destination."""
    template = env.get_template(template_name)
    content = template.render(**context)
    _write_file(dest, content)


def _update_claude_md(project_dir: Path, ade_section: str) -> None:
    """Append ADE section to CLAUDE.md, or create it."""
    claude_md = project_dir / "CLAUDE.md"

    if claude_md.exists():
        existing = claude_md.read_text(encoding="utf-8")
        if ADE_SECTION_MARKER in existing:
            return
        content = existing.rstrip() + "\n\n" + ade_section
    else:
        content = ade_section

    claude_md.write_text(content, encoding="utf-8")


def _check_command(name: str) -> bool:
    """Check if a command is available on PATH."""
    return shutil.which(name) is not None


def _render_template_dir(
    env: Environment,
    template_prefix: str,
    dest_dir: Path,
    context: dict,
    suffix: str = ".j2",
) -> None:
    """Render all templates under a prefix directory to a destination."""
    for template_name in env.loader.list_templates():
        if template_name.startswith(template_prefix) and template_name.endswith(suffix):
            relative = template_name[len(template_prefix) :]
            # Strip .j2 suffix from output filename
            dest_name = relative[: -len(suffix)] if relative.endswith(suffix) else relative
            # Convert underscores to dashes for Claude Code conventions
            dest_name = dest_name.replace("_", "-")
            _render_and_write(env, template_name, dest_dir / dest_name, context)


@app.command()
def init(
    project_dir: Annotated[Path, typer.Option(help="Project directory to initialize")] = Path("."),
    language: Annotated[
        str | None,
        typer.Option(help="Override detected languages (comma-separated)"),
    ] = None,
) -> None:
    """Initialize ADE in the current project."""
    project_dir = project_dir.resolve()

    if not project_dir.is_dir():
        rprint(f"[red]Error: {project_dir} is not a directory[/red]")
        raise typer.Exit(1)

    rprint(f"[bold]Initializing ADE in {project_dir}[/bold]")

    # Detect project
    info = detect_project(project_dir)

    # Apply language overrides
    if language:
        info.languages = [normalize_language(lang) for lang in language.split(",")]

    rprint(f"  Detected languages: {', '.join(info.languages) or 'none'}")
    rprint(f"  Project name: {info.project_name}")

    env = _get_template_env()
    ctx = {"info": info}

    # Generate .ade/.gitignore
    ade_dir = project_dir / ".ade"
    _render_and_write(env, "ade_gitignore.j2", ade_dir / ".gitignore", ctx)

    # Generate .claude/agents/*.md (from templates/agents/)
    _render_template_dir(env, "agents/", project_dir / ".claude" / "agents", ctx)

    # Generate .claude/skills/ade/ (from templates/skills/)
    _render_template_dir(env, "skills/", project_dir / ".claude" / "skills" / "ade", ctx)

    # Generate .claude/commands/*.md (from templates/commands/)
    commands_dir = project_dir / ".claude" / "commands"
    _render_template_dir(env, "commands/", commands_dir, ctx)

    # Update CLAUDE.md with ADE section
    ade_section_template = env.get_template("claude_md_section.md.j2")
    ade_section = ade_section_template.render(**ctx)
    _update_claude_md(project_dir, ade_section)

    rprint("\n[green]ADE initialized successfully![/green]")
    rprint("  Next steps:")
    rprint("    1. ade doctor          # Verify prerequisites")
    rprint("    2. claude              # Start Claude Code")
    rprint("    3. /ade-full <task>    # Run a full SDLC cycle")


@app.command()
def doctor() -> None:
    """Check that all ADE prerequisites are available."""
    all_ok = True

    required_tools = {
        "claude": "Claude Code CLI",
        "git": "Git",
    }

    optional_tools = {
        "pre-commit": "Pre-commit framework",
    }

    rprint("[bold]ADE Doctor — Checking prerequisites[/bold]\n")

    for cmd, description in required_tools.items():
        if _check_command(cmd):
            rprint(f"  [green]PASS[/green]  {description}")
        else:
            rprint(f"  [red]FAIL[/red]  {description} — '{cmd}' not found")
            all_ok = False

    for cmd, description in optional_tools.items():
        if _check_command(cmd):
            rprint(f"  [green]PASS[/green]  {description}")
        else:
            rprint(f"  [yellow]WARN[/yellow]  {description} — '{cmd}' not found (optional)")

    if all_ok:
        rprint("\n[green]All required prerequisites found.[/green]")
    else:
        rprint(
            "\n[red]Some required prerequisites are missing. Install them before using ADE.[/red]"
        )
        raise typer.Exit(1)


@app.command()
def status(
    project_dir: Annotated[Path, typer.Option(help="Project directory")] = Path("."),
) -> None:
    """Show the status of ADE tasks."""
    project_dir = project_dir.resolve()
    tasks_dir = project_dir / ".ade" / "tasks"

    if not tasks_dir.exists():
        rprint("[yellow]No .ade/tasks directory found. Run 'ade init' first.[/yellow]")
        return

    task_dirs = sorted(
        [d for d in tasks_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )

    if not task_dirs:
        rprint("No active tasks.")
        return

    table = Table(title="ADE Tasks")
    table.add_column("Task ID", style="bold")
    table.add_column("Phase")
    table.add_column("Last Updated")

    for task_dir in task_dirs:
        task_id = task_dir.name
        status_file = task_dir / "status.md"

        phase = "unknown"
        last_updated = datetime.fromtimestamp(task_dir.stat().st_mtime, tz=UTC).strftime(
            "%Y-%m-%d %H:%M"
        )

        if status_file.exists():
            content = status_file.read_text(encoding="utf-8").strip()
            # Extract phase from first non-empty line
            for line in content.splitlines():
                line = line.strip()
                if line:
                    phase = line
                    break

        table.add_row(task_id, phase, last_updated)

    rprint(table)
