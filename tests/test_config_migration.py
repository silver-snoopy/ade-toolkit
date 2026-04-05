from __future__ import annotations

from pathlib import Path

from ade.config import CONFIG_VERSION, AdeConfig, migrate_config


def test_migrate_same_version_noop(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config = AdeConfig(project={"name": "test", "languages": ["python"]})
    config_path.write_text(config.to_yaml(), encoding="utf-8")
    result, migrated = migrate_config(config_path)
    assert not migrated
    assert not (tmp_path / "config.yaml.bak").exists()


def test_migrate_old_version_creates_backup(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    old_yaml = "version: '1.0'\nproject:\n  name: test\n  languages: [python]\n"
    config_path.write_text(old_yaml, encoding="utf-8")
    result, migrated = migrate_config(config_path)
    assert migrated
    assert (tmp_path / "config.yaml.bak").exists()
    assert result.version == CONFIG_VERSION


def test_migrate_missing_version_field(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project:\n  name: test\n  languages: [python]\n", encoding="utf-8")
    result, migrated = migrate_config(config_path)
    assert migrated
    assert result.version == CONFIG_VERSION


def test_migrate_adds_new_fields_with_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    old_yaml = "version: '1.0'\nproject:\n  name: test\n  languages: [python]\n"
    config_path.write_text(old_yaml, encoding="utf-8")
    result, _ = migrate_config(config_path)
    assert result.logging.level == "info"  # Default applied
    assert result.orchestration.max_phase_iterations == 3  # Default applied


def test_migrate_preserves_user_values(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    old_yaml = (
        "version: '1.0'\n"
        "project:\n  name: my-app\n  languages: [python, typescript]\n"
        "models:\n  primary:\n    name: custom-model:7b\n"
    )
    config_path.write_text(old_yaml, encoding="utf-8")
    result, _ = migrate_config(config_path)
    assert result.project.name == "my-app"
    assert result.models.primary.name == "custom-model:7b"
