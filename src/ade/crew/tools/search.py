"""SearchCodeTool — grep-based code search for CrewAI agents."""

from __future__ import annotations

import subprocess
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import Field

_MAX_LINES = 50


class SearchCodeTool(BaseTool):
    """Search for patterns in the worktree using git grep."""

    name: str = "search_code"
    description: str = (
        "Search for a regex pattern in the project worktree using git grep. "
        "Returns matching lines with file paths and line numbers. "
        "Optionally filter by file glob (e.g. '*.py')."
    )
    worktree_path: Path = Field(description="Path to the git worktree")

    def _run(self, pattern: str, file_glob: str = "") -> str:
        cmd = [
            "git",
            "-C",
            str(self.worktree_path),
            "grep",
            "-n",
            pattern,
        ]
        if file_glob:
            cmd.extend(["--", file_glob])
        try:
            result = subprocess.run(
                cmd,
                shell=False,
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return "ERROR: Search timed out after 30s"
        except Exception as e:
            return f"ERROR: {e}"

        if result.returncode >= 2:
            return f"ERROR: {result.stderr.strip() or 'Search failed'}"

        output = result.stdout.strip()
        if not output:
            return "No matches found"

        lines = output.splitlines()
        if len(lines) > _MAX_LINES:
            truncated = lines[:_MAX_LINES]
            truncated.append(f"... truncated ({len(lines) - _MAX_LINES} more lines)")
            return "\n".join(truncated)

        return output
