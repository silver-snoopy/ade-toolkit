"""Static skill-quality checks (offline, deterministic). Shipped as `ade eval`."""

from __future__ import annotations

import re
from collections import namedtuple
from pathlib import Path

Finding = namedtuple("Finding", "skill level message")

_DESC_BUDGET = 350
_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def _parse_frontmatter(text: str) -> dict[str, str] | None:
    m = _FM_RE.match(text)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def run_eval(skills_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        folder = skill_md.parent.name
        text = skill_md.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        if fm is None:
            findings.append(Finding(folder, "error", "missing or malformed YAML frontmatter"))
            continue
        name = fm.get("name", "")
        desc = fm.get("description", "")
        if not name:
            findings.append(Finding(folder, "error", "frontmatter missing 'name'"))
        elif name != folder:
            findings.append(Finding(folder, "error", f"name '{name}' != folder '{folder}'"))
        if not desc:
            findings.append(Finding(folder, "error", "frontmatter missing 'description'"))
        elif len(desc) > _DESC_BUDGET:
            findings.append(
                Finding(folder, "error", f"description {len(desc)} chars > {_DESC_BUDGET} budget")
            )
        elif desc.lower().startswith("this skill"):
            findings.append(
                Finding(folder, "warn", "description starts with 'This skill' (filler)")
            )
    return findings
