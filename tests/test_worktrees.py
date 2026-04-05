from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ade.worktrees import (
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
