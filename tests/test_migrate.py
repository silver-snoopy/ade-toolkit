"""Tests for `ade migrate` (v2 → v3) command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app

runner = CliRunner()


def _make_v2_tree(p: Path) -> None:
    (p / ".claude" / "skills" / "ade" / "phases").mkdir(parents=True)
    (p / ".claude" / "skills" / "ade" / "ade-full.md").write_text("old\n")
    (p / ".claude" / "commands").mkdir(parents=True)
    (p / ".claude" / "commands" / "ade-full.md").write_text("old\n")
    (p / ".claude" / "ade-routing.json").write_text('{"escalation_globs": {"x": ["*.k"]}}\n')
    (p / ".claude" / "ade-stack.md").write_text("# user edited stack\n")
    (p / "CLAUDE.md").write_text(
        "# Mine\n\n## ADE — Agentic Development Environment (v4)\n\nold workflow\n"
    )


def test_migrate_moves_config_and_regenerates(python_project: Path) -> None:
    _make_v2_tree(python_project)
    result = runner.invoke(app, ["migrate", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    # user-owned config moved, edits preserved
    routing = python_project / ".ade" / "ade-routing.json"
    assert routing.exists() and "*.k" in routing.read_text()
    assert "user edited stack" in (python_project / ".ade" / "ade-stack.md").read_text()
    # stale generated trees gone
    assert not (python_project / ".claude" / "skills" / "ade").exists()
    assert not (python_project / ".claude" / "commands").exists()
    # v3 layout present
    assert (python_project / ".claude" / "skills" / "ade-pipeline" / "SKILL.md").exists()
    assert (python_project / "AGENTS.md").exists()
    # CLAUDE.md rewritten to a pointer, user content kept
    md = (python_project / "CLAUDE.md").read_text()
    assert md.startswith("# Mine") and "<!-- ADE:START -->" in md
    assert "(v4)" not in md


def test_migrate_is_idempotent(python_project: Path) -> None:
    _make_v2_tree(python_project)
    runner.invoke(app, ["migrate", "--project-dir", str(python_project)])
    runner.invoke(app, ["migrate", "--project-dir", str(python_project)])
    md = (python_project / "CLAUDE.md").read_text()
    assert md.count("<!-- ADE:START -->") == 1
