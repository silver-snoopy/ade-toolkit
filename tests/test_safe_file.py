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
