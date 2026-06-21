"""Golden-layout tests: assert the full on-disk tree produced by `ade init --agent <harness>`."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app

runner = CliRunner()


def test_copilot_layout(python_project: Path) -> None:
    result = runner.invoke(
        app, ["init", "--project-dir", str(python_project), "--agent", "copilot"]
    )
    assert result.exit_code == 0, result.output

    # Skills emitted to the primary Copilot skills dir
    assert (python_project / ".github" / "skills" / "ade-research" / "SKILL.md").exists()

    # Worker subagent definition (Copilot uses .agent.md extension)
    assert (python_project / ".github" / "agents" / "implementer.agent.md").exists()

    # Hook wiring: ADE-owned ade.json
    hook_json = python_project / ".github" / "hooks" / "ade.json"
    assert hook_json.exists()
    hook_text = hook_json.read_text()
    assert "--harness copilot" in hook_text
    assert "PreToolUse" in hook_text

    # Memory pointer
    md = (python_project / ".github" / "copilot-instructions.md").read_text()
    assert "<!-- ADE:START -->" in md
    assert "AGENTS.md" in md


def test_codex_layout(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project), "--agent", "codex"])
    assert result.exit_code == 0, result.output

    # Skills emitted to .agents/skills (the only Codex skills dir — no .codex/skills)
    assert (python_project / ".agents" / "skills" / "ade-research" / "SKILL.md").exists()

    # Worker subagent definition (TOML format)
    toml_path = python_project / ".codex" / "agents" / "implementer.toml"
    assert toml_path.exists()
    toml_text = toml_path.read_text()
    assert "developer_instructions =" in toml_text
    assert "'''" in toml_text  # literal multi-line string

    # Codex reads AGENTS.md natively
    assert (python_project / "AGENTS.md").exists()

    # Degraded-tier note emitted
    assert (python_project / ".ade" / "codex-degraded.md").exists()

    # Hook wiring: .codex/hooks.json (JSON, not TOML)
    hook_json = python_project / ".codex" / "hooks.json"
    assert hook_json.exists()
    hook_text = hook_json.read_text()
    assert "--harness codex" in hook_text
    assert "PreToolUse" in hook_text

    # Codex memory IS AGENTS.md natively — no separate memory pointer file
    assert not (python_project / ".codex" / "copilot-instructions").exists()


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
