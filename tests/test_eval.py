from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app
from ade.eval import run_eval

runner = CliRunner()


def test_eval_passes_on_generated_skills(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    result = runner.invoke(app, ["eval", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    assert "PASS" in result.output or "0 error" in result.output


def test_eval_flags_overlong_description(tmp_path: Path) -> None:
    skill = tmp_path / "ade-bad" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    long_desc = "x" * 400
    skill.write_text(f"---\nname: ade-bad\ndescription: {long_desc}\n---\nbody\n")
    findings = run_eval(tmp_path)
    assert any(f.level == "error" and "description" in f.message for f in findings)


def test_eval_flags_missing_frontmatter(tmp_path: Path) -> None:
    skill = tmp_path / "ade-x" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("no frontmatter here\n")
    findings = run_eval(tmp_path)
    assert any(f.level == "error" for f in findings)


def test_eval_flags_name_folder_mismatch(tmp_path: Path) -> None:
    skill = tmp_path / "ade-x" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: ade-y\ndescription: ok short desc\n---\nbody\n")
    findings = run_eval(tmp_path)
    assert any("name" in f.message for f in findings)
