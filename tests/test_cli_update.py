from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app
from ade.config import AdeConfig

runner = CliRunner()


def test_cli_update_no_ade_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["update", "--project-dir", str(tmp_path)])
    assert result.exit_code == 1


def test_cli_update_happy_path(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    config_path = ade_dir / "config.yaml"
    old_yaml = "version: '1.0'\nproject:\n  name: test\n  languages: [python]\n"
    config_path.write_text(old_yaml, encoding="utf-8")
    result = runner.invoke(app, ["update", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "migrated" in result.stdout.lower() or "updated" in result.stdout.lower()
