from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ade.cli import app

runner = CliRunner()


def test_init_python_project(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert result.exit_code == 0

    # Verify generated files
    assert (python_project / ".ade" / "config.yaml").exists()
    assert (python_project / ".ade" / ".gitignore").exists()
    assert (python_project / ".ade" / "crew" / "coder.yaml").exists()
    assert (python_project / ".pre-commit-config.yaml").exists()
    assert (python_project / ".claude" / "commands" / "ade-full.md").exists()
    assert (python_project / "CLAUDE.md").exists()


def test_init_creates_claude_md_with_ade_section(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert result.exit_code == 0

    content = (python_project / "CLAUDE.md").read_text()
    assert "ADE" in content
    assert "Agentic Development Environment" in content


def test_init_appends_to_existing_claude_md(python_project: Path) -> None:
    existing = "# My Project\n\nExisting content.\n"
    (python_project / "CLAUDE.md").write_text(existing)

    result = runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert result.exit_code == 0

    content = (python_project / "CLAUDE.md").read_text()
    assert content.startswith("# My Project")
    assert "Existing content." in content
    assert "ADE" in content


def test_init_does_not_duplicate_ade_section(python_project: Path) -> None:
    # Run init twice
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    content = (python_project / "CLAUDE.md").read_text()
    # ADE section marker should appear only once
    assert content.count("## ADE") == 1


def test_init_with_language_override(python_project: Path) -> None:
    result = runner.invoke(
        app, ["init", "--project-dir", str(python_project), "--language", "python,typescript"]
    )
    assert result.exit_code == 0

    config_content = (python_project / ".ade" / "config.yaml").read_text()
    assert "python" in config_content
    assert "typescript" in config_content


def test_init_node_project_includes_eslint(node_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(node_project)])
    assert result.exit_code == 0

    precommit = (node_project / ".pre-commit-config.yaml").read_text()
    assert "eslint" in precommit
    assert "prettier" in precommit


def test_init_python_project_excludes_eslint(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert result.exit_code == 0

    precommit = (python_project / ".pre-commit-config.yaml").read_text()
    assert "ruff" in precommit
    assert "eslint" not in precommit


def test_doctor_reports_missing_tools() -> None:
    """Doctor should report when tools are not found."""
    with patch("ade.cli._check_command", return_value=False):
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "FAIL" in result.output or "not found" in result.output.lower()


def test_doctor_reports_all_ok() -> None:
    """Doctor should report success when all tools are present."""
    with (
        patch("ade.cli._check_command", return_value=True),
        patch("ade.cli._check_ollama_models", return_value=[]),
    ):
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "ok" in result.output.lower() or "pass" in result.output.lower()


def test_doctor_warns_missing_models() -> None:
    """Doctor should warn (not fail) when Ollama models are missing."""
    with (
        patch("ade.cli._check_command", return_value=True),
        patch("ade.cli._check_ollama_models", return_value=["gemma4:31b"]),
    ):
        result = runner.invoke(app, ["doctor"])
    # Missing models are warnings, not failures — exit code 0
    assert result.exit_code == 0
    assert "gemma4:31b" in result.output
