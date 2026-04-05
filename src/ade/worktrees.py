"""Git worktree manager — create, list, remove isolated task workspaces."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("ade.worktrees")


@dataclass(frozen=True)
class WorktreeInfo:
    path: Path
    branch: str
    task_id: str | None = None


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command with timeout and clear error handling."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "git is not installed or not on PATH. Run 'ade doctor' to check dependencies."
        ) from None
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git {args[0]} timed out after 30 seconds") from None


def create_worktree(project_dir: Path, task_id: str) -> WorktreeInfo:
    """Create a git worktree for a task in .ade/worktrees/<task_id>."""
    worktree_path = project_dir / ".ade" / "worktrees" / task_id
    branch = f"ade/{task_id}"

    result = _run_git(["worktree", "add", str(worktree_path), "-b", branch], cwd=project_dir)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create worktree: {result.stderr.strip()}")

    return WorktreeInfo(path=worktree_path, branch=branch, task_id=task_id)


def remove_worktree(project_dir: Path, task_id: str) -> None:
    """Remove a task's worktree and clean up its branch."""
    worktree_path = project_dir / ".ade" / "worktrees" / task_id

    if not worktree_path.exists():
        raise FileNotFoundError(f"Worktree not found: {task_id}")

    result = _run_git(["worktree", "remove", str(worktree_path), "--force"], cwd=project_dir)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to remove worktree: {result.stderr.strip()}")

    # Best-effort branch cleanup
    branch_result = _run_git(["branch", "-D", f"ade/{task_id}"], cwd=project_dir)
    if branch_result.returncode != 0:
        logger.warning("Could not delete branch ade/%s: %s", task_id, branch_result.stderr.strip())


def list_worktrees(project_dir: Path) -> list[WorktreeInfo]:
    """List all git worktrees for this project."""
    result = _run_git(["worktree", "list", "--porcelain"], cwd=project_dir)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to list worktrees: {result.stderr.strip()}")

    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")

    if current:
        worktrees.append(current)

    results = []
    for wt in worktrees:
        path = Path(wt.get("path", ""))
        branch = wt.get("branch", "")
        task_id = branch[4:] if branch.startswith("ade/") else None
        results.append(WorktreeInfo(path=path, branch=branch, task_id=task_id))

    return results
