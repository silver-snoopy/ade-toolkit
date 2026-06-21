# Platform-Agnostic ADE (v3.0.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ADE first-class on Claude Code, Gemini CLI, GitHub Copilot, and Codex CLI by authoring the pipeline as portable Agent Skills (SKILL.md) that dispatch thin per-harness worker subagents, enforced by native PreToolUse hooks on all four harnesses.

**Architecture:** A thin `src/ade/harnesses/` adapter layer holds per-harness *placement* (which dirs) and *small deltas* (worker-def extension/format, hook substrate, memory-file name). The behavior lives in harness-neutral templates: one SKILL.md per SDLC phase, a user-invoked `ade-pipeline` driver, ~12 worker subagent defs, three deterministic hook scripts + `_hooklib`, and a canonical root `AGENTS.md`. `ade init --agent <targets>` emits the right layout per selected harness; `ade migrate` upgrades v2 trees; `ade eval` statically gates skill quality.

**Tech Stack:** Python 3.11+, Typer (CLI), Jinja2 (`PackageLoader("ade", "templates")`), Rich (output), pytest + `typer.testing.CliRunner` (tests), ruff (lint/format). No runtime agent framework — ADE only scaffolds files; Claude Code / the other harnesses are the runtime.

## Global Constraints

Every task's requirements implicitly include this section. Values copied verbatim from `docs/superpowers/specs/2026-06-21-platform-agnostic-ade-design.md`, ADR-0003, and `CLAUDE.md`.

- **Python:** 3.11+. Type hints on all public functions. `from __future__ import annotations` at top of every module (matches existing files).
- **Lint/format:** ruff, line-length **99**. Run `ruff check src/ tests/` and `ruff format src/ tests/` before every commit.
- **Tests:** pytest; tests in `tests/` mirror `src/`. Use the existing `python_project` / `node_project` / `mixed_project` fixtures from `tests/conftest.py`. Run `pytest` (all) or `pytest tests/test_x.py::test_y -v` (single).
- **Commits:** Conventional Commits. Every commit message ends with the trailer:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- **Version:** this is **v3.0.0** (breaking layout change). Do not bump partway; the version bump lands in Phase E.
- **`--agent` contract:** accepts a comma-separated list (`claude,gemini,codex,copilot`) or the literal `all`; **defaults to `claude`**. Unknown names exit non-zero.
- **Layout split rule (invariant across the whole plan):**
  - **Durable project knowledge** → `docs/` (specs, ADRs, `docs/learnings/`, `docs/review-calibration.md`). Versioned, harness-neutral. Never per-harness.
  - **ADE config (user-owned) + ephemeral state** → `.ade/` (single copy): `.ade/ade-routing.json`, `.ade/ade-stack.md`, `.ade/tasks/`, `.ade/worktrees/`. Only `.ade/tasks/` and `.ade/worktrees/` are gitignored.
  - **Generated artifacts** → per-harness dirs (skills, worker defs, hooks).
- **Ownership rule:** ADE-generated files (skills, worker defs, hook scripts, `AGENTS.md`, the ADE block in each memory file) are **always safe to overwrite** — regenerated on every `init`. User-owned files (`.ade/ade-routing.json`, `.ade/ade-stack.md`, `CONTEXT.md`, `docs/adr/*`, `docs/specs/*`, bootstrap READMEs) are **seed-if-missing, never overwritten** — use `_render_and_write_if_missing`.
- **SKILL.md frontmatter:** every skill folder is `<skill-name>/SKILL.md` with YAML frontmatter carrying at least `name` and `description`. Descriptions must be **lean** (Codex loads only an 8 KB discovery list of descriptions; `ade eval` flags overruns — per-skill description cap **≤ 350 characters**).
- **No personas:** worker defs and skills stay function-named/capability-organized. The blind `spec-verifier` stays unlabeled — never add "you are a senior X" framing.
- **Codex is a degraded tier:** orchestration (autonomous subagent dispatch) is user-gated upstream (`openai/codex#18513`). Codex still gets skills + TOML worker defs + native hooks + `AGENTS.md`; author-separation/blind-verification degrade to in-context conventions there, but the **native PreToolUse hooks still enforce G1/G2/G4**.

---

## File Structure

New and changed files across the whole plan. Paths under `src/ade/templates/` are Jinja2 sources (`.j2`); paths without are Python modules / repo docs.

**New Python modules**
- `src/ade/harnesses/__init__.py` — `TARGETS` registry + `selected_targets()`; re-exports `HarnessTarget`.
- `src/ade/harnesses/base.py` — `HarnessTarget` frozen dataclass (placement + deltas, pure data).
- `src/ade/harnesses/workers.py` — `render_worker(target, env, name, ctx) -> (relpath, content)`; markdown + TOML formatters.
- `src/ade/harnesses/hooks.py` — `emit_hooks(target, env, project_dir, ctx) -> str`; per-substrate wiring (claude_settings / gemini_settings / copilot_hooks / codex_toml).
- `src/ade/harnesses/memory.py` — `emit_memory_pointer(target, project_dir)`; thin delimited ADE block importing `AGENTS.md`.
- `src/ade/eval.py` — static skill-quality checks (`run_eval(skills_root) -> list[Finding]`).

**Changed Python modules**
- `src/ade/cli.py` — `init` re-routed through the adapter layer; `--agent` list/all; new `migrate` and `eval` commands; doctor updated for v3 paths.
- (unchanged) `src/ade/detect.py`.

**New templates**
- `src/ade/templates/AGENTS.md.j2` — canonical instruction superset (harness-neutral; the former `claude_md_section` content, expanded).
- `src/ade/templates/memory_pointer.md.j2` — the thin ADE block placed in each harness memory file.
- `src/ade/templates/skills/<skill>/SKILL.md.j2` — one folder per phase skill + driver (see Task A2 for the full set).
- `src/ade/templates/gemini_settings.json.j2`, `copilot_hooks.json.j2`, `codex_hooks.toml.j2` — per-harness hook wiring.

**Reorganized / removed templates**
- `templates/skills/phases/*.md.j2` → folded into `templates/skills/<skill>/SKILL.md.j2` bodies (Task A2), then removed.
- `templates/skills/ade-*.md.j2` composite skills → retired (Task A2/A3).
- `templates/commands/*` → removed (Task A3).
- `templates/claude_md_section.md.j2` → replaced by `AGENTS.md.j2` + `memory_pointer.md.j2` (Task B1).
- `templates/ade-routing.json.j2`, `templates/stack.md.j2` → emitted to `.ade/` instead of `.claude/` (Task B2).

**Changed docs**
- `docs/ade-architecture-design.md` — updated to the v3 layout (Task E3).
- `README.md`, `CLAUDE.md` (this repo's own) — updated for `uvx` + v3 layout (Task E1/E3).

---

# Phase A — Adapter abstraction + skills-first refactor on Claude

*Regression-safe: A1 is a pure plumbing refactor (all 84 tests stay green). A2–A5 change the Claude layout deliberately and update the pinning tests as the contract changes.*

### Task A1: Introduce the harness adapter layer (Claude only), route existing emission through it with identical output

**Files:**
- Create: `src/ade/harnesses/__init__.py`
- Create: `src/ade/harnesses/base.py`
- Modify: `src/ade/cli.py` (import + use `selected_targets`; no path changes yet)
- Test: `tests/test_harnesses.py` (new)

**Interfaces:**
- Produces: `HarnessTarget` frozen dataclass with fields used by every later task:
  `name: str`, `skills_dirs: tuple[str, ...]`, `workers_dir: str`, `worker_ext: str`,
  `worker_format: str` (`"markdown"`|`"toml"`), `hooks_dir: str`, `hook_substrate: str`,
  `memory_file: str`, `supports_at_import: bool`, `supports_subagents: bool`,
  `tier_models: dict[str, str]`, `skill_desc_budget: int`.
- Produces: `TARGETS: dict[str, HarnessTarget]` (claude only in this task) and
  `selected_targets(agent: str) -> list[HarnessTarget]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_harnesses.py
import pytest

from ade.harnesses import TARGETS, HarnessTarget, selected_targets


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_harnesses.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ade.harnesses'`

- [ ] **Step 3: Write `base.py`**

```python
# src/ade/harnesses/base.py
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
```

- [ ] **Step 4: Write `__init__.py` with the Claude target + registry**

```python
# src/ade/harnesses/__init__.py
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_harnesses.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Route the existing `init` emission through the adapter (no output change)**

In `src/ade/cli.py`, add the import and replace the hardcoded `agent` validation + the
two emission sites that name `.claude/skills/ade` and `.claude/agents` so they read from
the resolved Claude target. The emitted paths are **unchanged** in this task — only the
source of the path strings moves. Replace the validation block (currently lines 182–184):

```python
from ade.harnesses import selected_targets  # add to imports at top

# inside init(), replacing the old `if agent not in {"claude", "copilot"}` check:
try:
    targets = selected_targets(agent)
except KeyError as exc:
    rprint(f"[red]Error: unknown --agent value: {exc}[/red]")
    raise typer.Exit(1) from exc
```

Leave every existing emission line exactly as-is for now (still writing to
`.claude/skills/ade`, `.claude/agents`, `.claude/commands`, etc.). This task only proves
the adapter is wired without changing output.

- [ ] **Step 7: Run the full suite to verify no regression**

Run: `pytest`
Expected: PASS — all existing tests still green (the `--agent copilot` path still works because
`copilot` is not yet a key; see note). If `test_init_copilot_mode_emits_precommit_config` or
`test_init_rejects_unknown_agent` fail, that is expected churn handled in Step 8.

- [ ] **Step 8: Reconcile the two v2 `--agent` tests**

The old `--agent copilot` meant "pre-commit wiring." That semantics is replaced in Phase C.
For now keep v2 behavior alive by special-casing `copilot` *before* `selected_targets`:

```python
# at the top of init(), BEFORE selected_targets():
if agent == "copilot":
    legacy_copilot = True
    targets = selected_targets("claude")  # emit Claude tree; wire pre-commit below (v2)
else:
    legacy_copilot = False
    try:
        targets = selected_targets(agent)
    except KeyError as exc:
        rprint(f"[red]Error: unknown --agent value: {exc}[/red]")
        raise typer.Exit(1) from exc
```

Replace the later `if agent == "claude": ... else: # copilot` hook block's condition with
`if not legacy_copilot:` / `else:`. Run `pytest` — all 84 + 3 new tests green.

- [ ] **Step 9: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add src/ade/harnesses tests/test_harnesses.py src/ade/cli.py
git commit -m "refactor(harnesses): introduce thin per-harness adapter layer (claude)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A2: Reorganize phase skills into SKILL.md folders + the `ade-pipeline` driver; emit to `.claude/skills/` + `.agents/skills/`

**Files:**
- Create: `src/ade/templates/skills/ade-intent/SKILL.md.j2` … `ade-retro/SKILL.md.j2` (10 phase skills)
- Create: `src/ade/templates/skills/ade-pipeline/SKILL.md.j2` (driver), `ade-pr-review/SKILL.md.j2`
- Create: `src/ade/templates/skills/ade-research/references/feature-spec.md.j2`
- Move: `templates/skills/vendored/mattpocock-grill-with-docs/*` → keep as a skill folder under `skills/` (already SKILL.md form)
- Remove: `templates/skills/phases/*.md.j2`, `templates/skills/ade-code.md.j2`, `ade-plan.md.j2`, `ade-review.md.j2`, `ade-ship.md.j2`, `ade-status.md.j2`, `ade-full.md.j2`, `ade-pr-review.md.j2`, `feature-spec.md.j2`
- Modify: `src/ade/cli.py` (`_emit_skills(targets, env, project_dir, ctx)`)
- Test: `tests/test_cli.py` (update the path-pinning tests), `tests/test_skills.py` (new)

**Interfaces:**
- Consumes: `HarnessTarget.skills_dirs` (Task A1).
- Produces: `_emit_skills(targets, env, project_dir, ctx) -> None` writing each canonical
  skill folder to every unique dir in `{d for t in targets for d in t.skills_dirs}`.
- Canonical skill set (folder names, all kebab-case):
  `ade-intent ade-research ade-plan ade-design-check ade-implement ade-quality-gate
  ade-review ade-docs ade-ship ade-retro ade-pipeline ade-pr-review grill-with-docs`.

- [ ] **Step 1: Create the SKILL.md folder templates by moving phase bodies + prepending frontmatter**

For each phase, the SKILL.md *body* is the existing phase doc verbatim; prepend frontmatter.
Do this for all ten. Example for `ade-implement` (body = current
`templates/skills/phases/04-implement.md.j2`):

```bash
mkdir -p src/ade/templates/skills/ade-implement
git mv src/ade/templates/skills/phases/04-implement.md.j2 \
       src/ade/templates/skills/ade-implement/SKILL.md.j2
```

Then prepend this exact frontmatter to `ade-implement/SKILL.md.j2` (above the `# Phase 4 — Implement` line):

```markdown
---
name: ade-implement
description: ADE Phase 4 — author-separated TDD. Dispatch test-writer (RED) then implementer (GREEN); commits stay test-only / impl-only, enforced by the block-mixed-commit hook.
---
```

Repeat for the other nine using this name/description table (descriptions ≤ 350 chars):

| Folder | Body source | `name` | `description` |
|---|---|---|---|
| `ade-intent` | `phases/00-intent.md.j2` | `ade-intent` | `ADE Phase 0 — extract structured intent (type/goal/acceptance/scope) and assign a routing tier (trivial/standard/architecture) with forced-escalation. Run first.` |
| `ade-research` | `phases/01-research.md.j2` | `ade-research` | `ADE Phase 1 — produce a verified durable spec via R1–R5 (iterative-retrieval scouts, synthesis, grill, Chain-of-Verification with a spec-blind verifier).` |
| `ade-plan` | `phases/02-plan.md.j2` | `ade-plan` | `ADE Phase 2 — write the implementation plan (6 sections: context, ordered tasks, files, dependencies, test strategy, risks) from the Phase 1 spec.` |
| `ade-design-check` | `phases/03-design-check.md.j2` | `ade-design-check` | `ADE Phase 3 — dispatch a subagent in a worktree to create file stubs; review for plan alignment (max 2 iterations).` |
| `ade-implement` | `phases/04-implement.md.j2` | `ade-implement` | (above) |
| `ade-quality-gate` | `phases/05-quality-gate.md.j2` | `ade-quality-gate` | `ADE Phase 5 — run build + tests via a subagent; on failure dispatch a fixer subagent (max 3 attempts).` |
| `ade-review` | `phases/06-review.md.j2` | `ade-review` | `ADE Phase 6 — parallel logic/conventions/security review subagents reading the calibration corpus fresh; fix all HIGH/MEDIUM before proceeding.` |
| `ade-docs` | `phases/07-docs.md.j2` | `ade-docs` | `ADE Phase 7 — update docs triggered by code changes (architecture tree, endpoints, data model, conventions).` |
| `ade-ship` | `phases/08-ship.md.j2` | `ade-ship` | `ADE Phase 8 — stage, commit, push, open PR; stop at the merge gate for user review.` |
| `ade-retro` | `phases/09-retro.md.j2` | `ade-retro` | `ADE Phase 9 — record retro metrics then Codify: a read-only compounder folds findings into the calibration corpus and writes a learning. Closes the compound loop.` |

- [ ] **Step 2: Create the `ade-pipeline` driver skill (user-invoked) from the old `ade-full` body**

```bash
mkdir -p src/ade/templates/skills/ade-pipeline
git mv src/ade/templates/skills/ade-full.md.j2 \
       src/ade/templates/skills/ade-pipeline/SKILL.md.j2
```

Prepend frontmatter marking it explicitly invoked (so strict ordering never depends on
auto-activation):

```markdown
---
name: ade-pipeline
description: ADE end-to-end SDLC driver — sequences Phases 0→9 (intent→research→plan→design-check→implement→quality-gate→review→docs→ship→retro) with routing-tier masking and circuit breakers. Invoke explicitly to run a full cycle.
disable-model-invocation: true
---
```

Inside the body, update the trigger sentence to reference the driver skill rather than the
retired slash command (replace any "triggered by /ade-full" wording with "invoke the
`ade-pipeline` skill"). Keep all phase/exit-criteria/circuit-breaker content.

- [ ] **Step 3: Move `ade-pr-review` skill, the vendored grill skill, and the feature-spec reference**

```bash
mkdir -p src/ade/templates/skills/ade-pr-review
git mv src/ade/templates/skills/ade-pr-review.md.j2 \
       src/ade/templates/skills/ade-pr-review/SKILL.md.j2
mkdir -p src/ade/templates/skills/ade-research/references
git mv src/ade/templates/skills/feature-spec.md.j2 \
       src/ade/templates/skills/ade-research/references/feature-spec.md.j2
git mv src/ade/templates/skills/vendored/mattpocock-grill-with-docs \
       src/ade/templates/skills/grill-with-docs
```

Prepend the same `name:`/`description:` frontmatter to `ade-pr-review/SKILL.md.j2`:

```markdown
---
name: ade-pr-review
description: ADE post-merge loop — dispatch the pr-reviewer agent against a GitHub PR (MCP or gh fallback), apply fixes in the PR worktree, re-review. Bounded to 3 cycles; never auto-merges.
---
```

The grill skill already has compliant frontmatter (`name: grill-with-docs`, `description:`).
Its `LICENSE.j2`, `ADR-FORMAT.md.j2`, `CONTEXT-FORMAT.md.j2` move with it (attribution preserved).

- [ ] **Step 4: Remove the retired composite skill templates**

```bash
git rm src/ade/templates/skills/ade-code.md.j2 \
       src/ade/templates/skills/ade-plan.md.j2 \
       src/ade/templates/skills/ade-review.md.j2 \
       src/ade/templates/skills/ade-ship.md.j2 \
       src/ade/templates/skills/ade-status.md.j2
```

(`ade status` remains a CLI command; `ade-plan`/`ade-review`/`ade-ship` semantics now live in
the per-phase skills + driver.)

- [ ] **Step 5: Write the failing test for the new skill layout**

```python
# tests/test_skills.py
from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app

runner = CliRunner()

PHASE_SKILLS = [
    "ade-intent", "ade-research", "ade-plan", "ade-design-check", "ade-implement",
    "ade-quality-gate", "ade-review", "ade-docs", "ade-ship", "ade-retro",
]


def test_phase_skills_emit_as_skill_md_folders(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    for name in PHASE_SKILLS + ["ade-pipeline", "ade-pr-review", "grill-with-docs"]:
        skill = python_project / ".claude" / "skills" / name / "SKILL.md"
        assert skill.exists(), f"missing {name}/SKILL.md"
        head = skill.read_text()[:400]
        assert "name:" in head and "description:" in head


def test_skills_also_emit_to_shared_agents_dir(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert (python_project / ".agents" / "skills" / "ade-research" / "SKILL.md").exists()


def test_pipeline_driver_is_explicitly_invoked(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    head = (python_project / ".claude" / "skills" / "ade-pipeline" / "SKILL.md").read_text()[:400]
    assert "disable-model-invocation: true" in head


def test_old_phase_layout_is_gone(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert not (python_project / ".claude" / "skills" / "ade" / "phases").exists()
    assert not (python_project / ".claude" / "skills" / "ade" / "ade-full.md").exists()
```

- [ ] **Step 6: Run it to confirm failure**

Run: `pytest tests/test_skills.py -v`
Expected: FAIL — current code emits flat `.claude/skills/ade/*.md`, not folders.

- [ ] **Step 7: Replace the skills emission in `cli.py`**

Remove the line `_render_template_dir(env, "skills/", project_dir / ".claude" / "skills" / "ade", ctx)`
and add a folder-aware emitter:

```python
def _emit_skills(targets, env, project_dir: Path, ctx: dict) -> None:
    """Render every templates/skills/<skill>/** file into each target's skills dirs.

    SKILL.md content is identical on every harness; only the destination dirs differ.
    Each unique dir across the selected targets is written once.
    """
    dest_dirs = {d for t in targets for d in t.skills_dirs}
    prefix = "skills/"
    for template_name in env.loader.list_templates():
        if not template_name.startswith(prefix) or not template_name.endswith(".j2"):
            continue
        rel = template_name[len(prefix):-len(".j2")]  # e.g. "ade-implement/SKILL.md"
        for d in dest_dirs:
            _render_and_write(env, template_name, project_dir / d / rel, ctx)
```

Call it in `init()` where the old skills line was: `_emit_skills(targets, env, project_dir, ctx)`.

- [ ] **Step 8: Run the new test to verify it passes**

Run: `pytest tests/test_skills.py -v`
Expected: PASS (4 passed)

- [ ] **Step 9: Update the v2 path-pinning tests in `tests/test_cli.py`**

The following tests reference the old flat layout and must be updated to the folder layout.
Apply these exact path substitutions (old → new) in `tests/test_cli.py`:

- `".claude" / "skills" / "ade" / "ade-full.md"` → `".claude" / "skills" / "ade-pipeline" / "SKILL.md"`
- `".claude" / "skills" / "ade" / "ade-plan.md"` → `".claude" / "skills" / "ade-plan" / "SKILL.md"`
- `".claude" / "skills" / "ade" / "phases" / "00-intent.md"` → `".claude" / "skills" / "ade-intent" / "SKILL.md"`
- `…/ "phases" / "01-research.md"` → `".claude" / "skills" / "ade-research" / "SKILL.md"`
- `…/ "phases" / "04-implement.md"` → `".claude" / "skills" / "ade-implement" / "SKILL.md"`
- `…/ "phases" / "05-quality-gate.md"`/`06-review.md`/`07-docs.md`/`08-ship.md`/`09-retro.md` → corresponding `ade-*/SKILL.md`
- `".claude" / "skills" / "ade" / "feature-spec.md"` → `".claude" / "skills" / "ade-research" / "references" / "feature-spec.md"`
- In `test_init_generates_pr_review_command_and_skill`: drop the `commands/ade-pr-review.md`
  assertion (commands retired in A3) and point the skill assertion at `ade-pr-review/SKILL.md`.
- In `test_no_stale_stack_references`: change `claude_dir.rglob("*.md")` exclusion to also skip
  `grill-with-docs` (vendored) folders, matching the existing `"vendored" not in p.parts` intent —
  use `"grill-with-docs" not in p.parts`.

Delete the now-obsolete `test_init_generates_phase_docs` and `test_init_no_live_verification`'s
`phases/` existence assertions; replace with the equivalent checks against the new folders
(`ade-intent/SKILL.md` exists; no `07-verify` token in `ade-pipeline/SKILL.md`).

- [ ] **Step 10: Run the full suite**

Run: `pytest`
Expected: PASS. If `test_init_skills_have_phase_content` or
`test_phase4_skill_describes_author_separation` fail, update their paths the same way
(they read phase bodies that now live in `ade-*/SKILL.md`).

- [ ] **Step 11: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(skills): author pipeline as SKILL.md phase skills + ade-pipeline driver

BREAKING: skills move from .claude/skills/ade/*.md to .claude/skills/<name>/SKILL.md
and also emit to the shared .agents/skills/ dir.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A3: Retire the slash-command layer

**Files:**
- Remove: `src/ade/templates/commands/` (all 7 templates)
- Modify: `src/ade/cli.py` (drop the commands emission + the "next steps" hint)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: no `.claude/commands/` tree.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_skills.py
def test_no_command_layer_emitted(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert not (python_project / ".claude" / "commands").exists()
```

- [ ] **Step 2: Run it to confirm failure**

Run: `pytest tests/test_skills.py::test_no_command_layer_emitted -v`
Expected: FAIL — `.claude/commands/` is still emitted.

- [ ] **Step 3: Remove the commands emission and templates**

In `cli.py` delete the block:

```python
# DELETE these lines from init():
commands_dir = project_dir / ".claude" / "commands"
_render_template_dir(env, "commands/", commands_dir, ctx)
```

Then remove the templates:

```bash
git rm -r src/ade/templates/commands
```

Update the closing "Next steps" hint in `init()` (line ~281) from `/ade-full <task>` to
`ade-pipeline skill (run a full SDLC cycle)`.

- [ ] **Step 4: Update v2 command tests**

In `tests/test_cli.py`, delete the `commands/ade-full.md` and `commands/ade-ship.md`
assertions in `test_init_python_project`, and delete `test_init_generates_pr_review_command_and_skill`'s
command half (already pointed at the skill in A2).

- [ ] **Step 5: Run the full suite**

Run: `pytest`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(skills): retire the slash-command layer (skills-only)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A4: Route worker-subagent emission through the adapter

**Files:**
- Create: `src/ade/harnesses/workers.py`
- Modify: `src/ade/cli.py` (`_emit_workers`)
- Test: `tests/test_harnesses.py`

**Interfaces:**
- Consumes: `HarnessTarget.workers_dir`, `.worker_ext`, `.worker_format`, `.tier_models`.
- Produces: `render_worker(target, env, name, ctx) -> tuple[str, str]` returning
  `(relative_dest_path, content)`. Worker `name` is the template stem (e.g. `"implementer"`).
  For `worker_format == "markdown"`, content is the rendered template with `model:` remapped
  via `tier_models`. For `"toml"`, content is the TOML conversion (used by Codex in Task C3).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_harnesses.py
from jinja2 import Environment, PackageLoader

from ade.harnesses.workers import render_worker


def _env() -> Environment:
    return Environment(loader=PackageLoader("ade", "templates"), keep_trailing_newline=True)


def test_render_worker_markdown_for_claude() -> None:
    rel, content = render_worker(TARGETS["claude"], _env(), "implementer", {"info": None})
    assert rel == ".claude/agents/implementer.md"
    assert "model: sonnet" in content
    assert "implementer" in content.lower()
```

- [ ] **Step 2: Run it to confirm failure**

Run: `pytest tests/test_harnesses.py::test_render_worker_markdown_for_claude -v`
Expected: FAIL — `ade.harnesses.workers` does not exist.

- [ ] **Step 3: Write `workers.py`**

```python
# src/ade/harnesses/workers.py
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_harnesses.py::test_render_worker_markdown_for_claude -v`
Expected: PASS

- [ ] **Step 5: Use `render_worker` in `cli.py`**

Replace `_render_template_dir(env, "agents/", project_dir / ".claude" / "agents", ctx)` with:

```python
def _emit_workers(targets, env, project_dir: Path, ctx: dict) -> None:
    worker_names = [
        t[len("agents/"):-len(".md.j2")]
        for t in env.loader.list_templates()
        if t.startswith("agents/") and t.endswith(".md.j2")
    ]
    for target in targets:
        for name in worker_names:
            rel, content = render_worker(target, env, name, ctx)
            _write_file(project_dir / rel, content)
```

Call `_emit_workers(targets, env, project_dir, ctx)` in `init()`.

- [ ] **Step 6: Run the full suite**

Run: `pytest`
Expected: PASS (Claude worker paths unchanged: `.claude/agents/implementer.md` etc.).

- [ ] **Step 7: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "refactor(harnesses): emit worker subagents through the adapter

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task A5: Per-harness hook-emission framework + `_hooklib` envelope dispatch (Claude wired)

**Files:**
- Create: `src/ade/harnesses/hooks.py`
- Modify: `src/ade/templates/hooks/_hooklib.py.j2` (add `--harness` envelope dispatch)
- Modify: `src/ade/templates/claude_settings.json.j2` (hook commands gain `--harness claude`)
- Modify: `src/ade/cli.py` (`_emit_hooks` via adapter; drop the inline `_emit_claude_hooks`)
- Test: `tests/test_hooks.py`, `tests/test_harnesses.py`

**Interfaces:**
- Consumes: `HarnessTarget.hooks_dir`, `.hook_substrate`.
- Produces: `emit_hooks(target, env, project_dir, ctx) -> str` — renders the 4 hook scripts
  into `target.hooks_dir` and wires them per `hook_substrate`; returns a human action word.
  Substrate `"claude_settings"` reproduces today's `.claude/settings.json` merge behavior.
- Produces (in `_hooklib`): `gather()` selects the JSON-envelope parser from a `--harness`
  argv flag; default `"claude"`. Field-name table filled per harness in Phase C.

- [ ] **Step 1: Write the failing test for the envelope dispatch**

```python
# add to tests/test_hooks.py
import subprocess, sys, json
from pathlib import Path

def _run_hooklib_gather(tmp_path: Path, harness: str, payload: dict) -> str:
    # render the hooklib into tmp via a tiny driver that prints gather()'s command parse
    # (the test harness in tests/test_hooks.py already renders hooks; reuse its helper)
    ...

def test_hooklib_parses_claude_envelope(rendered_hooks: Path) -> None:
    # rendered_hooks fixture writes the hook scripts to a tmp dir (see existing tests)
    out = subprocess.run(
        [sys.executable, str(rendered_hooks / "block-mixed-commit.py"),
         "--stdin-json", "--harness", "claude"],
        input=json.dumps({"tool_input": {"command": "git commit -m 'x'"}}),
        capture_output=True, text=True, cwd=rendered_hooks,
    )
    # claude envelope is parsed (exit 0 with no staged files = pass)
    assert out.returncode in (0, 2)
```

> Note: `tests/test_hooks.py` already renders hook scripts to a tmp dir — read it first and
> reuse its existing fixture (do not invent a new rendering path). Adapt the call above to
> that fixture's name.

- [ ] **Step 2: Run it to confirm failure**

Run: `pytest tests/test_hooks.py -k envelope -v`
Expected: FAIL — `_hooklib.gather()` does not yet accept `--harness`.

- [ ] **Step 3: Add the per-harness envelope parser to `_hooklib.py.j2`**

Replace the `--stdin-json` branch of `gather()` with a dispatch keyed on `--harness`:

```python
def _harness() -> str:
    argv = sys.argv
    for i, a in enumerate(argv):
        if a == "--harness" and i + 1 < len(argv):
            return argv[i + 1]
    return "claude"


# Each parser maps the harness's PreToolUse JSON envelope to the shell command string.
# Field names differ per harness (Copilot uses camelCase); verified at build time in Phase C.
_ENVELOPE = {
    "claude": lambda p: str(p.get("tool_input", {}).get("command", "")),
    "gemini": lambda p: str(p.get("tool_input", {}).get("command", "")),
    "copilot": lambda p: str(p.get("toolInput", {}).get("command", "")),
    "codex": lambda p: str(p.get("tool_input", {}).get("command", "")),
}


def gather() -> tuple[list[str], str]:
    if "--stdin-json" in sys.argv:
        raw = sys.stdin.read().strip()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            sys.stderr.write("ADE hook: could not parse --stdin-json payload; skipping.\n")
            return [], ""
        parse = _ENVELOPE.get(_harness(), _ENVELOPE["claude"])
        command = parse(payload)
        if "git commit" not in command:
            return [], ""
        m = re.search(r"-m\s+(['\"])((?:\\.|[^\\])*?)\1", command, re.S)
        return staged_files(), (m.group(2) if m else "")
    msg_file = os.environ.get("PRE_COMMIT_COMMIT_MSG_FILENAME")
    if msg_file and os.path.exists(msg_file):
        return staged_files(), _read(msg_file)
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    return (argv or staged_files()), ""
```

> The `_ENVELOPE` field names for gemini/copilot/codex are confirmed against vendor docs in
> Task C0 and corrected there if needed; `claude` is the verified baseline.

- [ ] **Step 4: Add `--harness claude` to the Claude hook commands**

In `templates/claude_settings.json.j2`, append `--harness claude` to each command:

```json
{ "type": "command", "command": "python .claude/hooks/block-mixed-commit.py --stdin-json --harness claude" }
```

(do the same for `check-leftover-stub.py` and `check-escalation-paths.py`).

- [ ] **Step 5: Write `harnesses/hooks.py` with the substrate dispatch**

```python
# src/ade/harnesses/hooks.py
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


def emit_hooks(target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict) -> str:
    """Render the hook scripts into target.hooks_dir and wire them. Returns an action word."""
    _render_scripts(env, project_dir / target.hooks_dir, ctx)
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
            tgt = next(
                (b for b in existing if b.get("matcher") == ade_block.get("matcher")), None
            )
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
```

This is the existing `_emit_claude_hooks` + `_merge_hooks` logic relocated into the adapter
(verbatim behavior). The `_wire_gemini/_wire_copilot/_wire_codex` functions are stubs raising
`NotImplementedError("wired in Task C1/C2/C3")` until Phase C.

- [ ] **Step 6: Call `emit_hooks` from `cli.py` and delete the inline helpers**

In `init()`, replace the `_render_hooks(...)` call and the `if agent == "claude": action = _emit_claude_hooks(...)`
block with a per-target loop:

```python
from ade.harnesses.hooks import emit_hooks  # add import

# replace the old _render_hooks + _emit_claude_hooks block:
for target in targets:
    if target.hook_substrate == "claude_settings" or not legacy_copilot:
        action = emit_hooks(target, env, project_dir, ctx)
        rprint(f"  [green]+[/green] {action} {target.name} hooks")
```

Keep the v2 `legacy_copilot` pre-commit branch exactly as in Task A1 Step 8 (it still emits
`.claude/hooks/` + `.pre-commit-config.yaml`; that path is replaced wholesale in Phase C). Delete
the now-unused `_emit_claude_hooks`, `_merge_hooks`, and `_render_hooks` functions from `cli.py`
(they live in `harnesses/hooks.py` now).

- [ ] **Step 7: Run the full suite**

Run: `pytest`
Expected: PASS. `test_init_settings_merge_is_idempotent` now sees commands ending in
`--harness claude`; update its expected string to
`"python .claude/hooks/block-mixed-commit.py --stdin-json --harness claude"`.

- [ ] **Step 8: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "refactor(hooks): per-harness hook emission + _hooklib envelope dispatch

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

# Phase B — Canonical AGENTS.md + memory pointers + `.ade/` config move + `ade migrate`

### Task B1: Author canonical `AGENTS.md` + thin per-harness memory pointer

**Files:**
- Create: `src/ade/templates/AGENTS.md.j2` (body = current `claude_md_section.md.j2`, harness-neutral)
- Create: `src/ade/templates/memory_pointer.md.j2`
- Create: `src/ade/harnesses/memory.py`
- Modify: `src/ade/cli.py` (emit `AGENTS.md` once + a pointer per target; drop `_update_claude_md`)
- Remove: `src/ade/templates/claude_md_section.md.j2`
- Test: `tests/test_cli.py`, `tests/test_memory.py` (new)

**Interfaces:**
- Consumes: `HarnessTarget.memory_file`, `.supports_at_import`.
- Produces: `emit_memory_pointer(target, env, project_dir, ctx) -> None` writing/refreshing a
  delimited ADE block in `target.memory_file`. Block markers:
  `<!-- ADE:START -->` … `<!-- ADE:END -->`. Codex's `memory_file` is `AGENTS.md` itself →
  `emit_memory_pointer` is a no-op for it (it reads the canonical file natively).

- [ ] **Step 1: Create `AGENTS.md.j2`**

```bash
git mv src/ade/templates/claude_md_section.md.j2 src/ade/templates/AGENTS.md.j2
```

Edit the top heading of `AGENTS.md.j2` from `## ADE — Agentic Development Environment (v4)`
to `# ADE — Agentic Development Environment` (root file, h1; drop the stale "v4"). Replace the
two `.claude/ade-stack.md` and `.claude/ade-routing.json` references with `.ade/ade-stack.md`
and `.ade/ade-routing.json` (config moves in B2; do it now so AGENTS.md is correct on arrival).
Replace the trigger line "triggered by /ade-full or when the user says 'use ADE'" with
"triggered by invoking the `ade-pipeline` skill or when the user says 'use ADE'".

- [ ] **Step 2: Create `memory_pointer.md.j2`**

```jinja
<!-- ADE:START -->
## ADE — Agentic Development Environment

ADE's full workflow instructions live in [`AGENTS.md`](./AGENTS.md) at the repo root.
{% if supports_at_import %}@AGENTS.md
{% else %}See `./AGENTS.md` for the 9-phase SDLC, routing tiers, and orchestrator rules.
{% endif %}<!-- ADE:END -->
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_memory.py
from pathlib import Path
from typer.testing import CliRunner
from ade.cli import app

runner = CliRunner()


def test_agents_md_emitted_at_root(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agents = python_project / "AGENTS.md"
    assert agents.exists()
    assert "Phase 0" in agents.read_text()


def test_claude_md_has_pointer_block_not_full_workflow(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    md = (python_project / "CLAUDE.md").read_text()
    assert "<!-- ADE:START -->" in md and "<!-- ADE:END -->" in md
    assert "@AGENTS.md" in md  # Claude supports @import
    assert "Phase 1 — RESEARCH" not in md  # full workflow lives in AGENTS.md now


def test_pointer_block_is_idempotent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    md = (python_project / "CLAUDE.md").read_text()
    assert md.count("<!-- ADE:START -->") == 1


def test_existing_claude_md_preserved(python_project: Path) -> None:
    (python_project / "CLAUDE.md").write_text("# My Project\n\nMine.\n")
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    md = (python_project / "CLAUDE.md").read_text()
    assert md.startswith("# My Project") and "Mine." in md
    assert "<!-- ADE:START -->" in md
```

- [ ] **Step 4: Run to confirm failure**

Run: `pytest tests/test_memory.py -v`
Expected: FAIL — no `AGENTS.md`, `CLAUDE.md` still carries the full workflow.

- [ ] **Step 5: Write `memory.py`**

```python
# src/ade/harnesses/memory.py
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
```

- [ ] **Step 6: Wire it into `cli.py`; emit `AGENTS.md` once**

Replace the `_update_claude_md(...)` block in `init()` with:

```python
from ade.harnesses.memory import emit_memory_pointer  # import

# emit the canonical instruction file once (ADE-owned, always overwritten):
_render_and_write(env, "AGENTS.md.j2", project_dir / "AGENTS.md", ctx)
# thin pointer per harness:
for target in targets:
    emit_memory_pointer(target, env, project_dir, ctx)
```

Delete `_update_claude_md` and the `ADE_SECTION_MARKER` constant from `cli.py`.

- [ ] **Step 7: Update v2 CLAUDE.md tests**

In `tests/test_cli.py`, the four tests `test_init_creates_claude_md_with_ade_section`,
`test_init_appends_to_existing_claude_md`, `test_init_does_not_duplicate_ade_section`,
`test_claude_md_section_describes_compound_loop` now assert against the pointer block.
Repoint them: the "duplicate" check becomes `md.count("<!-- ADE:START -->") == 1`; the
"describes compound loop" content moved to `AGENTS.md` — assert those tokens in
`(project / "AGENTS.md").read_text()` instead. (These overlap `tests/test_memory.py`;
delete the now-redundant ones rather than maintain two copies.)

- [ ] **Step 8: Run the full suite**

Run: `pytest`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(memory): canonical AGENTS.md + thin per-harness pointer block

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task B2: Move user-owned config to `.ade/`

**Files:**
- Modify: `src/ade/cli.py` (routing + stack now seed into `.ade/`)
- Modify: `src/ade/templates/hooks/_hooklib.py.j2` (`load_routing_config` path → `.ade/ade-routing.json`)
- Modify: `src/ade/templates/skills/ade-intent/SKILL.md.j2` and any skill body referencing
  `.claude/ade-routing.json` / `.claude/ade-stack.md` → `.ade/...`
- Modify: `src/ade/cli.py` doctor (paths) — and `AGENTS.md.j2` already done in B1
- Test: `tests/test_cli.py`, `tests/test_hooks.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `.ade/ade-routing.json` and `.ade/ade-stack.md` (was `.claude/...`). Hooks read
  `.ade/ade-routing.json`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_cli.py
def test_config_lives_in_dot_ade(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert (python_project / ".ade" / "ade-routing.json").exists()
    assert (python_project / ".ade" / "ade-stack.md").exists()
    assert not (python_project / ".claude" / "ade-routing.json").exists()
    assert not (python_project / ".claude" / "ade-stack.md").exists()
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_cli.py::test_config_lives_in_dot_ade -v`
Expected: FAIL — config still seeds into `.claude/`.

- [ ] **Step 3: Repoint the seed destinations in `cli.py`**

Change `stack_dest = project_dir / ".claude" / "ade-stack.md"` →
`project_dir / ".ade" / "ade-stack.md"` and
`routing_dest = project_dir / ".claude" / "ade-routing.json"` →
`project_dir / ".ade" / "ade-routing.json"`. Update the two `rprint` strings to match.

- [ ] **Step 4: Repoint the hook config path**

In `_hooklib.py.j2`, change `load_routing_config`'s path:

```python
def load_routing_config() -> dict:
    path = os.path.join(".ade", "ade-routing.json")
    ...
```

- [ ] **Step 5: Repoint skill/doctor references**

Grep and update remaining literals:

```bash
grep -rl "\.claude/ade-routing.json\|\.claude/ade-stack.md" src/ade/templates src/ade/cli.py
```

In each hit (the `ade-intent` SKILL.md body, the `ade-implement`/`ade-quality-gate` bodies that
mention `.claude/ade-stack.md`, and `cli.py` doctor's `required_paths`/`bootstrap_paths`),
replace `.claude/ade-routing.json` → `.ade/ade-routing.json` and
`.claude/ade-stack.md` → `.ade/ade-stack.md`.

- [ ] **Step 6: Update the v2 config tests**

In `tests/test_cli.py`: `test_init_seeds_ade_stack_file`,
`test_init_ade_stack_seed_if_missing_preserves_edits`, `test_init_seeds_ade_routing_file`,
`test_init_ade_routing_seed_if_missing_preserves_edits`, `test_intent_skill_has_route_substep`
(asserts `ade-routing.json` substring — still fine), and `test_review_reads_calibration`
(`docs/...` unaffected). Repoint the four stack/routing path literals from `.claude/` to `.ade/`.

- [ ] **Step 7: Run the full suite**

Run: `pytest`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(config): move user-owned routing/stack config to .ade/

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task B3: `ade migrate` (v2 → v3) command

**Files:**
- Modify: `src/ade/cli.py` (new `migrate` command; `init` detects a v2 tree and nudges)
- Test: `tests/test_migrate.py` (new)

**Interfaces:**
- Consumes: `selected_targets`, the emission helpers from Phase A/B.
- Produces: `ade migrate --project-dir <p>` — idempotent. Steps:
  1. Move `.claude/ade-routing.json` → `.ade/ade-routing.json`, `.claude/ade-stack.md` →
     `.ade/ade-stack.md` (only if source exists and dest missing — preserve user edits).
  2. Remove stale generated trees: `.claude/skills/ade/`, `.claude/commands/ade_*`/`ade-*`.
  3. Re-run the v3 emission for `--agent` (default claude) — regenerates skills/workers/hooks,
     writes `AGENTS.md`, rewrites the `CLAUDE.md` ADE block to the pointer (replacing any old
     `## ADE — Agentic Development Environment (v4)` section).

- [ ] **Step 1: Write the failing test (simulate a v2 tree, then migrate)**

```python
# tests/test_migrate.py
import json
from pathlib import Path
from typer.testing import CliRunner
from ade.cli import app

runner = CliRunner()


def _make_v2_tree(p: Path) -> None:
    (p / ".claude" / "skills" / "ade" / "phases").mkdir(parents=True)
    (p / ".claude" / "skills" / "ade" / "ade-full.md").write_text("old\n")
    (p / ".claude" / "commands").mkdir(parents=True)
    (p / ".claude" / "commands" / "ade-full.md").write_text("old\n")
    (p / ".claude" / "ade-routing.json").write_text('{"escalation_globs": {"x": ["*.k"]}}\n')
    (p / ".claude" / "ade-stack.md").write_text("# user edited stack\n")
    (p / "CLAUDE.md").write_text(
        "# Mine\n\n## ADE — Agentic Development Environment (v4)\n\nold workflow\n"
    )


def test_migrate_moves_config_and_regenerates(python_project: Path) -> None:
    _make_v2_tree(python_project)
    result = runner.invoke(app, ["migrate", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    # user-owned config moved, edits preserved
    routing = python_project / ".ade" / "ade-routing.json"
    assert routing.exists() and "*.k" in routing.read_text()
    assert "user edited stack" in (python_project / ".ade" / "ade-stack.md").read_text()
    # stale generated trees gone
    assert not (python_project / ".claude" / "skills" / "ade").exists()
    assert not (python_project / ".claude" / "commands").exists()
    # v3 layout present
    assert (python_project / ".claude" / "skills" / "ade-pipeline" / "SKILL.md").exists()
    assert (python_project / "AGENTS.md").exists()
    # CLAUDE.md rewritten to a pointer, user content kept
    md = (python_project / "CLAUDE.md").read_text()
    assert md.startswith("# Mine") and "<!-- ADE:START -->" in md
    assert "(v4)" not in md


def test_migrate_is_idempotent(python_project: Path) -> None:
    _make_v2_tree(python_project)
    runner.invoke(app, ["migrate", "--project-dir", str(python_project)])
    runner.invoke(app, ["migrate", "--project-dir", str(python_project)])
    md = (python_project / "CLAUDE.md").read_text()
    assert md.count("<!-- ADE:START -->") == 1
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_migrate.py -v`
Expected: FAIL — no `migrate` command.

- [ ] **Step 3: Factor the v3 emission out of `init` into a reusable function**

Extract the body of `init()` that does the emission (after detection) into:

```python
def _emit_v3(targets, env, project_dir: Path, info, ctx: dict) -> None:
    """Emit the full v3 tree for the selected targets. Used by init and migrate."""
    _render_and_write(env, "ade_gitignore.j2", project_dir / ".ade" / ".gitignore", ctx)
    _emit_skills(targets, env, project_dir, ctx)
    _emit_workers(targets, env, project_dir, ctx)
    for target in targets:
        emit_hooks(target, env, project_dir, ctx)
    _render_and_write(env, "AGENTS.md.j2", project_dir / "AGENTS.md", ctx)
    for target in targets:
        emit_memory_pointer(target, env, project_dir, ctx)
    _seed_config(env, project_dir, ctx)       # the .ade/ routing+stack seed-if-missing
    _seed_bootstrap(env, project_dir, ctx)    # CONTEXT.md, docs/adr, etc. seed-if-missing
```

Have `init()` call `_emit_v3(...)`. (`_seed_config` and `_seed_bootstrap` wrap the existing
seed-if-missing blocks already in `init`.)

- [ ] **Step 4: Add the `migrate` command**

```python
_OLD_ADE_SECTION_RE = re.compile(
    r"(?ms)^##\s+ADE — Agentic Development Environment.*?(?=^\#\#\s|\Z)"
)


def _strip_old_claude_section(md_path: Path) -> None:
    if not md_path.exists():
        return
    text = md_path.read_text(encoding="utf-8")
    text = _OLD_ADE_SECTION_RE.sub("", text).rstrip() + "\n"
    md_path.write_text(text, encoding="utf-8")


@app.command()
def migrate(
    project_dir: Annotated[Path, typer.Option(help="Project directory to migrate")] = Path("."),
    agent: Annotated[str, typer.Option(help="Target harness(es): list or 'all'")] = "claude",
) -> None:
    """Upgrade a v2 ADE tree to the v3 layout (idempotent)."""
    project_dir = project_dir.resolve()
    targets = selected_targets(agent)
    info = detect_project(project_dir)
    env = _get_template_env()
    ctx = {"info": info}

    # 1. Move user-owned config (preserve edits: only if dest missing).
    for src_rel, dst_rel in (
        (".claude/ade-routing.json", ".ade/ade-routing.json"),
        (".claude/ade-stack.md", ".ade/ade-stack.md"),
    ):
        src, dst = project_dir / src_rel, project_dir / dst_rel
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

    # 2. Remove stale generated trees.
    shutil.rmtree(project_dir / ".claude" / "skills" / "ade", ignore_errors=True)
    shutil.rmtree(project_dir / ".claude" / "commands", ignore_errors=True)

    # 3. Strip the old CLAUDE.md ADE section, then re-emit v3 (pointer replaces it).
    _strip_old_claude_section(project_dir / "CLAUDE.md")
    _emit_v3(targets, env, project_dir, info, ctx)

    rprint("[green]Migrated to ADE v3 layout.[/green]")
```

- [ ] **Step 5: Make `init` nudge on a detected v2 tree**

Early in `init()`, after resolving `project_dir`:

```python
if (project_dir / ".claude" / "skills" / "ade").exists() or (
    project_dir / ".claude" / "commands"
).exists():
    rprint("[yellow]Detected a v2 ADE tree. Run `ade migrate` to upgrade.[/yellow]")
```

- [ ] **Step 6: Run the full suite**

Run: `pytest`
Expected: PASS (both migrate tests + no regressions).

- [ ] **Step 7: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(cli): ade migrate (v2 -> v3) + v2-tree detection in init

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

# Phase C — Gemini, Copilot, and Codex adapters

### Task C0: Verify each harness's skill dir, worker-def format, hook substrate + envelope fields

This task produces **recorded, verified constants** — not invented paths. It gates C1–C3.

**Files:**
- Create: `docs/harness-locations.md` (the verified reference table; refreshed when vendors change)
- Test: none (this is a research+record task; its output is consumed as constants in C1–C3)

- [ ] **Step 1: Verify Gemini CLI skills dir + subagent format + hook payload**

Use the context7 MCP (resolve-library-id → query-docs) for "Gemini CLI hooks" and "Gemini CLI
skills/subagents", and WebFetch `https://geminicli.com/docs/hooks/`. Record: skills dirs
(expected `.gemini/skills/`, `.agents/skills/`), subagent file location + extension + frontmatter
keys, the `.gemini/settings.json` hook schema, and the PreToolUse JSON **field path** for the
tool command. Write findings into `docs/harness-locations.md` under a `## Gemini` heading.

- [ ] **Step 2: Verify GitHub Copilot skills dir + `.agent.md` format + hook payload**

WebFetch `https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks`
and the Copilot skills docs. Record: skills dirs (`.github/skills/`, `.claude/skills/`,
`.agents/skills/`), worker `.agent.md` location/format, `.github/hooks/*.json` schema, and the
**camelCase** tool-command field path (e.g. `toolInput.command` — confirm exact name). Append to
`docs/harness-locations.md` under `## Copilot`.

- [ ] **Step 2 (cont.): Verify OpenAI Codex skills dir + TOML subagents + hooks**

WebFetch `https://developers.openai.com/codex/hooks` and the Codex skills docs. Resolve the
**open question**: does Codex read `.agents/skills/`, or need a Codex-specific dir? Record the
skills dir, the TOML subagent schema (keys for model/tools/instructions), the
`hooks.json`/`config.toml [hooks]` schema, the PreToolUse command field path, and the 8 KB
discovery-budget behavior. Append under `## Codex`.

- [ ] **Step 3: Record the model-tier identifiers per harness**

For each harness, record the model identifier strings to use for the `opus`/`sonnet`/`haiku`
tiers (or note "labels passed through unchanged"). These fill each target's `tier_models`.

- [ ] **Step 4: Commit the reference**

```bash
git add docs/harness-locations.md
git commit -m "docs(harnesses): verified per-harness skill/worker/hook locations

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

> **Downstream rule:** C1–C3 encode the values from `docs/harness-locations.md`. Where a value
> below differs from what you recorded, the recorded value wins — update the code and the golden
> test together.

---

### Task C1: Gemini adapter

**Files:**
- Modify: `src/ade/harnesses/__init__.py` (add `GEMINI` target)
- Create: `src/ade/templates/gemini_settings.json.j2`
- Modify: `src/ade/harnesses/hooks.py` (`_wire_gemini`)
- Test: `tests/test_harnesses.py`, `tests/test_golden.py` (new — golden layout per harness)

**Interfaces:**
- Consumes: `HarnessTarget`, `emit_hooks`, `_emit_skills`, `_emit_workers`, `emit_memory_pointer`.
- Produces: `TARGETS["gemini"]`. Skills → `.gemini/skills/` + `.agents/skills/`; workers →
  `.gemini/agents/*.md`; hooks → `.gemini/hooks/` wired via `.gemini/settings.json`; memory →
  `GEMINI.md` pointer (no `@import` unless C0 confirms support).

- [ ] **Step 1: Add the Gemini target (values from `docs/harness-locations.md`)**

```python
# in src/ade/harnesses/__init__.py
GEMINI = HarnessTarget(
    name="gemini",
    skills_dirs=(".gemini/skills", ".agents/skills"),
    workers_dir=".gemini/agents",
    worker_ext=".md",
    worker_format="markdown",
    hooks_dir=".gemini/hooks",
    hook_substrate="gemini_settings",
    memory_file="GEMINI.md",
    supports_at_import=False,  # set True only if C0 confirmed @import support
)
TARGETS["gemini"] = GEMINI  # add to the dict literal
```

- [ ] **Step 2: Write the failing golden test**

```python
# tests/test_golden.py
from pathlib import Path
from typer.testing import CliRunner
from ade.cli import app

runner = CliRunner()


def test_gemini_layout(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project), "--agent", "gemini"])
    assert (python_project / ".gemini" / "skills" / "ade-research" / "SKILL.md").exists()
    assert (python_project / ".agents" / "skills" / "ade-research" / "SKILL.md").exists()
    assert (python_project / ".gemini" / "agents" / "implementer.md").exists()
    assert (python_project / ".gemini" / "hooks" / "block-mixed-commit.py").exists()
    settings = python_project / ".gemini" / "settings.json"
    assert settings.exists()
    assert "block-mixed-commit.py" in settings.read_text()
    assert "--harness gemini" in settings.read_text()
    md = (python_project / "GEMINI.md").read_text()
    assert "<!-- ADE:START -->" in md and "AGENTS.md" in md
```

- [ ] **Step 3: Run to confirm failure**

Run: `pytest tests/test_golden.py::test_gemini_layout -v`
Expected: FAIL — no `gemini_settings.json.j2`, `_wire_gemini` raises NotImplementedError.

- [ ] **Step 4: Create `gemini_settings.json.j2`**

Use the schema recorded in C0. Expected shape (PreToolUse blocking, same script set):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "run_shell_command",
        "hooks": [
          { "type": "command", "command": "python .gemini/hooks/block-mixed-commit.py --stdin-json --harness gemini" },
          { "type": "command", "command": "python .gemini/hooks/check-leftover-stub.py --stdin-json --harness gemini" },
          { "type": "command", "command": "python .gemini/hooks/check-escalation-paths.py --stdin-json --harness gemini" }
        ]
      }
    ]
  }
}
```

> The `matcher` value (`run_shell_command` vs `Bash`) and key names come from C0 — correct them
> to the recorded schema.

- [ ] **Step 5: Implement `_wire_gemini` in `hooks.py`**

```python
def _wire_gemini(target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict) -> str:
    dest = project_dir / ".gemini" / "settings.json"
    ade = json.loads(env.get_template("gemini_settings.json.j2").render(**ctx))
    return _merge_into_json_settings(dest, ade)
```

Extract the create-or-merge tail shared with `_wire_claude` into `_merge_into_json_settings(dest, ade) -> str`
(the body currently in `_wire_claude` after computing `ade`), and have both call it. Confirm C0's
gemini command field path matches the `_ENVELOPE["gemini"]` parser in `_hooklib`; correct if needed.

- [ ] **Step 6: Run the golden test + full suite**

Run: `pytest tests/test_golden.py::test_gemini_layout -v && pytest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(harnesses): Gemini CLI adapter (skills, workers, hooks, memory)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task C2: Copilot adapter

**Files:**
- Modify: `src/ade/harnesses/__init__.py` (add `COPILOT` target)
- Create: `src/ade/templates/copilot_hooks.json.j2`
- Modify: `src/ade/harnesses/hooks.py` (`_wire_copilot`), `src/ade/harnesses/workers.py` (`.agent.md`)
- Test: `tests/test_golden.py`

**Interfaces:**
- Produces: `TARGETS["copilot"]`. Skills → `.github/skills/` + `.agents/skills/`; workers →
  `.github/agents/*.agent.md`; hooks → `.github/hooks/` wired via `.github/hooks/*.json`; memory →
  `.github/copilot-instructions.md` pointer. Envelope: camelCase (`_ENVELOPE["copilot"]`).

- [ ] **Step 1: Add the Copilot target (values from C0)**

```python
COPILOT = HarnessTarget(
    name="copilot",
    skills_dirs=(".github/skills", ".agents/skills"),
    workers_dir=".github/agents",
    worker_ext=".agent.md",
    worker_format="markdown",
    hooks_dir=".github/hooks",
    hook_substrate="copilot_hooks",
    memory_file=".github/copilot-instructions.md",
    supports_at_import=False,
)
TARGETS["copilot"] = COPILOT
```

- [ ] **Step 2: Write the failing golden test**

```python
# add to tests/test_golden.py
def test_copilot_layout(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project), "--agent", "copilot"])
    assert (python_project / ".github" / "skills" / "ade-research" / "SKILL.md").exists()
    assert (python_project / ".github" / "agents" / "implementer.agent.md").exists()
    assert (python_project / ".github" / "hooks").exists()
    hook_json = next((python_project / ".github" / "hooks").glob("*.json"))
    assert "--harness copilot" in hook_json.read_text()
    md = (python_project / ".github" / "copilot-instructions.md").read_text()
    assert "<!-- ADE:START -->" in md and "AGENTS.md" in md
```

> This test replaces the v2 `--agent copilot` meaning (pre-commit). Delete the v2 tests
> `test_init_copilot_mode_emits_precommit_config` and `test_init_copilot_seed_if_missing_preserves_existing`
> and the `legacy_copilot` branch in `cli.py` — `copilot` is now a real harness target.

- [ ] **Step 3: Run to confirm failure**

Run: `pytest tests/test_golden.py::test_copilot_layout -v`
Expected: FAIL.

- [ ] **Step 4: Remove the `legacy_copilot` special case from `cli.py`**

Delete the `if agent == "copilot": legacy_copilot = True ...` block (Task A1 Step 8) and the
pre-commit emission branch. `selected_targets("copilot")` now returns the real target. Remove the
now-dead `pre-commit-config.yaml.j2` reference from `init` (keep the template file for the
optional fallback documented in the spec, but it is no longer auto-emitted).

- [ ] **Step 5: Create `copilot_hooks.json.j2`** (schema from C0)

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "match": { "tool": "shell" },
        "run": "python .github/hooks/block-mixed-commit.py --stdin-json --harness copilot"
      },
      {
        "match": { "tool": "shell" },
        "run": "python .github/hooks/check-leftover-stub.py --stdin-json --harness copilot"
      },
      {
        "match": { "tool": "shell" },
        "run": "python .github/hooks/check-escalation-paths.py --stdin-json --harness copilot"
      }
    ]
  }
}
```

> Correct the key names (`preToolUse`, `match`, `run`) to the exact schema recorded in C0.
> Filename: emit as `.github/hooks/ade.json` (or per C0's expected filename).

- [ ] **Step 6: Implement `_wire_copilot`**

```python
def _wire_copilot(target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict) -> str:
    dest = project_dir / ".github" / "hooks" / "ade.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = env.get_template("copilot_hooks.json.j2").render(**ctx)
    dest.write_text(content, encoding="utf-8")  # ADE-owned file, safe to overwrite
    return "Created" if not dest.exists() else "Refreshed"
```

Confirm `_ENVELOPE["copilot"]` field path (camelCase) matches C0; correct in `_hooklib.py.j2` if needed.

- [ ] **Step 7: Run the golden test + full suite**

Run: `pytest tests/test_golden.py::test_copilot_layout -v && pytest`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(harnesses): GitHub Copilot adapter; retire v2 --agent copilot semantics

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task C3: Codex adapter (degraded tier) + TOML worker format

**Files:**
- Modify: `src/ade/harnesses/__init__.py` (add `CODEX` target)
- Modify: `src/ade/harnesses/workers.py` (`_to_toml` real implementation)
- Create: `src/ade/templates/codex_hooks.toml.j2`, `src/ade/templates/codex-degraded-note.md.j2`
- Modify: `src/ade/harnesses/hooks.py` (`_wire_codex`)
- Test: `tests/test_harnesses.py`, `tests/test_golden.py`

**Interfaces:**
- Produces: `TARGETS["codex"]`. `supports_subagents=False`. Skills → Codex skills dir (from C0)
  + `.agents/skills/`; workers → TOML; hooks → `hooks.toml`/`config.toml [hooks]`; memory →
  `AGENTS.md` (native, no pointer). Plus a generated `.ade/codex-degraded.md` explaining the
  sequential/user-gated orchestration tier.

- [ ] **Step 1: Add the Codex target (skills dir from C0)**

```python
CODEX = HarnessTarget(
    name="codex",
    skills_dirs=(".codex/skills", ".agents/skills"),  # correct .codex/skills to C0's recorded dir
    workers_dir=".codex/agents",
    worker_ext=".toml",
    worker_format="toml",
    hooks_dir=".codex/hooks",
    hook_substrate="codex_toml",
    memory_file="AGENTS.md",  # read natively; emit_memory_pointer no-ops
    supports_subagents=False,
)
TARGETS["codex"] = CODEX
```

- [ ] **Step 2: Write the failing test for TOML worker conversion**

```python
# add to tests/test_harnesses.py
def test_render_worker_toml_for_codex() -> None:
    rel, content = render_worker(TARGETS["codex"], _env(), "implementer", {"info": None})
    assert rel == ".codex/agents/implementer.toml"
    assert content.startswith("model =") or "model =" in content
    assert "instructions =" in content
    assert "'''" in content  # body as a TOML multi-line string
```

- [ ] **Step 3: Run to confirm failure**

Run: `pytest tests/test_harnesses.py::test_render_worker_toml_for_codex -v`
Expected: FAIL — `_to_toml` raises NotImplementedError.

- [ ] **Step 4: Implement `_to_toml` in `workers.py`**

```python
def _to_toml(markdown: str) -> str:
    """Convert `--- model: X\\ntools: [...] --- body` to Codex TOML.

    Emits `model = "X"`, `tools = [...]` (as a TOML array), and the body as
    `instructions = '''...'''`. Keys absent from the frontmatter are omitted.
    """
    fm: dict[str, str] = {}
    body = markdown
    if markdown.startswith("---"):
        _, raw_fm, body = markdown.split("---", 2)
        for line in raw_fm.strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()
    lines: list[str] = []
    if "model" in fm:
        lines.append(f'model = "{fm["model"]}"')
    if "tools" in fm:
        # tools frontmatter is already a [a, b] list; re-emit as a TOML array of strings.
        items = [t.strip() for t in fm["tools"].strip("[]").split(",") if t.strip()]
        arr = ", ".join(f'"{t}"' for t in items)
        lines.append(f"tools = [{arr}]")
    body_clean = body.strip().replace("'''", "''")
    lines.append(f"instructions = '''\n{body_clean}\n'''")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 5: Create the degraded-tier note + Codex hook wiring**

`codex-degraded-note.md.j2`:

```markdown
# Codex degraded tier

Codex CLI cannot autonomously dispatch subagents (openai/codex#18513), so ADE's
author-separation and spec-blind verification run as **in-context conventions** here:
either grant the requested delegation when ADE asks, or run phases **sequentially** in a
single context. The deterministic gates still hold — native Codex PreToolUse hooks enforce
G1 (author separation), G2 (no leftover stubs), and G4 (escalation floor), and `git
pre-commit` remains as a fallback. Upgrade path: revisit when #18513 lands.
```

`codex_hooks.toml.j2` (schema from C0 — `hooks.toml` or a `[hooks]` block in `config.toml`):

```toml
[[hooks.pre_tool_use]]
command = "python .codex/hooks/block-mixed-commit.py --stdin-json --harness codex"

[[hooks.pre_tool_use]]
command = "python .codex/hooks/check-leftover-stub.py --stdin-json --harness codex"

[[hooks.pre_tool_use]]
command = "python .codex/hooks/check-escalation-paths.py --stdin-json --harness codex"
```

- [ ] **Step 6: Implement `_wire_codex` + emit the note**

```python
def _wire_codex(target: HarnessTarget, env: Environment, project_dir: Path, ctx: dict) -> str:
    dest = project_dir / ".codex" / "hooks.toml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(env.get_template("codex_hooks.toml.j2").render(**ctx), encoding="utf-8")
    note = project_dir / ".ade" / "codex-degraded.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(env.get_template("codex-degraded-note.md.j2").render(**ctx), encoding="utf-8")
    return "Created"
```

> Correct the hook filename/location (`.codex/hooks.toml` vs `config.toml [hooks]`) to C0.

- [ ] **Step 7: Write the Codex golden test**

```python
# add to tests/test_golden.py
def test_codex_layout(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project), "--agent", "codex"])
    assert (python_project / ".agents" / "skills" / "ade-research" / "SKILL.md").exists()
    assert (python_project / ".codex" / "agents" / "implementer.toml").exists()
    assert (python_project / "AGENTS.md").exists()
    assert (python_project / ".ade" / "codex-degraded.md").exists()
    # Codex reads AGENTS.md natively → no separate memory pointer file
    assert "instructions =" in (python_project / ".codex" / "agents" / "implementer.toml").read_text()
```

- [ ] **Step 8: Run golden + full suite**

Run: `pytest tests/test_golden.py::test_codex_layout -v && pytest`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(harnesses): Codex adapter (TOML workers, native hooks, degraded-tier note)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task C4: `--agent` list/all parsing + `--agent all` integration test

**Files:**
- Modify: `src/ade/cli.py` (friendly validation message listing valid names)
- Test: `tests/test_golden.py`

**Interfaces:**
- Consumes: `selected_targets`.
- Produces: `--agent all` emits a valid tree for all four; `--agent claude,gemini` emits both;
  unknown names exit non-zero with the valid list.

- [ ] **Step 1: Write the failing tests**

```python
# add to tests/test_golden.py
def test_agent_all_emits_every_harness(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project), "--agent", "all"])
    assert result.exit_code == 0
    assert (python_project / ".claude" / "skills" / "ade-research" / "SKILL.md").exists()
    assert (python_project / ".gemini" / "agents" / "implementer.md").exists()
    assert (python_project / ".github" / "agents" / "implementer.agent.md").exists()
    assert (python_project / ".codex" / "agents" / "implementer.toml").exists()
    assert (python_project / ".agents" / "skills" / "ade-research" / "SKILL.md").exists()
    assert (python_project / "AGENTS.md").exists()


def test_agent_list_emits_subset(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project), "--agent", "claude,gemini"])
    assert (python_project / ".gemini" / "skills" / "ade-research" / "SKILL.md").exists()
    assert not (python_project / ".github").exists()


def test_unknown_agent_lists_valid_names(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project), "--agent", "cursor"])
    assert result.exit_code != 0
    assert "claude" in result.output and "gemini" in result.output
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_golden.py -k agent -v`
Expected: `test_unknown_agent_lists_valid_names` FAILs (message doesn't list names).

- [ ] **Step 3: Improve the validation message in `cli.py`**

```python
try:
    targets = selected_targets(agent)
except KeyError as exc:
    valid = ", ".join(sorted(TARGETS))  # import TARGETS
    rprint(f"[red]Error: unknown --agent value {exc}. Valid: {valid}, or 'all'.[/red]")
    raise typer.Exit(1) from exc
```

- [ ] **Step 4: Run the full suite**

Run: `pytest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(cli): --agent accepts a list or 'all'; friendly validation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

# Phase D — Static skill-quality gate (`ade eval`)

### Task D1: `ade eval` static checks

**Files:**
- Create: `src/ade/eval.py`
- Modify: `src/ade/cli.py` (`eval` command)
- Test: `tests/test_eval.py` (new)

**Interfaces:**
- Produces: `run_eval(skills_root: Path) -> list[Finding]` where
  `Finding = namedtuple("Finding", "skill level message")` (`level` ∈ `{"error","warn"}`).
  Checks each `<skill>/SKILL.md`: (1) parseable YAML frontmatter; (2) required `name` +
  `description`; (3) `name` matches the folder name; (4) `description` length ≤
  `skill_desc_budget` (350); (5) anti-patterns (empty description, description starting with
  "This skill"). `ade eval` prints findings and exits non-zero if any `error`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_eval.py
from pathlib import Path
from typer.testing import CliRunner
from ade.cli import app
from ade.eval import run_eval

runner = CliRunner()


def test_eval_passes_on_generated_skills(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    result = runner.invoke(app, ["eval", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    assert "PASS" in result.output or "0 error" in result.output


def test_eval_flags_overlong_description(tmp_path: Path) -> None:
    skill = tmp_path / "ade-bad" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    long_desc = "x" * 400
    skill.write_text(f"---\nname: ade-bad\ndescription: {long_desc}\n---\nbody\n")
    findings = run_eval(tmp_path)
    assert any(f.level == "error" and "description" in f.message for f in findings)


def test_eval_flags_missing_frontmatter(tmp_path: Path) -> None:
    skill = tmp_path / "ade-x" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("no frontmatter here\n")
    findings = run_eval(tmp_path)
    assert any(f.level == "error" for f in findings)


def test_eval_flags_name_folder_mismatch(tmp_path: Path) -> None:
    skill = tmp_path / "ade-x" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: ade-y\ndescription: ok short desc\n---\nbody\n")
    findings = run_eval(tmp_path)
    assert any("name" in f.message for f in findings)
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_eval.py -v`
Expected: FAIL — no `ade.eval` module, no `eval` command.

- [ ] **Step 3: Write `eval.py`**

```python
# src/ade/eval.py
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
            findings.append(Finding(folder, "warn", "description starts with 'This skill' (filler)"))
    return findings
```

- [ ] **Step 4: Add the `eval` command to `cli.py`**

```python
from ade.eval import run_eval  # import

@app.command()
def eval(  # noqa: A001 - intentional command name
    project_dir: Annotated[Path, typer.Option(help="Project directory")] = Path("."),
) -> None:
    """Statically check generated skills for quality (frontmatter, lean descriptions)."""
    project_dir = project_dir.resolve()
    roots = [
        project_dir / ".claude" / "skills",
        project_dir / ".agents" / "skills",
    ]
    seen: set[str] = set()
    findings = []
    for root in roots:
        if not root.is_dir():
            continue
        for f in run_eval(root):
            key = f"{f.skill}:{f.message}"
            if key not in seen:
                seen.add(key)
                findings.append(f)
    errors = [f for f in findings if f.level == "error"]
    for f in findings:
        color = "red" if f.level == "error" else "yellow"
        rprint(f"  [{color}]{f.level.upper()}[/{color}]  {f.skill}: {f.message}")
    if errors:
        rprint(f"[red]{len(errors)} error(s).[/red]")
        raise typer.Exit(1)
    rprint("[green]PASS — skills well-formed.[/green]")
```

- [ ] **Step 5: Run the eval tests + full suite**

Run: `pytest tests/test_eval.py -v && pytest`
Expected: PASS. If `test_eval_passes_on_generated_skills` fails, a generated skill's
description exceeds 350 chars — shorten it in its `SKILL.md.j2` frontmatter (this is the gate
doing its job).

- [ ] **Step 6: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(eval): static skill-quality gate (ade eval)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

# Phase E — Distribution (`uvx`) + docs + build-time location verification

### Task E1: `uvx` distribution + README/doctor

**Files:**
- Modify: `pyproject.toml` (confirm `[project.scripts] ade = "ade.cli:app"`; metadata for `uvx`)
- Modify: `README.md` (uvx quickstart)
- Modify: `src/ade/cli.py` doctor (mention `uvx`)
- Test: `tests/test_cli.py` (doctor output)

- [ ] **Step 1: Confirm the console-script entry point**

Read `pyproject.toml`; ensure `[project.scripts]` has `ade = "ade.cli:app"`. If missing, add it.
`uvx ade-toolkit init` resolves the `ade` script from the published package — no code change beyond
the entry point. (No failing test needed for a metadata check; verify by `uvx --from . ade --help`
in Step 4.)

- [ ] **Step 2: Update README quickstart**

Replace the install/run section of `README.md` with the `uvx` one-liner as the primary path:

```markdown
## Quickstart

Zero-install (recommended):

    uvx ade-toolkit init --agent all     # or: --agent claude,gemini

Or install:

    pip install ade-toolkit
    ade init --agent claude
```

Document `--agent` values (`claude`, `gemini`, `copilot`, `codex`, comma-list, or `all`), the
`ade migrate` upgrade path, and `ade eval`.

- [ ] **Step 3: Doctor mentions uvx (write the failing test first)**

```python
# add to tests/test_cli.py
def test_doctor_mentions_uvx(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    with patch("ade.cli._check_command", return_value=True):
        result = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert "uvx" in result.output
```

Run it (FAIL), then add a one-line `uvx` hint to the doctor "Next steps"/summary block, rerun (PASS).

- [ ] **Step 4: Verify the entry point resolves**

Run: `uvx --from . ade --help`
Expected: prints the ADE CLI help (commands: init, doctor, status, migrate, eval).

- [ ] **Step 5: Commit**

```bash
ruff format src/ tests/ && ruff check src/ tests/
git add -A
git commit -m "feat(dist): uvx quickstart + docs; doctor hints uvx

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task E2: Build-time location-verification test

**Files:**
- Create: `tests/test_locations.py`
- Consumes: `docs/harness-locations.md` (C0) + `TARGETS`

**Interfaces:**
- Produces: a test asserting each target's structural constants match the verified reference, so
  a silent vendor-path drift fails CI with a pointer to refresh `docs/harness-locations.md`.

- [ ] **Step 1: Write the test (it encodes the verified contract)**

```python
# tests/test_locations.py
from ade.harnesses import TARGETS

# Mirror of docs/harness-locations.md (C0). Update BOTH together when a vendor changes paths.
EXPECTED = {
    "claude":  {"skills": ".claude/skills",  "memory": "CLAUDE.md"},
    "gemini":  {"skills": ".gemini/skills",  "memory": "GEMINI.md"},
    "copilot": {"skills": ".github/skills",  "memory": ".github/copilot-instructions.md"},
    "codex":   {"skills": ".codex/skills",   "memory": "AGENTS.md"},
}


def test_every_target_matches_verified_locations() -> None:
    assert set(TARGETS) == set(EXPECTED)
    for name, exp in EXPECTED.items():
        t = TARGETS[name]
        assert exp["skills"] in t.skills_dirs, f"{name} skills dir drifted from docs/harness-locations.md"
        assert t.memory_file == exp["memory"]
        assert ".agents/skills" in t.skills_dirs  # shared convergence dir always present


def test_codex_is_degraded_tier() -> None:
    assert TARGETS["codex"].supports_subagents is False
```

> If C0 recorded a different Codex skills dir, update both `EXPECTED` here and the `CODEX` target.

- [ ] **Step 2: Run it + full suite**

Run: `pytest tests/test_locations.py -v && pytest`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_locations.py
git commit -m "test(harnesses): pin verified per-harness locations against drift

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task E3: Update architecture docs + this repo's CLAUDE.md + final regression sweep + version bump

**Files:**
- Modify: `docs/ade-architecture-design.md`
- Modify: `CLAUDE.md` (this repo's project instructions)
- Modify: `pyproject.toml` (`version = "3.0.0"`)
- Test: full suite

- [ ] **Step 1: Update `docs/ade-architecture-design.md`**

Replace the v2 layout description with the v3 split: SKILL.md phase skills + `ade-pipeline`
driver; `src/ade/harnesses/` adapter layer; `.agents/skills/` shared dir; per-harness worker
defs + native hooks; `.ade/` config; root `AGENTS.md` + memory pointers; `ade migrate` / `ade eval`.
Reference `docs/superpowers/specs/2026-06-21-platform-agnostic-ade-design.md` and ADR-0003.

- [ ] **Step 2: Update this repo's `CLAUDE.md`**

Update the "Project Structure" tree and the prose: `templates/skills/` now holds SKILL.md folders
(not `phases/` + composites); `templates/commands/` is gone; add `src/ade/harnesses/`, `src/ade/eval.py`;
note `.ade/` config, `AGENTS.md`, `ade migrate`, `ade eval`, and the four-harness `--agent` contract.
Update the "External skills are vendored" path to `src/ade/templates/skills/grill-with-docs/`.

- [ ] **Step 3: Bump the version**

In `pyproject.toml`, set `version = "3.0.0"`.

- [ ] **Step 4: Full regression sweep**

Run: `pytest && ruff check src/ tests/ && ruff format --check src/ tests/`
Expected: all green, no lint/format diffs.

- [ ] **Step 5: Smoke-test `--agent all` end to end**

Run:

```bash
rm -rf /tmp/ade-smoke && mkdir -p /tmp/ade-smoke && cd /tmp/ade-smoke && git init -q
python -c "import subprocess,sys; subprocess.run([sys.executable,'-m','ade','init','--agent','all','--project-dir','.'])" 2>/dev/null || ade init --agent all --project-dir .
ade eval --project-dir .
```

Expected: a tree with `.claude/`, `.gemini/`, `.github/`, `.codex/`, `.agents/skills/`, `AGENTS.md`,
`.ade/ade-routing.json`; `ade eval` prints PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs+release: v3.0.0 — platform-agnostic ADE (four harnesses, skills-first)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review Notes (for the executor)

- **Regression safety:** A1 is pure plumbing (84 tests stay green); every contract change after
  it (A2 skill folders, A3 commands retired, B1 memory split, B2 config move, C2 copilot semantics)
  updates its pinning tests in the same task. Never leave the suite red across a commit.
- **Open questions resolved in-plan:** C0 verifies the three spec open questions (Codex skills dir;
  per-harness hook envelope field names; worker-def locations/format) against current vendor docs
  and records them in `docs/harness-locations.md`; C1–C3 and E2 consume those recorded values — the
  "expected" constants in this plan are best-known defaults to be overwritten by C0's findings.
- **Type consistency:** `HarnessTarget` fields (A1) are used verbatim by `render_worker` (A4),
  `emit_hooks` (A5), `emit_memory_pointer` (B1), and every adapter (C1–C3). `Finding` (D1) and
  `selected_targets` (A1) are the other cross-task contracts.
- **No personas / blind verifier:** unchanged — worker bodies move verbatim; no role framing added.
```
