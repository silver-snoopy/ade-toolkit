import os
import subprocess
import sys
from pathlib import Path

import pytest

from ade.cli import _get_template_env

HOOK_TEMPLATES = ("_hooklib.py", "block-mixed-commit.py", "check-leftover-stub.py")


def _render_hooks(dest: Path) -> None:
    """Render the hook templates into dest/.claude/hooks/."""
    env = _get_template_env()
    hooks_dir = dest / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name in HOOK_TEMPLATES:
        content = env.get_template(f"hooks/{name}.j2").render()
        (hooks_dir / name).write_text(content, encoding="utf-8")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=False
    )


@pytest.fixture
def hook_repo(tmp_path: Path) -> Path:
    """A temp git repo with the ADE hooks rendered into .claude/hooks/."""
    _render_hooks(tmp_path)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", ".claude")
    _git(tmp_path, "commit", "-q", "-m", "chore: hooks")
    return tmp_path


def _run_hook(repo: Path, script: str, *argv: str) -> subprocess.CompletedProcess:
    """Run a hook in git/pre-commit mode (staged filenames passed as argv)."""
    return subprocess.run(
        [sys.executable, str(repo / ".claude" / "hooks" / script), *argv],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_stage(repo: Path, rel: str, content: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    _git(repo, "add", rel)


def test_block_mixed_commit_rejects_test_plus_impl(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    _write_stage(hook_repo, "tests/test_feature.py", "def test_f():\n    assert True\n")
    result = _run_hook(
        hook_repo, "block-mixed-commit.py", "src/feature.py", "tests/test_feature.py"
    )
    assert result.returncode == 2, result.stderr
    assert "mixes test and implementation" in result.stderr


def test_block_mixed_commit_allows_test_only(hook_repo: Path) -> None:
    _write_stage(hook_repo, "tests/test_feature.py", "def test_f():\n    assert True\n")
    result = _run_hook(hook_repo, "block-mixed-commit.py", "tests/test_feature.py")
    assert result.returncode == 0, result.stderr


def test_block_mixed_commit_allows_impl_only(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    result = _run_hook(hook_repo, "block-mixed-commit.py", "src/feature.py")
    assert result.returncode == 0, result.stderr


def test_block_mixed_commit_ignores_non_source(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    _write_stage(hook_repo, "README.md", "# docs\n")
    result = _run_hook(hook_repo, "block-mixed-commit.py", "src/feature.py", "README.md")
    assert result.returncode == 0, result.stderr


def test_block_mixed_commit_marker_bypass(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    _write_stage(hook_repo, "tests/test_feature.py", "def test_f():\n    assert True\n")
    msg = hook_repo / "MSG"
    msg.write_text("refactor: rename [test-refactor]\n", encoding="utf-8")
    env = dict(os.environ, PRE_COMMIT_COMMIT_MSG_FILENAME=str(msg))
    result = subprocess.run(
        [sys.executable, str(hook_repo / ".claude" / "hooks" / "block-mixed-commit.py")],
        cwd=hook_repo, capture_output=True, text=True, check=False, env=env,
    )
    assert result.returncode == 0, result.stderr


def test_check_leftover_stub_rejects_stub_in_source(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    raise NotImplementedError\n")
    result = _run_hook(hook_repo, "check-leftover-stub.py", "src/feature.py")
    assert result.returncode == 2, result.stderr
    assert "stub markers" in result.stderr


def test_check_leftover_stub_ignores_stub_in_test(hook_repo: Path) -> None:
    _write_stage(
        hook_repo, "tests/test_feature.py", "def test_f():\n    raise NotImplementedError\n"
    )
    result = _run_hook(hook_repo, "check-leftover-stub.py", "tests/test_feature.py")
    assert result.returncode == 0, result.stderr


def test_check_leftover_stub_allows_clean_impl(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 42\n")
    result = _run_hook(hook_repo, "check-leftover-stub.py", "src/feature.py")
    assert result.returncode == 0, result.stderr


def test_check_leftover_stub_rejects_js_throw(hook_repo: Path) -> None:
    _write_stage(
        hook_repo,
        "src/api.ts",
        "export function f() { throw new Error('Not implemented'); }\n",
    )
    result = _run_hook(hook_repo, "check-leftover-stub.py", "src/api.ts")
    assert result.returncode == 2, result.stderr


def test_hooks_stdin_json_mode(hook_repo: Path) -> None:
    """Claude substrate: payload on stdin, --stdin-json flag, files via git diff --cached."""
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    _write_stage(hook_repo, "tests/test_feature.py", "def test_f():\n    assert True\n")
    payload = '{"tool_input": {"command": "git commit -m \\"feat: x\\""}}'
    hook = hook_repo / ".claude" / "hooks" / "block-mixed-commit.py"
    result = subprocess.run(
        [sys.executable, str(hook), "--stdin-json"],
        cwd=hook_repo, input=payload, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2, result.stderr


def test_hooks_stdin_json_ignores_non_commit(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    raise NotImplementedError\n")
    payload = '{"tool_input": {"command": "ls -la"}}'
    hook = hook_repo / ".claude" / "hooks" / "check-leftover-stub.py"
    result = subprocess.run(
        [sys.executable, str(hook), "--stdin-json"],
        cwd=hook_repo, input=payload, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_check_leftover_stub_stdin_json_mode(hook_repo: Path) -> None:
    """check-leftover-stub reads staged files (not argv) under --stdin-json."""
    _write_stage(hook_repo, "src/feature.py", "def f():\n    raise NotImplementedError\n")
    payload = '{"tool_input": {"command": "git commit -m \\"feat: x\\""}}'
    hook = hook_repo / ".claude" / "hooks" / "check-leftover-stub.py"
    result = subprocess.run(
        [sys.executable, str(hook), "--stdin-json"],
        cwd=hook_repo, input=payload, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2, result.stderr
