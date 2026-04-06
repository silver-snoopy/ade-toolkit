"""ADE CrewAI runner — dispatches agents for SDLC phases."""

from __future__ import annotations

from pathlib import Path

import yaml
from crewai import Crew, Task

from ade.crew.agents import create_agent
from ade.crew.handoff import HandoffReport, HandoffStatus
from ade.crew.ollama import check_ollama_health, ensure_model_available
from ade.crew.progress import ProgressLogger

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_PARTIAL = 2
# Used by the orchestrator (Claude Code) when it kills the subprocess after
# the configured timeout. The runner itself does not return this code.
EXIT_TIMEOUT = 3
EXIT_ESCALATE = EXIT_TIMEOUT  # Alias per architecture spec

# Maps phases to the agent name that handles them
PHASE_AGENT_MAP: dict[str, str] = {
    "stubs": "architect",
    "code": "coder",
    "test": "tester",
    "fix": "fixer",
    "research": "researcher",
    "review_logic": "reviewer",
    "review_conventions": "reviewer",
    "review_security": "reviewer",
}

# Phase-specific task descriptions
PHASE_DESCRIPTIONS: dict[str, str] = {
    "stubs": (
        "Create file stubs and module structure based on the plan. "
        "For NEW files that don't exist yet, use mode='write' to create them with skeleton code. "
        "For EXISTING files that need modification, use mode='read' first, then mode='edit' "
        "with old_string/new_string to add imports or register new modules. "
        "NEVER use mode='write' on a file that already exists — it destroys the content."
    ),
    "code": "Implement the code according to the plan and stubs",
    "test": "Write comprehensive tests for the implemented code",
    "fix": "Fix failing tests and code issues identified by the test phase",
    "research": "Investigate existing implementation, patterns, and reusable utilities",
    "review_logic": "Review code for logic errors, edge cases, and correctness issues",
    "review_conventions": "Review code for convention violations and project pattern adherence",
    "review_security": "Review code for security vulnerabilities (OWASP top 10)",
}


def _extract_file_paths_from_md(path: Path) -> list[str]:
    """Extract backtick-quoted file paths from a markdown file."""
    files: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if "`" not in stripped:
            continue
        parts = stripped.split("`")
        for i in range(1, len(parts), 2):  # odd indices are inside backticks
            candidate = parts[i].strip()
            if "/" in candidate and "." in candidate.split("/")[-1]:
                files.append(candidate)
    return files


def _load_plan_files(task_dir: Path) -> list[str]:
    """Extract file list from plan documents.

    Checks plan.md first, then falls back to implementation-plan.md if
    plan.md yields fewer than 5 files. This handles the common case where
    a high-level plan.md has few paths but a detailed implementation plan
    lists all files.
    """
    files: list[str] = []

    plan_path = task_dir / "plan.md"
    if plan_path.exists():
        files = _extract_file_paths_from_md(plan_path)

    # If plan.md yielded few files, try implementation-plan.md
    if len(files) < 5:
        impl_path = task_dir / "implementation-plan.md"
        if impl_path.exists():
            impl_files = _extract_file_paths_from_md(impl_path)
            if len(impl_files) > len(files):
                files = impl_files

    return list(dict.fromkeys(files))  # deduplicate preserving order


def _resolve_model(agent_name: str, crew_config_dir: Path) -> str:
    """Read the model name from the agent's YAML config."""
    config_path = crew_config_dir / f"{agent_name}.yaml"
    if not config_path.exists():
        return "unknown"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    raw = config.get("model", "ollama/gemma4:31b")
    # Strip "ollama/" prefix for Ollama API calls
    return raw.removeprefix("ollama/")


def _resolve_fallback_model(config_path: str) -> str | None:
    """Read the fallback model name from .ade/config.yaml."""
    path = Path(config_path)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        fallback = config.get("models", {}).get("fallback", {})
        name = fallback.get("name") if isinstance(fallback, dict) else None
        return f"ollama/{name}" if name else None
    except (yaml.YAMLError, AttributeError):
        return None


def _check_worktree_changes(worktree_path: Path) -> bool:
    """Check if the worktree has source file changes (ignoring .ade/ bootstrapped files)."""
    import subprocess

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if not result.stdout.strip():
        return False
    # Filter out .ade/ paths — those are bootstrapped config, not agent output
    for line in result.stdout.strip().splitlines():
        # porcelain format: "XY path" or "XY path -> path"
        file_path = line[3:].split(" -> ")[0]
        if not file_path.startswith(".ade/") and not file_path.startswith(".ade\\"):
            return True
    return False


def _setup_worktree_task_dir(
    task_dir: Path, task_id: str, main_project_dir: Path | None = None
) -> None:
    """Ensure the worktree has all .ade/ files needed for agent execution.

    Copies from main project:
    - .ade/crew/*.yaml (agent configs with model names)
    - .ade/config.yaml (project config with fallback models)
    - .ade/tasks/<id>/*.md (plan, intent, and other task docs)
    """
    import shutil

    task_dir.mkdir(parents=True, exist_ok=True)

    if not main_project_dir:
        return

    main_ade = main_project_dir / ".ade"
    if not main_ade.exists():
        return

    # The worktree's .ade root (two levels up from task_dir: .ade/tasks/<id>)
    worktree_ade = task_dir.parent.parent

    # Copy crew agent configs (required for model resolution)
    main_crew = main_ade / "crew"
    if main_crew.is_dir():
        worktree_crew = worktree_ade / "crew"
        worktree_crew.mkdir(parents=True, exist_ok=True)
        for yaml_file in main_crew.glob("*.yaml"):
            dest = worktree_crew / yaml_file.name
            if not dest.exists():
                shutil.copy2(yaml_file, dest)

    # Copy project config
    main_config = main_ade / "config.yaml"
    worktree_config = worktree_ade / "config.yaml"
    if main_config.exists() and not worktree_config.exists():
        shutil.copy2(main_config, worktree_config)

    # Copy all .md files from the task directory (plan, intent, implementation-plan, etc.)
    main_task = main_ade / "tasks" / task_id
    if main_task.is_dir():
        for md_file in main_task.glob("*.md"):
            dest = task_dir / md_file.name
            if not dest.exists():
                shutil.copy2(md_file, dest)


def _load_project_context(worktree_path: Path) -> str:
    """Load project conventions from AGENTS.md or CLAUDE.md.

    Single source of truth — no duplication. If the project maintains
    AGENTS.md (cross-tool standard) or CLAUDE.md (Claude Code), the
    same file is injected into every agent's task description.

    TODO: If context rot becomes a problem with large files, add section
    filtering (e.g., only extract "Backend Conventions", "Project Structure")
    rather than loading the entire file. Fix the source, not the reader.
    """
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = worktree_path / name
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def _build_task_description(
    phase: str, task_dir: Path, plan_files: list[str], worktree_path: Path
) -> str:
    """Build a rich task description that includes plan context and file list.

    Local LLMs need explicit context — a generic one-liner like
    "create stubs based on the plan" produces no output because the
    agent doesn't know what plan or what files.
    """
    base = PHASE_DESCRIPTIONS[phase]

    # Load project conventions (AGENTS.md or CLAUDE.md)
    project_context = _load_project_context(worktree_path)

    # Read plan content (truncate to avoid blowing context)
    plan_content = ""
    for plan_name in ("plan.md", "implementation-plan.md"):
        plan_path = task_dir / plan_name
        if plan_path.exists():
            raw = plan_path.read_text(encoding="utf-8")
            # Keep first 8000 chars to fit in context
            plan_content = raw[:8000]
            break

    # Build file list section
    file_list = ""
    if plan_files:
        items = "\n".join(f"- {f}" for f in plan_files if "/" in f)
        file_list = f"\n\nFiles to create/modify:\n{items}"

    # Tool usage instructions (local LLMs need explicit guidance)
    tool_guidance = (
        "\n\nIMPORTANT TOOL USAGE RULES:\n"
        "You MUST use file_tool to create and modify files. Do NOT just describe changes.\n\n"
        "For NEW files: file_tool(path='src/new.ts', mode='write', content='full content here')\n\n"
        "For EXISTING files: NEVER use mode='write' — it destroys the file. Instead:\n"
        "1. Read the file: file_tool(path='src/existing.ts', mode='read')\n"
        "2. Edit it: file_tool(path='src/existing.ts', mode='edit', "
        "old_string='exact text to replace', new_string='replacement text')\n"
        "3. You can make multiple edits to the same file by calling edit multiple times.\n\n"
        "The old_string MUST match exactly (including whitespace and newlines). "
        "If it doesn't match, you'll get an error — read the file again and retry."
    )

    # Assemble: base + project conventions + plan + file list + tool guidance
    sections = [base]
    if project_context:
        sections.append(f"\n\n--- PROJECT CONVENTIONS ---\n{project_context}\n--- END CONVENTIONS ---")
    if plan_content:
        sections.append(f"\n\n--- PLAN ---\n{plan_content}\n--- END PLAN ---")
    sections.append(file_list)
    sections.append(tool_guidance)
    return "".join(sections)


def run(
    phase: str,
    task_id: str,
    worktree: str,
    config_path: str = ".ade/config.yaml",
    main_project_dir: str | None = None,
) -> int:
    """Run a CrewAI phase. Returns exit code."""
    worktree_path = Path(worktree)
    task_dir = worktree_path / ".ade" / "tasks" / task_id
    crew_config_dir = worktree_path / ".ade" / "crew"

    # Ensure task dir exists in worktree (Bug 2: .ade is gitignored)
    _setup_worktree_task_dir(
        task_dir,
        task_id,
        Path(main_project_dir) if main_project_dir else None,
    )

    progress = ProgressLogger(task_dir=task_dir)

    # Validate phase
    if phase not in PHASE_AGENT_MAP:
        progress.log(
            phase=phase,
            agent="runner",
            step="0/4",
            file="",
            status=f"invalid phase: {phase}",
        )
        return EXIT_FAILURE

    agent_name = PHASE_AGENT_MAP[phase]
    model_name = _resolve_model(agent_name, crew_config_dir)

    # Create handoff report for structured logging
    handoff = HandoffReport(
        task_id=task_id,
        phase=phase,
        agent_name=agent_name,
        model=model_name,
    )

    # Step 1: Check Ollama health
    progress.log(phase=phase, agent="runner", step="1/4", file="", status="checking ollama")
    if not check_ollama_health():
        progress.log(
            phase=phase,
            agent="runner",
            step="1/4",
            file="",
            status="ollama not running",
        )
        handoff.fail(HandoffStatus.OLLAMA_DOWN, "Ollama service is not responding")
        handoff.save(task_dir)
        return EXIT_FAILURE

    # Step 2: Verify model availability
    progress.log(
        phase=phase, agent="runner", step="2/4", file="", status=f"checking model {model_name}"
    )
    if not ensure_model_available(model_name):
        progress.log(
            phase=phase,
            agent="runner",
            step="2/4",
            file="",
            status=f"model not found: {model_name}",
        )
        handoff.fail(
            HandoffStatus.MODEL_NOT_FOUND,
            f"Model '{model_name}' is not available in Ollama",
        )
        handoff.save(task_dir)
        return EXIT_FAILURE

    # Load plan files
    plan_files = _load_plan_files(task_dir)

    # Step 3: Create agent
    progress.log(
        phase=phase,
        agent="runner",
        step="3/4",
        file="",
        status=f"creating {agent_name} agent",
    )
    try:
        agent = create_agent(
            agent_name=agent_name,
            config_dir=crew_config_dir,
            worktree_path=worktree_path,
            plan_files=plan_files,
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError) as e:
        progress.log(phase=phase, agent="runner", step="3/4", file="", status=f"error: {e}")
        handoff.fail(HandoffStatus.AGENT_CONFIG_ERROR, str(e))
        handoff.save(task_dir)
        return EXIT_FAILURE

    # Step 4: Execute crew
    progress.log(phase=phase, agent="runner", step="4/4", file="", status="running crew")
    try:
        task_description = _build_task_description(phase, task_dir, plan_files, worktree_path)
        task = Task(
            description=task_description,
            expected_output=f"Completed {phase} phase successfully",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        crew.kickoff()

        # Detect silent failures: agent "completed" but produced no file changes
        if phase in ("stubs", "code", "fix") and not _check_worktree_changes(worktree_path):
            progress.log(
                phase=phase,
                agent=agent_name,
                step="4/4",
                file="",
                status="WARNING: agent completed but produced no file changes",
            )

            # Attempt fallback model retry
            fallback_model = _resolve_fallback_model(config_path)
            if fallback_model:
                fallback_name = fallback_model.removeprefix("ollama/")
                progress.log(
                    phase=phase,
                    agent="runner",
                    step="4/4",
                    file="",
                    status=f"retrying with fallback model {fallback_name}",
                )
                try:
                    fallback_agent = create_agent(
                        agent_name=agent_name,
                        config_dir=crew_config_dir,
                        worktree_path=worktree_path,
                        plan_files=plan_files,
                        model_override=fallback_model,
                    )
                    retry_task = Task(
                        description=PHASE_DESCRIPTIONS[phase],
                        expected_output=f"Completed {phase} phase successfully",
                        agent=fallback_agent,
                    )
                    retry_crew = Crew(agents=[fallback_agent], tasks=[retry_task], verbose=False)
                    retry_crew.kickoff()

                    if _check_worktree_changes(worktree_path):
                        progress.log(
                            phase=phase,
                            agent=agent_name,
                            step="4/4",
                            file="",
                            status=f"fallback model {fallback_name} succeeded",
                        )
                        handoff.complete()
                        handoff.save(task_dir)
                        return EXIT_SUCCESS
                except Exception as fallback_err:
                    progress.log(
                        phase=phase,
                        agent=agent_name,
                        step="4/4",
                        file="",
                        status=f"fallback model also failed: {fallback_err}",
                    )

            handoff.fail(
                HandoffStatus.EXECUTION_ERROR,
                "Agent completed without producing any file changes. "
                "Check if plan_files were parsed correctly or if writes were blocked.",
            )
            handoff.save(task_dir)
            return EXIT_PARTIAL

        progress.log(phase=phase, agent=agent_name, step="4/4", file="", status="complete")
        handoff.complete()
        handoff.save(task_dir)
        return EXIT_SUCCESS
    except Exception as e:
        error_msg = str(e)
        progress.log(
            phase=phase,
            agent=agent_name,
            step="4/4",
            file="",
            status=f"error: {error_msg}",
        )
        if "max iterations" in error_msg.lower():
            handoff.fail(HandoffStatus.MAX_ITERATIONS, error_msg)
            handoff.save(task_dir)
            return EXIT_PARTIAL
        handoff.fail(HandoffStatus.EXECUTION_ERROR, error_msg)
        handoff.save(task_dir)
        return EXIT_FAILURE
