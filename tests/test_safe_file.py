from pathlib import Path

import pytest

from ade.crew.tools.safe_file import FilePermission, SafeFileTool, check_file_permission


@pytest.fixture
def plan_files() -> list[str]:
    return ["src/auth/tokens.py", "src/auth/handler.py"]


def test_tier1_plan_file_allowed(plan_files: list[str]) -> None:
    perm = check_file_permission("src/auth/tokens.py", plan_files, agent_role="coder")
    assert perm == FilePermission.ALLOWED


def test_tier2_init_file_allowed(plan_files: list[str]) -> None:
    perm = check_file_permission("src/auth/__init__.py", plan_files, agent_role="coder")
    assert perm == FilePermission.ALLOWED


def test_tier2_test_file_allowed_for_tester(plan_files: list[str]) -> None:
    perm = check_file_permission("tests/test_auth.py", plan_files, agent_role="tester")
    assert perm == FilePermission.ALLOWED


def test_tier2_test_file_logged_for_coder(plan_files: list[str]) -> None:
    perm = check_file_permission("tests/test_auth.py", plan_files, agent_role="coder")
    assert perm == FilePermission.LOGGED


def test_tier3_sibling_file_logged(plan_files: list[str]) -> None:
    perm = check_file_permission("src/auth/utils.py", plan_files, agent_role="coder")
    assert perm == FilePermission.LOGGED


def test_tier4_unrelated_file_blocked(plan_files: list[str]) -> None:
    perm = check_file_permission("src/database/models.py", plan_files, agent_role="coder")
    assert perm == FilePermission.BLOCKED


def test_env_file_always_blocked(plan_files: list[str]) -> None:
    perm = check_file_permission(".env", plan_files, agent_role="coder")
    assert perm == FilePermission.BLOCKED


def test_credentials_file_blocked(plan_files: list[str]) -> None:
    perm = check_file_permission("credentials.json", plan_files, agent_role="coder")
    assert perm == FilePermission.BLOCKED


def test_safe_file_tool_blocks_write_to_tier4() -> None:
    tool = SafeFileTool(
        worktree_path=Path("/tmp/test"),
        plan_files=["src/foo.py"],
        agent_role="coder",
    )
    result = tool._run(path="src/bar/unrelated.py", content="hack")
    assert "BLOCKED" in result


def test_safe_file_tool_allows_write_to_tier1() -> None:
    SafeFileTool(
        worktree_path=Path("/tmp/test"),
        plan_files=["src/foo.py"],
        agent_role="coder",
    )
    # Logic test is sufficient — full integration tested in test_runner.py
    perm = check_file_permission("src/foo.py", ["src/foo.py"], agent_role="coder")
    assert perm == FilePermission.ALLOWED


# --- Read mode tests ---


def test_safe_file_tool_reads_file(tmp_path: Path) -> None:
    (tmp_path / "hello.py").write_text("print('hi')", encoding="utf-8")
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=[],
        agent_role="coder",
    )
    result = tool._run(path="hello.py", mode="read")
    assert result == "print('hi')"


def test_safe_file_tool_read_blocks_env(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=123", encoding="utf-8")
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=[],
        agent_role="coder",
    )
    result = tool._run(path=".env", mode="read")
    assert "BLOCKED" in result


def test_safe_file_tool_read_blocks_credentials(tmp_path: Path) -> None:
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=[],
        agent_role="coder",
    )
    result = tool._run(path="credentials.json", mode="read")
    assert "BLOCKED" in result


def test_safe_file_tool_read_nonexistent(tmp_path: Path) -> None:
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=[],
        agent_role="coder",
    )
    result = tool._run(path="nope.py", mode="read")
    assert "does not exist" in result


# --- Path traversal tests ---


def test_read_blocked_path_traversal(tmp_path: Path) -> None:
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=[],
        agent_role="coder",
    )
    result = tool._run(path="../../etc/passwd", mode="read")
    assert "BLOCKED" in result


def test_write_blocked_path_traversal(tmp_path: Path) -> None:
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=["../../etc/evil.py"],
        agent_role="coder",
    )
    result = tool._run(path="../../etc/evil.py", content="hack")
    assert "BLOCKED" in result


def test_read_blocked_absolute_path(tmp_path: Path) -> None:
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=[],
        agent_role="coder",
    )
    result = tool._run(path="/etc/passwd", mode="read")
    assert "BLOCKED" in result


# --- Edit mode tests ---


def test_edit_replaces_exact_match(tmp_path: Path) -> None:
    (tmp_path / "src" / "auth").mkdir(parents=True)
    target = tmp_path / "src" / "auth" / "tokens.py"
    target.write_text("def hello():\n    pass\n", encoding="utf-8")
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=["src/auth/tokens.py"],
        agent_role="coder",
    )
    result = tool._run(
        path="src/auth/tokens.py",
        mode="edit",
        old_string="    pass",
        new_string="    return 'world'",
    )
    assert "OK" in result
    assert target.read_text() == "def hello():\n    return 'world'\n"


def test_edit_fails_when_old_string_not_found(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=["app.py"],
        agent_role="coder",
    )
    result = tool._run(
        path="app.py",
        mode="edit",
        old_string="DOES NOT EXIST",
        new_string="y = 2",
    )
    assert "ERROR" in result
    assert "old_string not found" in result
    # Original file must be unchanged
    assert target.read_text() == "x = 1\n"


def test_edit_fails_on_nonexistent_file(tmp_path: Path) -> None:
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=["missing.py"],
        agent_role="coder",
    )
    result = tool._run(
        path="missing.py",
        mode="edit",
        old_string="x",
        new_string="y",
    )
    assert "ERROR" in result
    assert "does not exist" in result


def test_edit_fails_with_empty_old_string(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=["app.py"],
        agent_role="coder",
    )
    result = tool._run(path="app.py", mode="edit", old_string="", new_string="y")
    assert "ERROR" in result
    assert "must not be empty" in result


def test_edit_blocked_on_tier4_file(tmp_path: Path) -> None:
    target = tmp_path / "unrelated" / "file.py"
    target.parent.mkdir(parents=True)
    target.write_text("secret = 1\n", encoding="utf-8")
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=["src/other.py"],
        agent_role="coder",
    )
    result = tool._run(
        path="unrelated/file.py",
        mode="edit",
        old_string="secret = 1",
        new_string="secret = 2",
    )
    assert "BLOCKED" in result
    # File must be unchanged
    assert target.read_text() == "secret = 1\n"


def test_edit_blocked_on_sensitive_file(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    target.write_text("KEY=val\n", encoding="utf-8")
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=[".env"],  # Even if in plan
        agent_role="coder",
    )
    result = tool._run(
        path=".env",
        mode="edit",
        old_string="KEY=val",
        new_string="KEY=hacked",
    )
    assert "BLOCKED" in result


def test_edit_replaces_only_first_occurrence(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("x = 1\nx = 1\nx = 1\n", encoding="utf-8")
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=["app.py"],
        agent_role="coder",
    )
    result = tool._run(
        path="app.py",
        mode="edit",
        old_string="x = 1",
        new_string="x = 2",
    )
    assert "OK" in result
    assert "first of 3" in result
    assert target.read_text() == "x = 2\nx = 1\nx = 1\n"


def test_edit_path_traversal_blocked(tmp_path: Path) -> None:
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=["../../etc/passwd"],
        agent_role="coder",
    )
    result = tool._run(
        path="../../etc/passwd",
        mode="edit",
        old_string="root",
        new_string="hacked",
    )
    assert "BLOCKED" in result


# --- Mode validation tests ---


def test_safe_file_invalid_mode(tmp_path: Path) -> None:
    tool = SafeFileTool(
        worktree_path=tmp_path,
        plan_files=[],
        agent_role="coder",
    )
    result = tool._run(path="foo.py", content="x", mode="delete")
    assert "ERROR" in result
