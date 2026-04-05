"""ADE CLI — scaffolding tool for Agentic Development Environment."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from jinja2 import Environment, PackageLoader
from rich import print as rprint

from ade.config import build_config
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
            # Already has ADE section — skip
            return
        # Append ADE section
        content = existing.rstrip() + "\n\n" + ade_section
    else:
        content = ade_section

    claude_md.write_text(content, encoding="utf-8")


def _check_command(name: str) -> bool:
    """Check if a command is available on PATH."""
    return shutil.which(name) is not None


def _check_ollama_models(required: list[str]) -> list[str]:
    """Check which required Ollama models are missing. Returns missing model names."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return required
        # Parse model names from first column of ollama list output
        installed_models = set()
        for line in result.stdout.strip().splitlines()[1:]:  # Skip header
            if line.strip():
                installed_models.add(line.split()[0])
        return [m for m in required if m not in installed_models]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return required


@app.command()
def doctor() -> None:
    """Check that all ADE dependencies are available."""
    all_ok = True

    required_tools = {
        "ollama": "Ollama (local LLM runtime)",
        "claude": "Claude Code CLI",
        "pre-commit": "Pre-commit framework",
        "git": "Git",
    }

    optional_tools = {
        "ruff": "Ruff (Python linting)",
        "semgrep": "Semgrep (SAST scanning)",
    }

    rprint("[bold]ADE Doctor — Checking dependencies[/bold]\n")

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

    # Check Ollama models
    required_models = ["gemma4:31b", "qwen2.5-coder:14b", "qwen2.5-coder:32b"]
    missing = _check_ollama_models(required_models)
    if missing:
        rprint(f"\n  [yellow]WARN[/yellow]  Missing Ollama models: {', '.join(missing)}")
        rprint("    Install with: " + " && ".join(f"ollama pull {m}" for m in missing))
    else:
        rprint("  [green]PASS[/green]  All required Ollama models available")

    if all_ok:
        rprint("\n[green]All required dependencies found.[/green]")
    else:
        rprint(
            "\n[red]Some required dependencies are missing. Install them before using ADE.[/red]"
        )
        raise typer.Exit(1)


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

    # Build config
    config = build_config(info)
    env = _get_template_env()
    ctx = {"config": config, "info": info}

    # Generate .ade/ directory
    ade_dir = project_dir / ".ade"
    _write_file(ade_dir / "config.yaml", config.to_yaml())
    _render_and_write(env, "ade_gitignore.j2", ade_dir / ".gitignore", ctx)

    # Generate CrewAI agent definitions
    for agent in ["architect", "coder", "tester", "fixer"]:
        _render_and_write(env, f"crew/{agent}.yaml.j2", ade_dir / "crew" / f"{agent}.yaml", ctx)

    # Generate Ollama Modelfiles
    for mf in ["gemma4_ade", "qwen_test_ade", "qwen_fallback_ade"]:
        _render_and_write(
            env,
            f"modelfiles/{mf}.j2",
            ade_dir / "modelfiles" / f"Modelfile.{mf.replace('_', '-')}",
            ctx,
        )

    # Generate .pre-commit-config.yaml
    _render_and_write(
        env, "pre_commit_config.yaml.j2", project_dir / ".pre-commit-config.yaml", ctx
    )

    # Generate .claude/ commands
    commands_dir = project_dir / ".claude" / "commands"
    for cmd in ["ade_full", "ade_plan", "ade_code", "ade_review", "ade_status"]:
        dest_name = cmd.replace("_", "-") + ".md"
        _render_and_write(env, f"commands/{cmd}.md.j2", commands_dir / dest_name, ctx)

    # Generate .claude/settings.json
    _render_and_write(env, "settings_json.j2", project_dir / ".claude" / "settings.json", ctx)

    # Update CLAUDE.md
    ade_section_template = env.get_template("claude_md_section.md.j2")
    ade_section = ade_section_template.render(**ctx)
    _update_claude_md(project_dir, ade_section)

    rprint("\n[green]ADE initialized successfully![/green]")
    rprint("  Next steps:")
    rprint("    1. pre-commit install")
    rprint("    2. ade doctor          # Verify dependencies")
    rprint("    3. claude              # Start Claude Code")
    rprint("    4. /ade-full <task>    # Run a full SDLC cycle")
