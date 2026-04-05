"""Tests for SearchCodeTool."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ade.crew.tools.search import SearchCodeTool


def test_search_finds_matching_lines() -> None:
    tool = SearchCodeTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="src/foo.py:10:def hello():\nsrc/foo.py:20:hello()\n",
            stderr="",
            returncode=0,
        )
        result = tool._run(pattern="hello")
    assert "src/foo.py:10:def hello():" in result
    assert "src/foo.py:20:hello()" in result
    # Verify git grep command structure
    cmd = mock_run.call_args[0][0]
    assert cmd[:2] == ["git", "-C"]
    assert "grep" in cmd
    assert "-n" in cmd


def test_search_returns_no_matches() -> None:
    tool = SearchCodeTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="",
            returncode=1,
        )
        result = tool._run(pattern="nonexistent_symbol_xyz")
    assert result == "No matches found"


def test_search_truncates_output_beyond_50_lines() -> None:
    tool = SearchCodeTool(worktree_path=Path("/tmp/test"))
    lines = [f"file.py:{i}:match line {i}" for i in range(80)]
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="\n".join(lines) + "\n",
            stderr="",
            returncode=0,
        )
        result = tool._run(pattern="match")
    result_lines = result.strip().splitlines()
    # 50 content lines + 1 truncation message
    assert len(result_lines) == 51
    assert "truncated" in result_lines[-1].lower()


def test_search_sets_cwd_to_worktree_path() -> None:
    wt = Path("/tmp/my-worktree")
    tool = SearchCodeTool(worktree_path=wt)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="a:1:x\n", stderr="", returncode=0)
        tool._run(pattern="x")
    assert mock_run.call_args.kwargs["cwd"] == wt


def test_search_uses_file_glob() -> None:
    tool = SearchCodeTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=1)
        tool._run(pattern="hello", file_glob="*.py")
    cmd = mock_run.call_args[0][0]
    assert "--" in cmd
    assert "*.py" in cmd


def test_search_returns_error_on_exit_code_2() -> None:
    tool = SearchCodeTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="fatal: invalid regex",
            returncode=2,
        )
        result = tool._run(pattern="[invalid")
    assert "ERROR" in result


def test_search_no_glob_omits_double_dash() -> None:
    tool = SearchCodeTool(worktree_path=Path("/tmp/test"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=1)
        tool._run(pattern="hello")
    cmd = mock_run.call_args[0][0]
    assert "--" not in cmd
