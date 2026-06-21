"""Render a canonical worker-subagent definition for a specific harness."""

from __future__ import annotations

import re

from jinja2 import Environment

from ade.harnesses.base import HarnessTarget

_MODEL_RE = re.compile(r"(?m)^model:\s*(\w+)\s*$")


def _remap_model(content: str, tier_models: dict[str, str]) -> str:
    def sub(m: re.Match[str]) -> str:
        tier = m.group(1)
        return f"model: {tier_models.get(tier, tier)}"

    return _MODEL_RE.sub(sub, content)


def render_worker(
    target: HarnessTarget, env: Environment, name: str, ctx: dict
) -> tuple[str, str]:
    """Return (relative_dest_path, content) for worker `name` on `target`."""
    content = env.get_template(f"agents/{name}.md.j2").render(**ctx)
    content = _remap_model(content, target.tier_models)
    if target.worker_format == "toml":
        content = _to_toml(content)
    rel = f"{target.workers_dir}/{name}{target.worker_ext}"
    return rel, content


def _to_toml(markdown: str) -> str:
    """Convert a `--- frontmatter --- body` worker def to Codex TOML.

    Frontmatter keys (model, tools) become top-level TOML; the body becomes
    `instructions = '''...'''`. Implemented for real in Task C3; markdown harnesses
    never call this path.
    """
    raise NotImplementedError("TOML worker format is wired in Task C3 (Codex adapter)")
