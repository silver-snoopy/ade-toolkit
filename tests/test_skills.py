# tests/test_skills.py
from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app

runner = CliRunner()

PHASE_SKILLS = [
    "ade-intent",
    "ade-research",
    "ade-plan",
    "ade-design-check",
    "ade-implement",
    "ade-quality-gate",
    "ade-review",
    "ade-docs",
    "ade-ship",
    "ade-retro",
]


def test_phase_skills_emit_as_skill_md_folders(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    for name in PHASE_SKILLS + ["ade-pipeline", "ade-pr-review", "grill-with-docs"]:
        skill = python_project / ".claude" / "skills" / name / "SKILL.md"
        assert skill.exists(), f"missing {name}/SKILL.md"
        head = skill.read_text()[:400]
        assert "name:" in head and "description:" in head


def test_skills_also_emit_to_shared_agents_dir(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert (python_project / ".agents" / "skills" / "ade-research" / "SKILL.md").exists()


def test_pipeline_driver_is_explicitly_invoked(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    head = (python_project / ".claude" / "skills" / "ade-pipeline" / "SKILL.md").read_text()[:400]
    assert "disable-model-invocation: true" in head


def test_old_phase_layout_is_gone(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert not (python_project / ".claude" / "skills" / "ade" / "phases").exists()
    assert not (python_project / ".claude" / "skills" / "ade" / "ade-full.md").exists()


def test_no_command_layer_emitted(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert not (python_project / ".claude" / "commands").exists()
