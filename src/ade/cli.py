"""ADE CLI — scaffolding tool for Agentic Development Environment."""

from __future__ import annotations

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from jinja2 import Environment, PackageLoader
from rich import print as rprint
from rich.table import Table

from ade.detect import detect_project, normalize_language
from ade.harnesses import TARGETS, HarnessTarget, selected_targets
from ade.harnesses.hooks import emit_hooks
from ade.harnesses.memory import emit_memory_pointer
from ade.harnesses.workers import render_worker

app = typer.Typer(
    name="ade",
    help="ADE — Agentic Development Environment toolkit",
    no_args_is_help=True,
)


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


def _render_and_write_if_missing(
    env: Environment, template_name: str, dest: Path, context: dict
) -> bool:
    """Render a template only if the destination does not already exist.

    Returns True if the file was created, False if it already existed.
    Used for project artifacts (CONTEXT.md, ADRs) that ADE seeds but the
    user owns thereafter — never overwrite existing content.
    """
    if dest.exists():
        return False
    _render_and_write(env, template_name, dest, context)
    return True


def _check_command(name: str) -> bool:
    """Check if a command is available on PATH."""
    return shutil.which(name) is not None


def _emit_workers(
    targets: list[HarnessTarget], env: Environment, project_dir: Path, ctx: dict
) -> None:
    """Render every templates/agents/*.md.j2 into each target's workers_dir."""
    worker_names = [
        t[len("agents/") : -len(".md.j2")]
        for t in env.loader.list_templates()
        if t.startswith("agents/") and t.endswith(".md.j2")
    ]
    for target in targets:
        for name in worker_names:
            rel, content = render_worker(target, env, name, ctx)
            _write_file(project_dir / rel, content)


def _emit_skills(
    targets: list[HarnessTarget], env: Environment, project_dir: Path, ctx: dict
) -> None:
    """Render every templates/skills/<skill>/** file into each target's skills dirs.

    SKILL.md content is identical on every harness; only the destination dirs differ.
    Each unique dir across the selected targets is written once.
    """
    dest_dirs = {d for t in targets for d in t.skills_dirs}
    prefix = "skills/"
    for template_name in env.loader.list_templates():
        if not template_name.startswith(prefix) or not template_name.endswith(".j2"):
            continue
        rel = template_name[len(prefix) : -len(".j2")]  # e.g. "ade-implement/SKILL.md"
        for d in dest_dirs:
            _render_and_write(env, template_name, project_dir / d / rel, ctx)


def _seed_config(env: Environment, project_dir: Path, ctx: dict) -> list[tuple[str, Path]]:
    """Seed .ade/ routing and stack config files (seed-if-missing, user-owned).

    Returns a list of (action, path) pairs for progress reporting.
    """
    results: list[tuple[str, Path]] = []
    stack_dest = project_dir / ".ade" / "ade-stack.md"
    if _render_and_write_if_missing(env, "stack.md.j2", stack_dest, ctx):
        results.append(("created", stack_dest))
    else:
        results.append(("kept", stack_dest))

    routing_dest = project_dir / ".ade" / "ade-routing.json"
    if _render_and_write_if_missing(env, "ade-routing.json.j2", routing_dest, ctx):
        results.append(("created", routing_dest))
    else:
        results.append(("kept", routing_dest))

    return results


def _seed_bootstrap(env: Environment, project_dir: Path, ctx: dict) -> list[tuple[str, Path]]:
    """Seed project bootstrap artifacts (CONTEXT.md, docs/adr, etc.) — seed-if-missing.

    Returns a list of (action, path) pairs for progress reporting.
    """
    bootstrap_targets = [
        ("bootstrap/CONTEXT.md.j2", project_dir / "CONTEXT.md"),
        (
            "bootstrap/adr-0001-record-architecture-decisions.md.j2",
            project_dir / "docs" / "adr" / "0001-record-architecture-decisions.md",
        ),
        ("bootstrap/specs-README.md.j2", project_dir / "docs" / "specs" / "README.md"),
        ("bootstrap/learnings-README.md.j2", project_dir / "docs" / "learnings" / "README.md"),
        ("bootstrap/review-calibration.md.j2", project_dir / "docs" / "review-calibration.md"),
    ]
    results: list[tuple[str, Path]] = []
    for template_name, dest in bootstrap_targets:
        created = _render_and_write_if_missing(env, template_name, dest, ctx)
        results.append(("created" if created else "kept", dest))
    return results


def _emit_v3(
    targets: list[HarnessTarget],
    env: Environment,
    project_dir: Path,
    info: object,
    ctx: dict,
) -> None:
    """Emit the full v3 tree for the selected targets (excluding hook wiring).

    Used by both init() and migrate(). Hook wiring is handled by the callers
    so that each target is wired independently.
    """
    _render_and_write(env, "ade_gitignore.j2", project_dir / ".ade" / ".gitignore", ctx)
    _emit_skills(targets, env, project_dir, ctx)
    _emit_workers(targets, env, project_dir, ctx)
    _render_and_write(env, "AGENTS.md.j2", project_dir / "AGENTS.md", ctx)
    for target in targets:
        emit_memory_pointer(target, env, project_dir, ctx)
    _seed_config(env, project_dir, ctx)
    _seed_bootstrap(env, project_dir, ctx)


_OLD_ADE_SECTION_RE = re.compile(
    r"(?ms)^##\s+ADE — Agentic Development Environment.*?(?=^##\s|\Z)"
)
_V3_ADE_BLOCK_RE = re.compile(r"(?ms)<!--\s*ADE:START\s*-->.*?<!--\s*ADE:END\s*-->\n?")


def _strip_old_claude_section(md_path: Path) -> None:
    """Remove any ADE-owned section from CLAUDE.md, preserving all other content.

    Strips both the old v2 ``## ADE — Agentic Development Environment`` heading
    section and the v3 ``<!-- ADE:START -->...<!-- ADE:END -->`` delimited block so
    that ``emit_memory_pointer`` can write a fresh, single copy.
    """
    if not md_path.exists():
        return
    text = md_path.read_text(encoding="utf-8")
    # Strip v3 delimited block first (avoids partial regex matches below).
    text = _V3_ADE_BLOCK_RE.sub("", text)
    # Strip old v2 heading section (anything left after the v3 removal).
    text = _OLD_ADE_SECTION_RE.sub("", text).rstrip() + "\n"
    md_path.write_text(text, encoding="utf-8")


@app.command()
def migrate(
    project_dir: Annotated[Path, typer.Option(help="Project directory to migrate")] = Path("."),
    agent: Annotated[str, typer.Option(help="Target harness(es): list or 'all'")] = "claude",
) -> None:
    """Upgrade a v2 ADE tree to the v3 layout (idempotent)."""
    project_dir = project_dir.resolve()
    targets = selected_targets(agent)
    info = detect_project(project_dir)
    env = _get_template_env()
    ctx = {"info": info}

    # 1. Move user-owned config (preserve edits: only if dest missing).
    for src_rel, dst_rel in (
        (".claude/ade-routing.json", ".ade/ade-routing.json"),
        (".claude/ade-stack.md", ".ade/ade-stack.md"),
    ):
        src, dst = project_dir / src_rel, project_dir / dst_rel
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

    # 2. Remove stale generated trees.
    shutil.rmtree(project_dir / ".claude" / "skills" / "ade", ignore_errors=True)
    shutil.rmtree(project_dir / ".claude" / "commands", ignore_errors=True)

    # 3. Strip the old CLAUDE.md ADE section, then re-emit v3 (pointer replaces it).
    _strip_old_claude_section(project_dir / "CLAUDE.md")
    _emit_v3(targets, env, project_dir, info, ctx)
    for target in targets:
        emit_hooks(target, env, project_dir, ctx)

    rprint("[green]Migrated to ADE v3 layout.[/green]")


@app.command()
def init(
    project_dir: Annotated[Path, typer.Option(help="Project directory to initialize")] = Path("."),
    language: Annotated[
        str | None,
        typer.Option(help="Override detected languages (comma-separated)"),
    ] = None,
    agent: Annotated[
        str,
        typer.Option(help="Target agent for hook wiring: 'claude' or 'copilot'"),
    ] = "claude",
) -> None:
    """Initialize ADE in the current project."""
    project_dir = project_dir.resolve()

    if not project_dir.is_dir():
        rprint(f"[red]Error: {project_dir} is not a directory[/red]")
        raise typer.Exit(1)

    # Nudge users with an existing v2 tree to run migrate instead.
    if (project_dir / ".claude" / "skills" / "ade").exists() or (
        project_dir / ".claude" / "commands"
    ).exists():
        rprint("[yellow]Detected a v2 ADE tree. Run `ade migrate` to upgrade.[/yellow]")

    try:
        targets = selected_targets(agent)
    except KeyError as exc:
        valid = ", ".join(sorted(TARGETS))
        rprint(f"[red]Error: unknown --agent value {exc}. Valid: {valid}, or 'all'.[/red]")
        raise typer.Exit(1) from exc

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

    # Emit the full v3 tree (skills, workers, AGENTS.md, memory pointer, config seeds,
    # bootstrap seeds) then wire deterministic hooks per target.
    _emit_v3(targets, env, project_dir, info, ctx)

    for target in targets:
        action = emit_hooks(target, env, project_dir, ctx)
        rprint(f"  [green]+[/green] {action} {target.name} hooks")

    rprint("\n[green]ADE initialized successfully![/green]")
    rprint("  Next steps:")
    rprint("    1. ade doctor          # Verify prerequisites")
    rprint("    2. claude              # Start Claude Code")
    rprint("    3. ade-pipeline skill (run a full SDLC cycle)")


@app.command()
def doctor(
    project_dir: Annotated[Path, typer.Option(help="Project directory to check")] = Path("."),
) -> None:
    """Check ADE prerequisites and project state."""
    project_dir = project_dir.resolve()
    all_ok = True
    warnings = 0

    rprint("[bold]ADE Doctor — Checking prerequisites[/bold]\n")

    # 1. External tools (PATH)
    rprint("[bold]External tools[/bold]")
    required_tools = {
        "claude": "Claude Code CLI",
        "git": "Git",
    }
    optional_tools = {
        "pre-commit": "Pre-commit framework",
    }

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
            warnings += 1

    # 2. Project state (generated by `ade init`)
    rprint(f"\n[bold]Project state[/bold] [dim](in {project_dir})[/dim]")

    # Required: ADE-generated files. Their absence means `ade init` was not run
    # (or the generated tree was deleted). Recovery is a single command.
    required_paths = [
        (".claude/skills", "ADE skills directory"),
        (".claude/agents/scout.md", "Scout agent (R2.1)"),
        (".claude/agents/synthesizer.md", "Synthesizer agent (R3.1, R5)"),
        (".claude/agents/spec-verifier.md", "Spec-verifier agent (R5 CoVe)"),
        (".claude/agents/web-researcher.md", "Web-researcher agent (R2.3)"),
        (".claude/skills/grill-with-docs/SKILL.md", "Vendored grill-with-docs skill (R4)"),
        (".claude/skills/ade-research/SKILL.md", "Research phase skill"),
        (".claude/hooks/_hooklib.py", "Hook library: _hooklib (G1/G2 dependency)"),
        (".claude/hooks/block-mixed-commit.py", "Commit hook: block-mixed-commit (G1)"),
        (".claude/hooks/check-leftover-stub.py", "Commit hook: check-leftover-stub (G2)"),
        (".claude/hooks/check-escalation-paths.py", "Commit hook: check-escalation-paths (G4)"),
    ]
    project_initialized = True
    for rel, description in required_paths:
        path = project_dir / rel
        if path.exists():
            rprint(f"  [green]PASS[/green]  {description}")
        else:
            rprint(f"  [red]FAIL[/red]  {description} — missing {rel}")
            project_initialized = False
            all_ok = False

    if not project_initialized:
        rprint("  [dim]-> run `ade init` to (re)generate ADE templates[/dim]")

    # Bootstrap artifacts: user-owned. WARN (not FAIL) if missing —
    # they're seeded by `ade init` but the user may have intentionally
    # removed or restructured them.
    bootstrap_paths = [
        ("CONTEXT.md", "Domain glossary (CONTEXT.md)"),
        ("docs/adr", "ADR directory (docs/adr/)"),
        ("docs/specs", "Specs directory (docs/specs/)"),
        ("docs/learnings", "Learnings directory (docs/learnings/)"),
        ("docs/review-calibration.md", "Review calibration corpus (docs/review-calibration.md)"),
    ]
    for rel, description in bootstrap_paths:
        path = project_dir / rel
        if path.exists():
            rprint(f"  [green]PASS[/green]  {description}")
        else:
            rprint(f"  [yellow]WARN[/yellow]  {description} — missing at {rel}")
            warnings += 1

    # Hook wiring nudge (mode is inferred from which wiring file exists).
    if (project_dir / ".pre-commit-config.yaml").exists():
        if _check_command("pre-commit"):
            rprint(
                "  [dim]copilot hook wiring detected — ensure hooks are installed:\n"
                "    pre-commit install --hook-type pre-commit --hook-type commit-msg[/dim]"
            )
        else:
            rprint(
                "  [yellow]WARN[/yellow]  .pre-commit-config.yaml present"
                " but 'pre-commit' not installed"
            )
            warnings += 1

    # 3. Peer plugins (recommended, not detected)
    rprint("\n[bold]Recommended Claude Code plugins[/bold]")
    rprint(
        "  [dim]ADE phases reference these as preferred mechanisms.[/dim]\n"
        "  [dim]Phase still works without them via inline fallbacks, but quality is lower.[/dim]"
    )
    peer_plugins = [
        (
            "pr-review-toolkit",
            "Multi-agent PR review (Phase 6 — Review)",
            "/plugin marketplace add anthropics/claude-code"
            "  &&  /plugin install pr-review-toolkit",
        ),
    ]
    for name, purpose, install_hint in peer_plugins:
        rprint(f"  [cyan]?[/cyan]     [bold]{name}[/bold] — {purpose}")
        rprint(f"          [dim]install: {install_hint}[/dim]")

    # Summary
    rprint()
    if all_ok:
        if warnings:
            rprint(f"[yellow]All required checks pass with {warnings} warning(s).[/yellow]")
        else:
            rprint("[green]All checks pass.[/green]")
    else:
        rprint("[red]Required checks failed. Fix issues above before running ADE workflows.[/red]")
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
