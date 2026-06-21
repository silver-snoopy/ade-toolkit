from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app

runner = CliRunner()


def test_agents_md_emitted_at_root(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agents = python_project / "AGENTS.md"
    assert agents.exists()
    assert "Phase 0" in agents.read_text()


def test_claude_md_has_pointer_block_not_full_workflow(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    md = (python_project / "CLAUDE.md").read_text()
    assert "<!-- ADE:START -->" in md and "<!-- ADE:END -->" in md
    assert "@AGENTS.md" in md  # Claude supports @import
    assert "Phase 1 — RESEARCH" not in md  # full workflow lives in AGENTS.md now


def test_pointer_block_is_idempotent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    md = (python_project / "CLAUDE.md").read_text()
    assert md.count("<!-- ADE:START -->") == 1


def test_existing_claude_md_preserved(python_project: Path) -> None:
    (python_project / "CLAUDE.md").write_text("# My Project\n\nMine.\n")
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    md = (python_project / "CLAUDE.md").read_text()
    assert md.startswith("# My Project") and "Mine." in md
    assert "<!-- ADE:START -->" in md
