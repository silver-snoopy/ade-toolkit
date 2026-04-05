from ade.config import build_config
from ade.detect import ProjectInfo


def test_build_config_python_project() -> None:
    info = ProjectInfo(
        project_name="my-app",
        languages=["python"],
        test_commands={"python": "pytest --tb=short -q"},
    )
    config = build_config(info)
    assert config.project.name == "my-app"
    assert config.project.languages == ["python"]
    assert config.scanning.ruff.enabled is True
    assert config.scanning.eslint.enabled is False


def test_build_config_typescript_project() -> None:
    info = ProjectInfo(
        project_name="web-app",
        languages=["typescript"],
        test_commands={"typescript": "jest"},
    )
    config = build_config(info)
    assert config.scanning.eslint.enabled is True
    assert config.scanning.prettier.enabled is True
    assert config.scanning.ruff.enabled is False


def test_build_config_mixed_project() -> None:
    info = ProjectInfo(
        project_name="mixed",
        languages=["python", "typescript"],
        test_commands={"python": "pytest --tb=short -q", "typescript": "jest"},
    )
    config = build_config(info)
    assert config.scanning.ruff.enabled is True
    assert config.scanning.eslint.enabled is True


def test_config_to_yaml() -> None:
    info = ProjectInfo(project_name="test", languages=["python"])
    config = build_config(info)
    yaml_str = config.to_yaml()
    assert "version:" in yaml_str
    assert "test" in yaml_str
    assert "python" in yaml_str


def test_config_defaults() -> None:
    info = ProjectInfo(project_name="proj", languages=[])
    config = build_config(info)
    assert config.version == "2.0"
    assert config.models.primary.name == "gemma4:31b"
    assert config.models.mode == "hot-swap"
    assert config.orchestration.max_phase_iterations == 3
    assert config.worktree.branch_prefix == "ade/"
