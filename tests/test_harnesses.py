import pytest
from jinja2 import Environment, PackageLoader

from ade.harnesses import TARGETS, HarnessTarget, selected_targets
from ade.harnesses.workers import render_worker


def _env() -> Environment:
    return Environment(loader=PackageLoader("ade", "templates"), keep_trailing_newline=True)


def test_claude_target_shape() -> None:
    claude = TARGETS["claude"]
    assert isinstance(claude, HarnessTarget)
    assert claude.name == "claude"
    assert ".claude/skills" in claude.skills_dirs
    assert claude.workers_dir == ".claude/agents"
    assert claude.worker_ext == ".md"
    assert claude.worker_format == "markdown"
    assert claude.hooks_dir == ".claude/hooks"
    assert claude.hook_substrate == "claude_settings"
    assert claude.memory_file == "CLAUDE.md"


def test_selected_targets_default_is_claude() -> None:
    assert [t.name for t in selected_targets("claude")] == ["claude"]


def test_selected_targets_rejects_unknown() -> None:
    with pytest.raises(KeyError):
        selected_targets("cursor")


def test_selected_targets_rejects_empty() -> None:
    with pytest.raises(KeyError):
        selected_targets("")
    with pytest.raises(KeyError):
        selected_targets("  ")


def test_render_worker_markdown_for_claude() -> None:
    rel, content = render_worker(TARGETS["claude"], _env(), "implementer", {"info": None})
    assert rel == ".claude/agents/implementer.md"
    assert "model: sonnet" in content
    assert "implementer" in content.lower()
