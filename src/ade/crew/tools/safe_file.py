"""SafeFileTool — tiered file permission enforcement for CrewAI agents."""

from __future__ import annotations

import enum
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

from crewai.tools import BaseTool
from pydantic import Field

# Patterns that are always blocked regardless of tier
_ALWAYS_BLOCKED_PATTERNS: list[str] = [
    "*.env*",
    "*credentials*",
    "*.ssh/*",
    "*secret*",
    "*.pem",
    "*.key",
]


class FilePermission(enum.Enum):
    """Result of a file permission check."""

    ALLOWED = "ALLOWED"
    LOGGED = "LOGGED"
    BLOCKED = "BLOCKED"


def _is_always_blocked(path: str) -> bool:
    """Check if a path matches any always-blocked pattern."""
    posix = PurePosixPath(path)
    # Check against full path and filename
    for pattern in _ALWAYS_BLOCKED_PATTERNS:
        if fnmatch(str(posix), pattern) or fnmatch(posix.name, pattern):
            return True
    return False


def _is_test_file(path: str) -> bool:
    """Check if a path looks like a test file."""
    posix = PurePosixPath(path)
    name = posix.name
    parts = posix.parts
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or "tests" in parts
        or "test" in parts
    )


def check_file_permission(
    path: str,
    plan_files: list[str],
    agent_role: str,
) -> FilePermission:
    """Determine the permission tier for writing to a file.

    Tier 1: Exact match in plan_files → ALLOWED
    Tier 2: __init__.py → ALLOWED; test files → ALLOWED for tester, LOGGED for others
    Tier 3: Same parent directory as a plan file → LOGGED
    Tier 4: Everything else → BLOCKED

    Always-blocked patterns (secrets, credentials) override all tiers.
    """
    # Always-blocked patterns take priority over everything
    if _is_always_blocked(path):
        return FilePermission.BLOCKED

    posix = PurePosixPath(path)

    # Tier 1: exact match in plan files
    if path in plan_files:
        return FilePermission.ALLOWED

    # Tier 2: __init__.py files are auto-allowed
    if posix.name == "__init__.py":
        return FilePermission.ALLOWED

    # Tier 2: test files
    if _is_test_file(path):
        if agent_role == "tester":
            return FilePermission.ALLOWED
        return FilePermission.LOGGED

    # Tier 3: same parent directory as any plan file
    plan_parents = {str(PurePosixPath(pf).parent) for pf in plan_files}
    if str(posix.parent) in plan_parents:
        return FilePermission.LOGGED

    # Tier 4: everything else
    return FilePermission.BLOCKED


class SafeFileTool(BaseTool):
    """Read and write files with tiered permission enforcement.

    Agents can only write to files that pass the permission check.
    Plan files are freely writable, related files are logged, and
    unrelated files are blocked. Sensitive files are always blocked.
    Any file in the worktree can be read, except always-blocked patterns.
    """

    name: str = "file_tool"
    description: str = (
        "Read or write a file in the project worktree. "
        "Use mode='read' to read a file, mode='write' (default) to write. "
        "Only files in the task plan, related __init__.py/test files, "
        "and same-directory siblings are permitted for writing. "
        "Sensitive files (.env, credentials, secrets) are always blocked."
    )
    worktree_path: Path = Field(description="Path to the git worktree")
    plan_files: list[str] = Field(description="List of files in the task plan")
    agent_role: str = Field(description="Role of the agent (coder, tester, etc.)")

    def _read_file(self, path: str) -> str:
        """Read a file from the worktree. Blocks always-blocked patterns."""
        if _is_always_blocked(path):
            return f"BLOCKED: Read of '{path}' is not permitted by file policy"

        target = self.worktree_path / path
        if not target.exists():
            return f"ERROR: File '{path}' does not exist"
        if not target.is_file():
            return f"ERROR: '{path}' is not a file"

        try:
            return target.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR: {e}"

    def _run(self, path: str, content: str = "", mode: str = "write") -> str:
        if mode == "read":
            return self._read_file(path)

        permission = check_file_permission(path, self.plan_files, self.agent_role)

        if permission == FilePermission.BLOCKED:
            return f"BLOCKED: Write to '{path}' is not permitted by file policy"

        target = self.worktree_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        if permission == FilePermission.LOGGED:
            return (
                f"OK (logged): Wrote {len(content)} chars to '{path}' "
                f"— this write was outside the task plan and has been logged"
            )

        return f"OK: Wrote {len(content)} chars to '{path}'"
