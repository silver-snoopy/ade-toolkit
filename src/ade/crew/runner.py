"""ADE CrewAI runner — dispatches agents for SDLC phases."""

from __future__ import annotations

from pathlib import Path

from crewai import Crew, Task

from ade.crew.agents import create_agent
from ade.crew.ollama import check_ollama_health
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
}

# Phase-specific task descriptions
PHASE_DESCRIPTIONS: dict[str, str] = {
    "stubs": "Create file stubs and module structure based on the plan",
    "code": "Implement the code according to the plan and stubs",
    "test": "Write comprehensive tests for the implemented code",
    "fix": "Fix failing tests and code issues identified by the test phase",
}


def _load_plan_files(task_dir: Path) -> list[str]:
    """Extract file list from plan.md in the task directory."""
    plan_path = task_dir / "plan.md"
    if not plan_path.exists():
        return []

    files: list[str] = []
    in_files_section = False
    for line in plan_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("## files") or stripped.lower().startswith("**files"):
            in_files_section = True
            continue
        if in_files_section and stripped.startswith("##"):
            break
        if in_files_section and stripped.startswith("- ") and "`" in stripped:
            # Extract file path from lines like "- Create: `src/foo.py`" or "- `src/foo.py`"
            path = stripped.split("`")[1]
            files.append(path)
    return files


def run(
    phase: str,
    task_id: str,
    worktree: str,
    config_path: str = ".ade/config.yaml",
) -> int:
    """Run a CrewAI phase. Returns exit code."""
    worktree_path = Path(worktree)
    task_dir = worktree_path / ".ade" / "tasks" / task_id
    crew_config_dir = worktree_path / ".ade" / "crew"

    progress = ProgressLogger(task_dir=task_dir)

    # Validate phase
    if phase not in PHASE_AGENT_MAP:
        progress.log(
            phase=phase,
            agent="runner",
            step="0/3",
            file="",
            status=f"invalid phase: {phase}",
        )
        return EXIT_FAILURE

    agent_name = PHASE_AGENT_MAP[phase]

    # Check Ollama health
    progress.log(phase=phase, agent="runner", step="1/3", file="", status="checking ollama")
    if not check_ollama_health():
        progress.log(
            phase=phase,
            agent="runner",
            step="1/3",
            file="",
            status="ollama not running",
        )
        return EXIT_FAILURE

    # Load plan files
    plan_files = _load_plan_files(task_dir)

    # Create agent
    progress.log(
        phase=phase,
        agent="runner",
        step="2/3",
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
        progress.log(phase=phase, agent="runner", step="2/3", file="", status=f"error: {e}")
        return EXIT_FAILURE

    # Create and run crew
    progress.log(phase=phase, agent="runner", step="3/3", file="", status="running crew")
    try:
        task = Task(
            description=PHASE_DESCRIPTIONS[phase],
            expected_output=f"Completed {phase} phase successfully",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], verbose=False)
        crew.kickoff()
        progress.log(phase=phase, agent=agent_name, step="3/3", file="", status="complete")
        return EXIT_SUCCESS
    except Exception as e:
        error_msg = str(e)
        progress.log(
            phase=phase,
            agent=agent_name,
            step="3/3",
            file="",
            status=f"error: {error_msg}",
        )
        if "max iterations" in error_msg.lower():
            return EXIT_PARTIAL
        return EXIT_FAILURE
