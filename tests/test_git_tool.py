"""Tests for GitCommitTool."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ade.crew.tools.git import GitCommitTool


def test_commit_succeeds_on_feature_branch() -> None:
    tool = GitCommitTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        # First call: git branch --show-current -> feature branch
        # Second call: git add
        # Third call: git commit
        mock_run.side_effect = [
            MagicMock(stdout="feat/search-tool\n", stderr="", returncode=0),
            MagicMock(stdout="", stderr="", returncode=0),
            MagicMock(
                stdout="[feat/search-tool abc1234] feat: add search\n",
                stderr="",
                returncode=0,
            ),
        ]
        result = tool._run(files="src/foo.py src/bar.py", message="feat: add search")
    assert "feat: add search" in result
    assert mock_run.call_count == 3


def test_commit_blocked_on_main_branch() -> None:
    tool = GitCommitTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="main\n", stderr="", returncode=0
        )
        result = tool._run(files="src/foo.py", message="bad commit")
    assert "BLOCKED" in result
    # Only one call (branch check), no add/commit
    assert mock_run.call_count == 1


def test_commit_blocked_on_master_branch() -> None:
    tool = GitCommitTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="master\n", stderr="", returncode=0
        )
        result = tool._run(files="src/foo.py", message="bad commit")
    assert "BLOCKED" in result
    assert mock_run.call_count == 1


def test_commit_handles_git_errors() -> None:
    tool = GitCommitTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout="feat/x\n", stderr="", returncode=0),
            MagicMock(stdout="", stderr="", returncode=0),
            MagicMock(
                stdout="",
                stderr="error: nothing to commit",
                returncode=1,
            ),
        ]
        result = tool._run(files="src/foo.py", message="empty commit")
    assert "error" in result.lower()


def test_commit_blocks_flag_injection() -> None:
    tool = GitCommitTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="feat/x\n", stderr="", returncode=0
        )
        result = tool._run(files="--all", message="hack")
    assert "BLOCKED" in result


def test_commit_sets_cwd_to_worktree_path() -> None:
    wt = Path("/tmp/my-worktree")
    tool = GitCommitTool(worktree_path=wt)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout="feat/x\n", stderr="", returncode=0),
            MagicMock(stdout="", stderr="", returncode=0),
            MagicMock(stdout="committed\n", stderr="", returncode=0),
        ]
        tool._run(files="f.py", message="test")
    for call in mock_run.call_args_list:
        assert call.kwargs["cwd"] == wt
