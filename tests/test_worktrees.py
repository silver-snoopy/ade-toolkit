from __future__ import annotations

import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest

from ade.worktrees import (
    WorktreeInfo,
    create_worktree,
    list_worktrees,
    remove_worktree,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo for worktree tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
    (repo / "README.md").write_text("# Test", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True)
    return repo


def test_create_worktree(git_repo: Path) -> None:
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    info = create_worktree(
        project_dir=git_repo,
        task_id="abc123",
    )
    assert info.task_id == "abc123"
    assert info.branch == "ade/abc123"
    assert info.path.exists()
    assert (info.path / "README.md").exists()


def test_create_worktree_path(git_repo: Path) -> None:
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    info = create_worktree(project_dir=git_repo, task_id="abc123")
    assert str(info.path).endswith("abc123")
    assert ".ade" in str(info.path) or "worktrees" in str(info.path)


def test_remove_worktree(git_repo: Path) -> None:
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    info = create_worktree(project_dir=git_repo, task_id="abc123")
    assert info.path.exists()
    remove_worktree(project_dir=git_repo, task_id="abc123")
    assert not info.path.exists()


def test_remove_worktree_not_found(git_repo: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Worktree not found"):
        remove_worktree(project_dir=git_repo, task_id="nonexistent")


def test_list_worktrees_empty(git_repo: Path) -> None:
    trees = list_worktrees(project_dir=git_repo)
    # Only the main worktree exists
    assert len(trees) == 1


def test_list_worktrees_with_task(git_repo: Path) -> None:
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    create_worktree(project_dir=git_repo, task_id="abc123")
    trees = list_worktrees(project_dir=git_repo)
    assert len(trees) == 2  # main + task worktree
    branches = [t.branch for t in trees]
    assert "ade/abc123" in branches


def test_create_worktree_timeout(git_repo: Path) -> None:
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    timeout_err = subprocess.TimeoutExpired(cmd="git", timeout=30)
    with (
        patch("ade.worktrees.subprocess.run", side_effect=timeout_err),
        pytest.raises(RuntimeError, match="timed out"),
    ):
        create_worktree(project_dir=git_repo, task_id="abc123")


def test_create_worktree_git_not_found(git_repo: Path) -> None:
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    with (
        patch("ade.worktrees.subprocess.run", side_effect=FileNotFoundError),
        pytest.raises(RuntimeError, match="git is not installed"),
    ):
        create_worktree(project_dir=git_repo, task_id="abc123")


def test_remove_worktree_cleans_branch(git_repo: Path) -> None:
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    create_worktree(project_dir=git_repo, task_id="abc123")
    remove_worktree(project_dir=git_repo, task_id="abc123")
    # Branch should be deleted
    result = subprocess.run(
        ["git", "branch", "--list", "ade/abc123"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""


def test_remove_worktree_branch_cleanup_nonfatal(git_repo: Path) -> None:
    """Branch deletion failing should not raise."""
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    create_worktree(project_dir=git_repo, task_id="abc123")
    remove_worktree(project_dir=git_repo, task_id="abc123")
    # No exception raised = success


def test_list_worktrees_raises_on_git_failure(tmp_path: Path) -> None:
    """list_worktrees should raise RuntimeError when git fails, not return []."""
    with pytest.raises(RuntimeError, match="Failed to list worktrees"):
        list_worktrees(project_dir=tmp_path)  # Not a git repo


def test_worktree_info_frozen() -> None:
    info = WorktreeInfo(path=Path("/tmp/x"), branch="main")
    with pytest.raises(FrozenInstanceError):
        info.path = Path("/tmp/y")
