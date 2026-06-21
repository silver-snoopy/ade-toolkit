"""Per-harness placement rules and small format deltas.

The harness layer is THIN: SKILL.md *content* is identical on every harness;
only *where* files land and a few format deltas (worker-def extension/format,
hook substrate, memory-file name) vary. Behaviour lives in the templates, not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HarnessTarget:
    name: str
    # Skills: each SKILL.md folder is copied verbatim into every dir here.
    skills_dirs: tuple[str, ...]
    # Worker subagent defs: dir, filename extension, and body format.
    workers_dir: str
    worker_ext: str
    worker_format: str  # "markdown" | "toml"
    # Deterministic hooks: where ADE's scripts land + how they are wired natively.
    hooks_dir: str
    hook_substrate: str  # "claude_settings" | "gemini_settings" | "copilot_hooks" | "codex_toml"
    # Memory file carrying the thin ADE pointer block to AGENTS.md.
    memory_file: str
    # Capabilities / deltas.
    supports_at_import: bool = False  # does memory_file honour an `@AGENTS.md` import?
    supports_subagents: bool = True  # Codex cannot autonomously dispatch (#18513)
    tier_models: dict[str, str] = field(
        default_factory=lambda: {"opus": "opus", "sonnet": "sonnet", "haiku": "haiku"}
    )
    skill_desc_budget: int = 350  # per-skill description char cap (Codex 8 KB discovery)
