"""Emit/refresh ADE's delimited pointer block in a harness memory file."""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment

from ade.harnesses.base import HarnessTarget

_START = "<!-- ADE:START -->"
_END = "<!-- ADE:END -->"
_BLOCK_RE = re.compile(re.escape(_START) + r".*?" + re.escape(_END), re.S)


def emit_memory_pointer(
    target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict
) -> None:
    """Insert or replace the ADE block in target.memory_file. No-op when it is AGENTS.md."""
    if target.memory_file == "AGENTS.md":
        return  # Codex reads the canonical file natively
    block = env.get_template("memory_pointer.md.j2").render(
        supports_at_import=target.supports_at_import, **ctx
    )
    dest = project_dir / target.memory_file
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        existing = dest.read_text(encoding="utf-8")
        if _BLOCK_RE.search(existing):
            content = _BLOCK_RE.sub(block.rstrip(), existing)
        else:
            content = existing.rstrip() + "\n\n" + block
    else:
        content = block
    dest.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
