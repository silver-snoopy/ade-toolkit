"""SafeShellTool — command execution with allowlist enforcement."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import Field

# Commands that agents are allowed to run (matched by first token)
_ALLOWED_PREFIXES: list[str] = [
    # Test runners
    "pytest",
    "npx jest",
    "npm test",
    "go test",
    "cargo test",
    # Linters / scanners
    "ruff",
    "eslint",
    "prettier",
    "semgrep",
    # Pre-commit
    "pre-commit",
    # Git (read + stage + commit only)
    "git add",
    "git commit",
    "git diff",
    "git status",
    "git log",
    "git show",
    # Build tools
    "npm run",
    "make",
    "cargo build",
]

# Commands that are explicitly blocked (even if they match an allowed prefix)
_BLOCKED_PATTERNS: list[str] = [
    "rm -rf",
    "rm -r",
    "curl",
    "wget",
    "ssh",
    "scp",
    "docker",
    "sudo",
    "pip install",
    "npm install",
    "git push",
    "git checkout main",
    "git checkout master",
    "git reset --hard",
    "git clean",
]


_SHELL_METACHARACTERS: list[str] = [
    "`",
    "$(",
    "|",
    ";",
    "&&",
    "||",
    ">",
    "<",
    "\n",
]


def is_command_allowed(command: str) -> bool:
    """Check if a command is allowed by the sandbox policy."""
    cmd = command.strip()

    # Block shell metacharacters as defense-in-depth against command injection
    # via shlex.split parsing and allowlist bypass
    for meta in _SHELL_METACHARACTERS:
        if meta in cmd:
            return False

    # Check blocklist first (takes priority)
    for pattern in _BLOCKED_PATTERNS:
        if cmd.startswith(pattern) or f" {pattern}" in cmd:
            return False

    # Check allowlist
    return any(cmd == prefix or cmd.startswith(prefix + " ") for prefix in _ALLOWED_PREFIXES)


class SafeShellTool(BaseTool):
    """Execute shell commands within a sandboxed worktree directory."""

    name: str = "execute_command"
    description: str = (
        "Execute a shell command in the project worktree. "
        "Only allowlisted commands (test runners, linters, git) are permitted. "
        "Network access, destructive operations, and dependency changes are blocked."
    )
    worktree_path: Path = Field(description="Path to the git worktree")
    timeout: int = Field(default=300, description="Command timeout in seconds")

    def _run(self, command: str) -> str:
        if not is_command_allowed(command):
            return f"BLOCKED: '{command}' is not in the allowed command list"

        try:
            result = subprocess.run(
                shlex.split(command),
                shell=False,
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            output = result.stdout
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]\n{result.stderr}"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return f"TIMEOUT: Command '{command}' timed out after {self.timeout}s"
        except Exception as e:
            return f"ERROR: {e}"
