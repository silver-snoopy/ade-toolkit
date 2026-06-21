"""Harness adapter registry. Add a HarnessTarget here to support a new harness."""

from __future__ import annotations

from ade.harnesses.base import HarnessTarget

CLAUDE = HarnessTarget(
    name="claude",
    skills_dirs=(".claude/skills", ".agents/skills"),
    workers_dir=".claude/agents",
    worker_ext=".md",
    worker_format="markdown",
    hooks_dir=".claude/hooks",
    hook_substrate="claude_settings",
    memory_file="CLAUDE.md",
    supports_at_import=True,
)

TARGETS: dict[str, HarnessTarget] = {"claude": CLAUDE}


def selected_targets(agent: str) -> list[HarnessTarget]:
    """Resolve the --agent value to a list of targets. 'all' = every registered target."""
    if agent == "all":
        return list(TARGETS.values())
    return [TARGETS[name.strip()] for name in agent.split(",") if name.strip()]


__all__ = ["HarnessTarget", "TARGETS", "selected_targets"]
