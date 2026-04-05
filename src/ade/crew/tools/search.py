"""SearchCodeTool — grep-based code search for CrewAI agents."""

from __future__ import annotations

import subprocess
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import Field

_MAX_LINES = 50


class SearchCodeTool(BaseTool):
    """Search for patterns in the worktree using grep."""

    name: str = "search_code"
    description: str = (
        "Search for a regex pattern in the project worktree using grep. "
        "Returns matching lines with file paths and line numbers. "
        "Optionally filter by file glob (e.g. '*.py')."
    )
    worktree_path: Path = Field(description="Path to the git worktree")

    def _run(self, pattern: str, file_glob: str = "*") -> str:
        cmd = [
            "grep",
            "-rn",
            f"--include={file_glob}",
            pattern,
            str(self.worktree_path),
        ]
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

        output = result.stdout.strip()
        if not output:
            return "No matches found"

        lines = output.splitlines()
        if len(lines) > _MAX_LINES:
            truncated = lines[:_MAX_LINES]
            truncated.append(
                f"... truncated ({len(lines) - _MAX_LINES} more lines)"
            )
            return "\n".join(truncated)

        return output
