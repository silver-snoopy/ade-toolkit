from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ade.cli import app

runner = CliRunner()


def test_init_python_project(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert result.exit_code == 0

    # Verify v4 generated files
    assert (python_project / ".ade" / ".gitignore").exists()
    assert (python_project / ".claude" / "agents" / "backend-coder.md").exists()
    assert (python_project / ".claude" / "agents" / "code-reviewer.md").exists()
    assert (python_project / ".claude" / "agents" / "test-runner.md").exists()
    assert (python_project / ".claude" / "skills" / "ade" / "ade-full.md").exists()
    assert (python_project / ".claude" / "skills" / "ade" / "ade-plan.md").exists()
    assert (python_project / ".claude" / "commands" / "ade-full.md").exists()
    assert (python_project / ".claude" / "commands" / "ade-ship.md").exists()
    assert (python_project / "CLAUDE.md").exists()


def test_init_does_not_generate_v3_artifacts(python_project: Path) -> None:
    """v4 should NOT generate CrewAI, Ollama, or pre-commit artifacts."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    assert not (python_project / ".ade" / "config.yaml").exists()
    assert not (python_project / ".ade" / "crew").exists()
    assert not (python_project / ".ade" / "modelfiles").exists()
    assert not (python_project / ".pre-commit-config.yaml").exists()
    assert not (python_project / ".claude" / "settings.json").exists()


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
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    content = (python_project / "CLAUDE.md").read_text()
    assert content.count("## ADE") == 1


def test_init_agent_definitions_have_model(python_project: Path) -> None:
    """Agent definitions should specify a model."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    backend = (python_project / ".claude" / "agents" / "backend-coder.md").read_text()
    assert "model:" in backend
    assert "sonnet" in backend

    test_runner = (python_project / ".claude" / "agents" / "test-runner.md").read_text()
    assert "haiku" in test_runner


def test_init_skills_have_phase_content(python_project: Path) -> None:
    """Skills should contain phase instructions."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    full = (python_project / ".claude" / "skills" / "ade" / "ade-full.md").read_text()
    assert "Phase 0" in full
    assert "Phase 10" in full or "RETROSPECTIVE" in full
    assert "Circuit Breaker" in full or "circuit breaker" in full.lower()

    plan = (python_project / ".claude" / "skills" / "ade" / "ade-plan.md").read_text()
    assert "PLAN" in plan or "plan" in plan


def test_doctor_reports_missing_tools() -> None:
    with patch("ade.cli._check_command", return_value=False):
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_doctor_reports_all_ok() -> None:
    with patch("ade.cli._check_command", return_value=True):
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0


def test_status_no_tasks(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    result = runner.invoke(app, ["status", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    assert "No" in result.output


def test_status_with_tasks(python_project: Path) -> None:
    tasks_dir = python_project / ".ade" / "tasks" / "test-task"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "status.md").write_text("Phase 4/10 - Implementing\n", encoding="utf-8")

    result = runner.invoke(app, ["status", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    assert "test-task" in result.output
