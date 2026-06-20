import os
import subprocess
import sys
from pathlib import Path

import pytest

from ade.cli import _get_template_env

HOOK_TEMPLATES = (
    "_hooklib.py",
    "block-mixed-commit.py",
    "check-leftover-stub.py",
    "check-escalation-paths.py",
)


def _render_hooks(dest: Path) -> None:
    """Render the hook templates into dest/.claude/hooks/."""
    env = _get_template_env()
    hooks_dir = dest / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name in HOOK_TEMPLATES:
        content = env.get_template(f"hooks/{name}.j2").render()
        (hooks_dir / name).write_text(content, encoding="utf-8")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)


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
        cwd=hook_repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
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
        cwd=hook_repo,
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2, result.stderr


def test_hooks_stdin_json_ignores_non_commit(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    raise NotImplementedError\n")
    payload = '{"tool_input": {"command": "ls -la"}}'
    hook = hook_repo / ".claude" / "hooks" / "check-leftover-stub.py"
    result = subprocess.run(
        [sys.executable, str(hook), "--stdin-json"],
        cwd=hook_repo,
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_check_leftover_stub_stdin_json_mode(hook_repo: Path) -> None:
    """check-leftover-stub reads staged files (not argv) under --stdin-json."""
    _write_stage(hook_repo, "src/feature.py", "def f():\n    raise NotImplementedError\n")
    payload = '{"tool_input": {"command": "git commit -m \\"feat: x\\""}}'
    hook = hook_repo / ".claude" / "hooks" / "check-leftover-stub.py"
    result = subprocess.run(
        [sys.executable, str(hook), "--stdin-json"],
        cwd=hook_repo,
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2, result.stderr


def test_block_mixed_commit_marker_bypass_stdin_json(hook_repo: Path) -> None:
    """The [test-refactor] bypass is reachable under the Claude substrate too."""
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    _write_stage(hook_repo, "tests/test_feature.py", "def test_f():\n    assert True\n")
    payload = '{"tool_input": {"command": "git commit -m \\"refactor: x [test-refactor]\\""}}'
    hook = hook_repo / ".claude" / "hooks" / "block-mixed-commit.py"
    result = subprocess.run(
        [sys.executable, str(hook), "--stdin-json"],
        cwd=hook_repo,
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _route(repo: Path, task_id: str, tier: str) -> None:
    """Put the repo on an ade/<task-id> branch with a routing.md recording the tier."""
    _git(repo, "checkout", "-q", "-b", f"ade/{task_id}")
    rd = repo / ".ade" / "tasks" / task_id
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "routing.md").write_text(f"Tier: {tier}\n", encoding="utf-8")


def test_escalation_hook_blocks_below_floor(hook_repo: Path) -> None:
    _route(hook_repo, "feat-x", "standard")
    _write_stage(hook_repo, "src/db/migrations/001_add.sql", "CREATE TABLE t (id int);\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "src/db/migrations/001_add.sql")
    assert result.returncode == 2, result.stderr
    assert "architecture" in result.stderr


def test_escalation_hook_allows_when_floor_met(hook_repo: Path) -> None:
    _route(hook_repo, "feat-x", "architecture")
    _write_stage(hook_repo, "src/db/migrations/001_add.sql", "CREATE TABLE t (id int);\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "src/db/migrations/001_add.sql")
    assert result.returncode == 0, result.stderr


def test_escalation_hook_noop_off_ade_branch(hook_repo: Path) -> None:
    # hook_repo is on the default branch (not ade/*); migration must NOT be blocked.
    _write_stage(hook_repo, "src/db/migrations/001_add.sql", "CREATE TABLE t (id int);\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "src/db/migrations/001_add.sql")
    assert result.returncode == 0, result.stderr


def test_escalation_hook_baseline_holds_without_config(hook_repo: Path) -> None:
    # No .claude/ade-routing.json at all; baseline must still block an auth change at trivial.
    _route(hook_repo, "feat-x", "trivial")
    _write_stage(hook_repo, "src/auth/login.py", "def login():\n    return True\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "src/auth/login.py")
    assert result.returncode == 2, result.stderr
    assert "standard" in result.stderr


def test_escalation_hook_config_extends_baseline(hook_repo: Path) -> None:
    _route(hook_repo, "feat-x", "standard")
    cfg = hook_repo / ".claude" / "ade-routing.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text('{"escalation_globs": {"architecture": ["*.weird"]}}\n', encoding="utf-8")
    _write_stage(hook_repo, "thing.weird", "x\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "thing.weird")
    assert result.returncode == 2, result.stderr


def test_escalation_hook_malformed_config_falls_back_to_baseline(hook_repo: Path) -> None:
    _route(hook_repo, "feat-x", "trivial")
    cfg = hook_repo / ".claude" / "ade-routing.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("{ not json", encoding="utf-8")
    _write_stage(hook_repo, "src/auth/login.py", "def login():\n    return True\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "src/auth/login.py")
    assert result.returncode == 2, result.stderr  # baseline still enforced


def test_escalation_hook_blocks_top_level_dir(hook_repo: Path) -> None:
    _route(hook_repo, "feat-x", "trivial")
    _write_stage(hook_repo, "auth/login.py", "def login():\n    return True\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "auth/login.py")
    assert result.returncode == 2, result.stderr
    assert "standard" in result.stderr
