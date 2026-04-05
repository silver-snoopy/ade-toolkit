"""Git worktree manager — create, list, remove isolated task workspaces."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WorktreeInfo:
    path: Path
    branch: str
    task_id: str | None = None


def create_worktree(project_dir: Path, task_id: str) -> WorktreeInfo:
    """Create a git worktree for a task in .ade/worktrees/<task_id>."""
    worktree_path = project_dir / ".ade" / "worktrees" / task_id
    branch = f"ade/{task_id}"

    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path), "-b", branch],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create worktree: {result.stderr.strip()}")

    return WorktreeInfo(path=worktree_path, branch=branch, task_id=task_id)


def remove_worktree(project_dir: Path, task_id: str) -> None:
    """Remove a task's worktree and optionally delete its branch."""
    worktree_path = project_dir / ".ade" / "worktrees" / task_id

    if not worktree_path.exists():
        raise FileNotFoundError(f"Worktree not found: {task_id}")

    result = subprocess.run(
        ["git", "worktree", "remove", str(worktree_path), "--force"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to remove worktree: {result.stderr.strip()}")


def list_worktrees(project_dir: Path) -> list[WorktreeInfo]:
    """List all git worktrees for this project."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    worktrees = []
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
        task_id = None
        if branch.startswith("ade/"):
            task_id = branch[4:]
        results.append(WorktreeInfo(path=path, branch=branch, task_id=task_id))

    return results
