"""GitCommitTool — safe git add + commit for CrewAI agents."""

from __future__ import annotations

import subprocess
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import Field

_BLOCKED_BRANCHES = {"main", "master"}


class GitCommitTool(BaseTool):
    """Stage files and commit in the worktree, with branch restrictions."""

    name: str = "git_commit"
    description: str = (
        "Stage files and create a git commit in the project worktree. "
        "Commits to main/master are blocked. "
        "Pass space-separated file paths and a commit message."
    )
    worktree_path: Path = Field(description="Path to the git worktree")

    def _run(self, files: str, message: str) -> str:
        try:
            # Check current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                shell=False,
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            branch = branch_result.stdout.strip()
            if branch in _BLOCKED_BRANCHES:
                return f"BLOCKED: Commits to '{branch}' are not allowed. Use a feature branch."

            # git add
            file_list = files.split()
            if any(f.startswith("-") for f in file_list):
                return "BLOCKED: File arguments cannot start with '-' (flag injection)"
            add_cmd = ["git", "add", "--"] + file_list
            add_result = subprocess.run(
                add_cmd,
                shell=False,
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if add_result.returncode != 0:
                return f"ERROR (git add): {add_result.stderr.strip()}"

            # git commit
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                shell=False,
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if commit_result.returncode != 0:
                return f"ERROR (git commit): {commit_result.stderr.strip()}"

            return commit_result.stdout.strip()

        except subprocess.TimeoutExpired:
            return "ERROR: Git operation timed out"
        except Exception as e:
            return f"ERROR: {e}"
