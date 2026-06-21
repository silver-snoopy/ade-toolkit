"""Render ADE's deterministic hook scripts into a harness tree and wire them natively."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from jinja2 import Environment

from ade.harnesses.base import HarnessTarget

_HOOK_SCRIPTS = (
    "_hooklib.py",
    "block-mixed-commit.py",
    "check-leftover-stub.py",
    "check-escalation-paths.py",
)


def _render_scripts(env: Environment, hooks_dir: Path, ctx: dict) -> None:
    for name in _HOOK_SCRIPTS:
        content = env.get_template(f"hooks/{name}.j2").render(**ctx)
        dest = hooks_dir / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


def render_hook_scripts(
    target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict
) -> None:
    """Render hook scripts into target's hooks_dir (public helper for the legacy_copilot path)."""
    _render_scripts(env, project_dir / target.hooks_dir, ctx)


def emit_hooks(target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict) -> str:
    """Render the hook scripts into target.hooks_dir and wire them. Returns an action word."""
    render_hook_scripts(target, env, project_dir, ctx)
    if target.hook_substrate == "claude_settings":
        return _wire_claude(target, env, project_dir, ctx)
    if target.hook_substrate == "gemini_settings":
        return _wire_gemini(target, env, project_dir, ctx)  # Task C1
    if target.hook_substrate == "copilot_hooks":
        return _wire_copilot(target, env, project_dir, ctx)  # Task C2
    if target.hook_substrate == "codex_toml":
        return _wire_codex(target, env, project_dir, ctx)  # Task C3
    raise ValueError(f"unknown hook substrate: {target.hook_substrate}")


def _merge_hooks(current: dict, ade: dict) -> dict:
    """Idempotently merge ADE PreToolUse hook commands into an existing settings dict."""
    merged = copy.deepcopy(current)
    hooks = merged.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        merged["hooks"] = hooks
    for event, blocks in ade.get("hooks", {}).items():
        existing = hooks.setdefault(event, [])
        for ade_block in blocks:
            tgt = next((b for b in existing if b.get("matcher") == ade_block.get("matcher")), None)
            if tgt is None:
                existing.append(ade_block)
                continue
            tgt_hooks = tgt.setdefault("hooks", [])
            seen = {h.get("command") for h in tgt_hooks}
            for hook in ade_block.get("hooks", []):
                if hook.get("command") not in seen:
                    tgt_hooks.append(hook)
    return merged


def _wire_claude(target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict) -> str:
    dest = project_dir / ".claude" / "settings.json"
    ade = json.loads(env.get_template("claude_settings.json.j2").render(**ctx))
    if dest.exists():
        try:
            current = json.loads(dest.read_text(encoding="utf-8"))
            if not isinstance(current, dict):
                current = {}
        except json.JSONDecodeError:
            current = {}
        merged = _merge_hooks(current, ade)
        action = "Merged hooks into"
    else:
        merged = ade
        action = "Created"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return action


def _wire_gemini(target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict) -> str:
    raise NotImplementedError("wired in Task C1/C2/C3")


def _wire_copilot(target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict) -> str:
    raise NotImplementedError("wired in Task C1/C2/C3")


def _wire_codex(target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict) -> str:
    raise NotImplementedError("wired in Task C1/C2/C3")
