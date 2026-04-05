from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal temporary project directory."""
    return tmp_path


@pytest.fixture
def python_project(tmp_path: Path) -> Path:
    """Create a temporary Python project with pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n")
    return tmp_path


@pytest.fixture
def node_project(tmp_path: Path) -> Path:
    """Create a temporary Node.js project with package.json."""
    pkg = tmp_path / "package.json"
    pkg.write_text('{"name": "test-project", "scripts": {"test": "jest"}}\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.ts").write_text("console.log('hello');\n")
    return tmp_path


@pytest.fixture
def mixed_project(tmp_path: Path) -> Path:
    """Create a temporary multi-language project."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "mixed"\n')
    (tmp_path / "package.json").write_text('{"name": "mixed"}\n')
    (tmp_path / "src").mkdir()
    return tmp_path
