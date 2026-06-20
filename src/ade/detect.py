"""Project stack auto-detection for ADE initialization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectInfo:
    """Detected project information."""

    project_name: str
    languages: list[str] = field(default_factory=list)
    test_commands: dict[str, str] = field(default_factory=dict)
    commands: dict[str, dict[str, str]] = field(default_factory=dict)
    existing_linter_configs: list[str] = field(default_factory=list)
    has_claude_md: bool = False
    root: Path = field(default_factory=lambda: Path("."))


# Marker files → language mapping
_LANGUAGE_MARKERS: dict[str, str] = {
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "package.json": "javascript",
    "go.mod": "go",
    "Cargo.toml": "rust",
}

# Aliases for language names (user input → canonical)
_LANGUAGE_ALIASES: dict[str, str] = {
    "ts": "typescript",
    "js": "javascript",
    "py": "python",
    "rs": "rust",
}

# Known linter config files to detect
_LINTER_CONFIGS: list[str] = [
    "ruff.toml",
    ".ruff.toml",
    "eslint.config.js",
    "eslint.config.mjs",
    ".eslintrc.js",
    ".eslintrc.json",
    ".eslintrc.yml",
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.yml",
    "prettier.config.js",
]

# Default test commands per language
_DEFAULT_TEST_COMMANDS: dict[str, str] = {
    "python": "pytest --tb=short -q",
    "javascript": "npx jest --ci",
    "typescript": "npx jest --ci",
    "go": "go test ./...",
    "rust": "cargo test",
}

# Default build/lint/format commands per language. Slots that do not apply to a
# language are OMITTED here (e.g. python has no separate build) — the omission is what
# drives the "none" three-state rendering in _detect_commands.
_DEFAULT_BUILD_COMMANDS: dict[str, str] = {
    "javascript": "npm run build",
    "typescript": "npm run build",
    "go": "go build ./...",
    "rust": "cargo build",
}
_DEFAULT_LINT_COMMANDS: dict[str, str] = {
    "python": "ruff check",
    "javascript": "npm run lint",
    "typescript": "npm run lint",
    "go": "go vet ./...",
    "rust": "cargo clippy",
}
_DEFAULT_FORMAT_COMMANDS: dict[str, str] = {
    "python": "ruff format",
    "javascript": "npm run format",
    "typescript": "npm run format",
    "go": "gofmt -l .",
    "rust": "cargo fmt --check",
}

# Slot name → its per-language default map. Order defines the rendered order.
_SLOT_DEFAULTS: dict[str, dict[str, str]] = {
    "build": _DEFAULT_BUILD_COMMANDS,
    "lint": _DEFAULT_LINT_COMMANDS,
    "format": _DEFAULT_FORMAT_COMMANDS,
    "test": _DEFAULT_TEST_COMMANDS,
}

# A language is "known" if ADE ships defaults for it (keyed off the test map, which
# has an entry for every supported language).
_KNOWN_LANGUAGES: frozenset[str] = frozenset(_DEFAULT_TEST_COMMANDS)


def normalize_language(lang: str) -> str:
    """Normalize a language name, resolving aliases."""
    lang = lang.strip().lower()
    return _LANGUAGE_ALIASES.get(lang, lang)


def detect_project(root: Path) -> ProjectInfo:
    """Detect project stack, languages, test commands, and existing configs."""
    info = ProjectInfo(project_name=root.name, root=root)

    _detect_languages(root, info)
    _detect_linter_configs(root, info)
    _detect_test_commands(root, info)
    _detect_commands(root, info)
    _detect_project_name(root, info)
    info.has_claude_md = (root / "CLAUDE.md").exists()

    return info


def _detect_languages(root: Path, info: ProjectInfo) -> None:
    """Detect languages from marker files."""
    for marker, language in _LANGUAGE_MARKERS.items():
        if (root / marker).exists() and language not in info.languages:
            info.languages.append(language)

    # Upgrade javascript → typescript if TS files exist or tsconfig present
    if "javascript" in info.languages:
        # Check tsconfig first (fast), then look for .ts files in src/ only
        # to avoid scanning node_modules/
        src_dir = root / "src"
        has_ts = (root / "tsconfig.json").exists() or (
            src_dir.is_dir() and any(src_dir.rglob("*.ts"))
        )
        if has_ts:
            info.languages.remove("javascript")
            if "typescript" not in info.languages:
                info.languages.append("typescript")


def _detect_linter_configs(root: Path, info: ProjectInfo) -> None:
    """Detect existing linter configuration files."""
    for config_name in _LINTER_CONFIGS:
        if (root / config_name).exists():
            info.existing_linter_configs.append(config_name)


def _detect_test_commands(root: Path, info: ProjectInfo) -> None:
    """Detect test commands from project configs or use defaults."""
    # Check package.json for test script
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            test_script = pkg.get("scripts", {}).get("test")
            if test_script:
                lang = "typescript" if "typescript" in info.languages else "javascript"
                info.test_commands[lang] = test_script
        except (json.JSONDecodeError, OSError):
            pass

    # Apply defaults for languages without explicit test commands
    for lang in info.languages:
        if lang not in info.test_commands:
            default = _DEFAULT_TEST_COMMANDS.get(lang)
            if default:
                info.test_commands[lang] = default


def _detect_commands(root: Path, info: ProjectInfo) -> None:
    """Populate info.commands with a build/lint/format/test block per language.

    Three slot states keep the rendered file honest:
    - a present per-language default → the command;
    - an omitted slot for a *known* language → the literal ``none`` (phases skip it);
    - any slot for an *unknown/undetected* language → a ``# set your <slot> command``
      placeholder for the user to fill in.
    The test slot reuses the package.json override already captured in test_commands.
    """
    for lang in info.languages:
        known = lang in _KNOWN_LANGUAGES
        slots: dict[str, str] = {}
        for slot, defaults in _SLOT_DEFAULTS.items():
            if slot == "test" and lang in info.test_commands:
                slots[slot] = info.test_commands[lang]
            elif lang in defaults:
                slots[slot] = defaults[lang]
            elif known:
                slots[slot] = "none"
            else:
                slots[slot] = f"# set your {slot} command"
        info.commands[lang] = slots


def _detect_project_name(root: Path, info: ProjectInfo) -> None:
    """Extract project name from config files if available."""
    # Try pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib

            data = tomllib.loads(pyproject.read_text())
            name = data.get("project", {}).get("name")
            if name:
                info.project_name = name
                return
        except Exception:
            pass

    # Try package.json
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            name = pkg.get("name")
            if name:
                info.project_name = name
        except (json.JSONDecodeError, OSError):
            pass
