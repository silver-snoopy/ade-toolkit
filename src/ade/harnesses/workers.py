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
        content = _to_toml(content, name)
    rel = f"{target.workers_dir}/{name}{target.worker_ext}"
    return rel, content


def _to_toml(markdown: str, name: str) -> str:
    """Convert a ``--- frontmatter --- body`` worker def to Codex TOML.

    Synthesises required Codex keys from the markdown template:
    - ``name`` = stem passed in (e.g. ``"implementer"``)
    - ``description`` = first non-empty body line (the role sentence)
    - ``model`` = frontmatter ``model:`` value, if present (optional in Codex)
    - ``developer_instructions`` = full body as a TOML literal string (``'''...''``)
    The ``tools`` frontmatter key is dropped — Codex TOML uses ``sandbox_mode`` /
    ``mcp_servers`` instead; omitted here for V1.
    """
    fm: dict[str, str] = {}
    body = markdown
    if markdown.startswith("---"):
        _, raw_fm, body = markdown.split("---", 2)
        for line in raw_fm.strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()

    body_stripped = body.strip()
    # description = first non-empty line of the body
    description = next((ln.strip() for ln in body_stripped.splitlines() if ln.strip()), "")
    # Escape any literal ''' in the body so it doesn't break the TOML literal string
    developer_instructions = body_stripped.replace("'''", "''")

    lines: list[str] = [
        f'name = "{name}"',
        f'description = "{description}"',
    ]
    if "model" in fm:
        lines.append(f'model = "{fm["model"]}"')
    lines.append(f"developer_instructions = '''\n{developer_instructions}\n'''\n")
    return "\n".join(lines) + "\n"
