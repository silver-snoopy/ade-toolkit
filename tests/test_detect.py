from pathlib import Path

from ade.detect import detect_project


def test_detect_python_project(python_project: Path) -> None:
    info = detect_project(python_project)
    assert "python" in info.languages
    assert info.project_name == "test-project"


def test_detect_node_project(node_project: Path) -> None:
    info = detect_project(node_project)
    assert "typescript" in info.languages
    assert info.project_name == "test-project"
    assert info.test_commands.get("typescript") == "jest"


def test_detect_mixed_project(mixed_project: Path) -> None:
    info = detect_project(mixed_project)
    assert "python" in info.languages
    assert "typescript" in info.languages or "javascript" in info.languages


def test_detect_empty_project(tmp_project: Path) -> None:
    info = detect_project(tmp_project)
    assert info.languages == []
    assert info.project_name == tmp_project.name


def test_detect_existing_ruff_config(python_project: Path) -> None:
    (python_project / "ruff.toml").write_text('[lint]\nselect = ["E"]\n')
    info = detect_project(python_project)
    assert "ruff.toml" in info.existing_linter_configs


def test_detect_existing_eslint_config(node_project: Path) -> None:
    (node_project / "eslint.config.js").write_text("export default [];\n")
    info = detect_project(node_project)
    assert "eslint.config.js" in info.existing_linter_configs


def test_detect_python_test_command_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "tp"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
    )
    info = detect_project(tmp_path)
    assert info.test_commands.get("python") == "pytest --tb=short -q"


def test_detect_go_project(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/foo\n\ngo 1.22\n")
    info = detect_project(tmp_path)
    assert "go" in info.languages
    assert info.test_commands.get("go") == "go test ./..."


def test_detect_existing_claude_md(python_project: Path) -> None:
    (python_project / "CLAUDE.md").write_text("# My Project\n\nExisting content.\n")
    info = detect_project(python_project)
    assert info.has_claude_md is True


def test_detect_no_claude_md(python_project: Path) -> None:
    info = detect_project(python_project)
    assert info.has_claude_md is False


def test_detect_commands_python(python_project: Path) -> None:
    info = detect_project(python_project)
    py = info.commands["python"]
    assert py["lint"] == "ruff check"
    assert py["format"] == "ruff format"
    assert py["test"] == "pytest --tb=short -q"
    # Python has no separate build step → not-applicable slot renders "none".
    assert py["build"] == "none"


def test_detect_commands_node(node_project: Path) -> None:
    info = detect_project(node_project)
    ts = info.commands["typescript"]
    assert ts["build"] == "npm run build"
    assert ts["lint"] == "npm run lint"
    # package.json scripts.test override flows through to the test slot.
    assert ts["test"] == "jest"


def test_detect_commands_unknown_language() -> None:
    from ade.detect import ProjectInfo, _detect_commands

    info = ProjectInfo(project_name="x", languages=["elixir"])
    _detect_commands(info.root, info)
    elixir = info.commands["elixir"]
    assert elixir["build"] == "# set your build command"
    assert elixir["test"] == "# set your test command"
