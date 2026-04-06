"""SafeFileTool — tiered file permission enforcement for CrewAI agents."""

from __future__ import annotations

import enum
import logging
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

from crewai.tools import BaseTool
from pydantic import Field

logger = logging.getLogger("ade.tools.file")

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
    """Read, write, and edit files with tiered permission enforcement.

    Agents can only write/edit files that pass the permission check.
    Plan files are freely writable, related files are logged, and
    unrelated files are blocked. Sensitive files are always blocked.
    Any file in the worktree can be read, except always-blocked patterns.

    Modes:
    - read: Read file contents
    - write: Create or overwrite a file (use for NEW files only)
    - edit: Search-and-replace in an existing file (use for MODIFYING files)
    """

    name: str = "file_tool"
    description: str = (
        "Read, write, or edit a file in the project worktree. "
        "Modes: mode='read' to read, mode='write' to create NEW files, "
        "mode='edit' to modify EXISTING files (requires old_string and new_string). "
        "For edit mode: old_string is the exact text to find, new_string is the replacement. "
        "Only files in the task plan and related directories are permitted for writing/editing. "
        "Sensitive files (.env, credentials, secrets) are always blocked."
    )
    worktree_path: Path = Field(description="Path to the git worktree")
    plan_files: list[str] = Field(description="List of files in the task plan")
    agent_role: str = Field(description="Role of the agent (coder, tester, etc.)")

    def _read_file(self, path: str) -> str:
        """Read a file from the worktree. Blocks always-blocked patterns."""
        if _is_always_blocked(path):
            return f"BLOCKED: Read of '{path}' is not permitted by file policy"

        target = (self.worktree_path / path).resolve()
        if not target.is_relative_to(self.worktree_path.resolve()):
            return f"BLOCKED: '{path}' escapes the worktree boundary"

        if not target.exists():
            return f"ERROR: File '{path}' does not exist"
        if not target.is_file():
            return f"ERROR: '{path}' is not a file"

        try:
            return target.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR: {e}"

    def _edit_file(self, path: str, old_string: str, new_string: str) -> str:
        """Replace exact text in an existing file. Safe: no match = no change."""
        permission = check_file_permission(path, self.plan_files, self.agent_role)

        if permission == FilePermission.BLOCKED:
            logger.warning(
                "file_tool edit BLOCKED path=%s agent=%s",
                path,
                self.agent_role,
            )
            return f"BLOCKED: Edit of '{path}' is not permitted by file policy"

        target = (self.worktree_path / path).resolve()
        if not target.is_relative_to(self.worktree_path.resolve()):
            logger.warning("file_tool edit BLOCKED path=%s reason=path_traversal", path)
            return f"BLOCKED: '{path}' escapes the worktree boundary"

        if not target.exists():
            return f"ERROR: File '{path}' does not exist. Use mode='write' to create new files."

        if not old_string:
            return "ERROR: old_string must not be empty for edit mode"

        try:
            original = target.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR: Could not read '{path}': {e}"

        if old_string not in original:
            # Help the agent understand what went wrong
            return (
                f"ERROR: old_string not found in '{path}'. "
                f"The file has {len(original)} chars and {original.count(chr(10))+1} lines. "
                f"Use mode='read' to see the current content, then retry with the exact text."
            )

        count = original.count(old_string)
        updated = original.replace(old_string, new_string, 1)

        try:
            target.write_text(updated, encoding="utf-8")
        except OSError as e:
            logger.error("file_tool edit ERROR path=%s error=%s", path, e)
            return f"ERROR: {e}"

        logger.info(
            "file_tool edit %s path=%s old_chars=%d new_chars=%d occurrences=%d",
            permission.value,
            path,
            len(old_string),
            len(new_string),
            count,
        )

        result = f"OK: Replaced {len(old_string)} chars with {len(new_string)} chars in '{path}'"
        if count > 1:
            result += f" (replaced first of {count} occurrences)"
        if permission == FilePermission.LOGGED:
            result += " — this edit was outside the task plan and has been logged"
        return result

    def _run(
        self,
        path: str,
        content: str = "",
        mode: str = "write",
        old_string: str = "",
        new_string: str = "",
    ) -> str:
        if mode not in ("read", "write", "edit"):
            return f"ERROR: Invalid mode '{mode}'. Use 'read', 'write', or 'edit'."

        if mode == "read":
            result = self._read_file(path)
            logger.info(
                "file_tool read path=%s result=%s",
                path,
                result[:60] if len(result) > 60 else result,
            )
            return result

        if mode == "edit":
            return self._edit_file(path, old_string, new_string)

        # mode == "write"
        permission = check_file_permission(path, self.plan_files, self.agent_role)

        if permission == FilePermission.BLOCKED:
            logger.warning(
                "file_tool write BLOCKED path=%s agent=%s plan_files=%s",
                path,
                self.agent_role,
                self.plan_files[:5],
            )
            return f"BLOCKED: Write to '{path}' is not permitted by file policy"

        target = (self.worktree_path / path).resolve()
        if not target.is_relative_to(self.worktree_path.resolve()):
            logger.warning("file_tool write BLOCKED path=%s reason=path_traversal", path)
            return f"BLOCKED: '{path}' escapes the worktree boundary"

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as e:
            logger.error("file_tool write ERROR path=%s error=%s", path, e)
            return f"ERROR: {e}"

        logger.info("file_tool write %s path=%s chars=%d", permission.value, path, len(content))

        if permission == FilePermission.LOGGED:
            return (
                f"OK (logged): Wrote {len(content)} chars to '{path}' "
                f"— this write was outside the task plan and has been logged"
            )

        return f"OK: Wrote {len(content)} chars to '{path}'"
