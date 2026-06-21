"""Golden-layout tests: assert the full on-disk tree produced by `ade init --agent <harness>`."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app

runner = CliRunner()


def test_gemini_layout(python_project: Path) -> None:
    result = runner.invoke(
        app, ["init", "--project-dir", str(python_project), "--agent", "gemini"]
    )
    assert result.exit_code == 0, result.output

    # Skills emitted to both Gemini skill dirs
    assert (python_project / ".gemini" / "skills" / "ade-research" / "SKILL.md").exists()
    assert (python_project / ".agents" / "skills" / "ade-research" / "SKILL.md").exists()

    # Worker subagent definition
    assert (python_project / ".gemini" / "agents" / "implementer.md").exists()

    # Hook script
    assert (python_project / ".gemini" / "hooks" / "block-mixed-commit.py").exists()

    # Hook wiring file: correct event name, correct harness flag, correct script name
    settings = python_project / ".gemini" / "settings.json"
    assert settings.exists()
    text = settings.read_text()
    assert "block-mixed-commit.py" in text
    assert "--harness gemini" in text
    assert "BeforeTool" in text

    # Memory pointer
    md = (python_project / "GEMINI.md").read_text()
    assert "<!-- ADE:START -->" in md
    assert "AGENTS.md" in md
