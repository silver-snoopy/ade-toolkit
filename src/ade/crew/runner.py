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
    "stubs": "Create file stubs and module structure based on the plan",
    "code": "Implement the code according to the plan and stubs",
    "test": "Write comprehensive tests for the implemented code",
    "fix": "Fix failing tests and code issues identified by the test phase",
    "research": "Investigate existing implementation, patterns, and reusable utilities",
    "review_logic": "Review code for logic errors, edge cases, and correctness issues",
    "review_conventions": "Review code for convention violations and project pattern adherence",
    "review_security": "Review code for security vulnerabilities (OWASP top 10)",
}


def _load_plan_files(task_dir: Path) -> list[str]:
    """Extract file list from plan.md — supports bullet lists, tables, and inline backticks."""
    plan_path = task_dir / "plan.md"
    if not plan_path.exists():
        return []

    files: list[str] = []
    for line in plan_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if "`" not in stripped:
            continue
        # Extract all backtick-quoted strings and check if they look like file paths
        parts = stripped.split("`")
        for i in range(1, len(parts), 2):  # odd indices are inside backticks
            candidate = parts[i].strip()
            if "/" in candidate and "." in candidate.split("/")[-1]:
                files.append(candidate)
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
    """Check if the worktree has uncommitted changes (new or modified files)."""
    import subprocess

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return bool(result.stdout.strip())


def _setup_worktree_task_dir(
    task_dir: Path, task_id: str, main_project_dir: Path | None = None
) -> None:
    """Ensure the task directory exists in the worktree, copying plan from main if needed."""
    task_dir.mkdir(parents=True, exist_ok=True)

    # Copy plan.md from main project .ade if it exists and worktree doesn't have it
    if main_project_dir and not (task_dir / "plan.md").exists():
        main_plan = main_project_dir / ".ade" / "tasks" / task_id / "plan.md"
        if main_plan.exists():
            import shutil

            shutil.copy2(main_plan, task_dir / "plan.md")

    # Copy intent.md similarly
    if main_project_dir and not (task_dir / "intent.md").exists():
        main_intent = main_project_dir / ".ade" / "tasks" / task_id / "intent.md"
        if main_intent.exists():
            import shutil

            shutil.copy2(main_intent, task_dir / "intent.md")


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
        task = Task(
            description=PHASE_DESCRIPTIONS[phase],
            expected_output=f"Completed {phase} phase successfully",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], verbose=False)
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
