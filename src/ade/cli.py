"""ADE CLI — scaffolding tool for Agentic Development Environment."""

from __future__ import annotations

import copy
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from jinja2 import Environment, PackageLoader
from rich import print as rprint
from rich.table import Table

from ade.detect import detect_project, normalize_language
from ade.harnesses import selected_targets

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


def _render_hooks(env: Environment, hooks_dir: Path, context: dict) -> None:
    """Render the deterministic hook scripts, preserving exact filenames.

    Rendered explicitly (not via _render_template_dir) so the leading-underscore
    helper `_hooklib.py` is not mangled into a dashed name.
    """
    for name in (
        "_hooklib.py",
        "block-mixed-commit.py",
        "check-leftover-stub.py",
        "check-escalation-paths.py",
    ):
        _render_and_write(env, f"hooks/{name}.j2", hooks_dir / name, context)


def _merge_hooks(current: dict, ade: dict) -> dict:
    """Idempotently merge ADE PreToolUse hook commands into an existing settings dict."""
    merged = copy.deepcopy(current)
    hooks = merged.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        merged["hooks"] = hooks
    for event, blocks in ade.get("hooks", {}).items():
        existing_blocks = hooks.setdefault(event, [])
        for ade_block in blocks:
            target = next(
                (b for b in existing_blocks if b.get("matcher") == ade_block.get("matcher")),
                None,
            )
            if target is None:
                existing_blocks.append(ade_block)
                continue
            target_hooks = target.setdefault("hooks", [])
            seen = {h.get("command") for h in target_hooks}
            for hook in ade_block.get("hooks", []):
                if hook.get("command") not in seen:
                    target_hooks.append(hook)
    return merged


def _emit_claude_hooks(env: Environment, project_dir: Path, context: dict) -> str:
    """Create or idempotently merge .claude/settings.json hooks. Returns action word."""
    dest = project_dir / ".claude" / "settings.json"
    ade_settings = json.loads(env.get_template("claude_settings.json.j2").render(**context))
    if dest.exists():
        try:
            current = json.loads(dest.read_text(encoding="utf-8"))
            if not isinstance(current, dict):
                current = {}
        except json.JSONDecodeError:
            current = {}
        merged = _merge_hooks(current, ade_settings)
        action = "Merged hooks into"
    else:
        merged = ade_settings
        action = "Created"
    _write_file(dest, json.dumps(merged, indent=2) + "\n")
    return action


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

    if agent == "copilot":
        legacy_copilot = True
        targets = selected_targets("claude")  # v2 shim: Claude tree + pre-commit  # noqa: F841
    else:
        legacy_copilot = False
        try:
            targets = selected_targets(agent)  # noqa: F841
        except KeyError as exc:
            rprint(f"[red]Error: unknown --agent value: {exc}[/red]")
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

    # Deterministic commit hooks (G1/G2) — scripts always emitted to the committed
    # .claude/hooks/ dir so they exist inside git worktrees; wiring is mode-specific.
    _render_hooks(env, project_dir / ".claude" / "hooks", ctx)

    if not legacy_copilot:
        action = _emit_claude_hooks(env, project_dir, ctx)
        rprint(f"  [green]+[/green] {action} .claude/settings.json (hook wiring)")
    else:  # legacy copilot (v2 pre-commit path)
        created = _render_and_write_if_missing(
            env, "pre-commit-config.yaml.j2", project_dir / ".pre-commit-config.yaml", ctx
        )
        if created:
            rprint("  [green]+[/green] Created .pre-commit-config.yaml")
            rprint(
                "    [dim]run: pre-commit install"
                " --hook-type pre-commit --hook-type commit-msg[/dim]"
            )
        else:
            rprint("  [dim]= Kept existing .pre-commit-config.yaml[/dim]")
            rprint("    [dim]Add the ADE `repo: local` hooks block manually — see docs.[/dim]")

    # Seed .claude/ade-stack.md (G5b) — ADE-tooling config, seed-if-missing, user-owned.
    stack_dest = project_dir / ".claude" / "ade-stack.md"
    if _render_and_write_if_missing(env, "stack.md.j2", stack_dest, ctx):
        rprint("  [green]+[/green] Created .claude/ade-stack.md")
    else:
        rprint("  [dim]= Kept existing .claude/ade-stack.md[/dim]")

    # Seed .claude/ade-routing.json (G4) — routing config, seed-if-missing, user-owned.
    routing_dest = project_dir / ".claude" / "ade-routing.json"
    if _render_and_write_if_missing(env, "ade-routing.json.j2", routing_dest, ctx):
        rprint("  [green]+[/green] Created .claude/ade-routing.json")
    else:
        rprint("  [dim]= Kept existing .claude/ade-routing.json[/dim]")

    # Update CLAUDE.md with ADE section
    ade_section_template = env.get_template("claude_md_section.md.j2")
    ade_section = ade_section_template.render(**ctx)
    _update_claude_md(project_dir, ade_section)

    # Bootstrap project artifacts (CONTEXT.md glossary, docs/adr/, docs/specs/).
    # These are user-owned project artifacts ADE seeds at init time but never
    # overwrites afterward — grill-with-docs and the Research phase populate
    # them incrementally during normal use.
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
    for template_name, dest in bootstrap_targets:
        created = _render_and_write_if_missing(env, template_name, dest, ctx)
        rel = dest.relative_to(project_dir)
        if created:
            rprint(f"  [green]+[/green] Created {rel}")
        else:
            rprint(f"  [dim]= Kept existing {rel}[/dim]")

    rprint("\n[green]ADE initialized successfully![/green]")
    rprint("  Next steps:")
    rprint("    1. ade doctor          # Verify prerequisites")
    rprint("    2. claude              # Start Claude Code")
    rprint("    3. /ade-full <task>    # Run a full SDLC cycle")


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
        (".claude/skills/ade", "ADE skills directory"),
        (".claude/agents/scout.md", "Scout agent (R2.1)"),
        (".claude/agents/synthesizer.md", "Synthesizer agent (R3.1, R5)"),
        (".claude/agents/spec-verifier.md", "Spec-verifier agent (R5 CoVe)"),
        (".claude/agents/web-researcher.md", "Web-researcher agent (R2.3)"),
        (
            ".claude/skills/ade/vendored/mattpocock-grill-with-docs/SKILL.md",
            "Vendored grill-with-docs skill (R4)",
        ),
        (".claude/skills/ade/phases/01-research.md", "Research phase skill"),
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
