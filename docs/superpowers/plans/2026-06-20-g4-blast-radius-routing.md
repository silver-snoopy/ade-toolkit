# G4 — Blast-radius routing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add tiered blast-radius routing to ADE — a Phase-0 sub-step classifies each task `trivial` / `standard` / `architecture`, masks which phases run, and a deterministic Ship-time hook enforces forced-escalation floors that the orchestrator (no diff at Phase 0) can only best-effort guess.

**Architecture:** Mostly Jinja2 template + small Python. The deterministic backbone is a new commit hook (`check-escalation-paths.py`) sharing `_hooklib`, with a hardcoded security baseline that `.claude/ade-routing.json` may only extend. Routing is prose the orchestrator runs inside Phase 0; tier masking and the architecture-tier Plan Soundness Review are documented in the phase/composite skills. A new read-only `plan-reviewer` agent backs the architecture tier.

**Tech Stack:** Python 3.11+, Typer, Jinja2, pytest, ruff. Hooks under `src/ade/templates/hooks/`; the existing G1/G2 hooks (`_hooklib.py`, `block-mixed-commit.py`, `check-leftover-stub.py`) are the pattern to follow.

## Global Constraints

- Python 3.11+; type hints on public functions; ruff line-length 99. `ruff check src/ tests/` and `ruff format --check src/ tests/` clean; `pytest` green before every commit.
- Hooks honor the one exit-code contract in `_hooklib`: `0` = pass, `_hooklib.BLOCK` (=2) = reject. They run under two substrates via `_hooklib.gather()`: git/pre-commit (filenames as argv) and Claude PreToolUse (`--stdin-json`, files via `git diff --cached`). Reuse `gather()` — do not re-implement file collection.
- The escalation hook's authority is the **routing contract, scoped to ADE-routed tasks**: it acts only when HEAD is on an `ade/<task-id>` branch AND `.ade/tasks/<task-id>/routing.md` exists; otherwise it is a **no-op** (must never break non-ADE commits).
- **Security baseline is un-removable.** Escalation globs = a hardcoded baseline compiled into the hook ∪ `escalation_globs` from `.claude/ade-routing.json`. A missing/malformed config → baseline-only (warn), never fail-open-to-nothing. Config can only extend.
- Glob matching uses `fnmatch.fnmatchcase` on posix-normalized paths (`\` → `/`). fnmatch `*` spans `/`, so patterns are written `*`-style (e.g. `*/migrations/*`, `*.sql`), not `**`-style. Over-inclusive matching is the safe direction for a security floor.
- Tier vocabulary is fixed: `trivial` / `standard` / `architecture` (see `CONTEXT.md`). `standard` = today's full 0–9 flow, unchanged.
- Routing is the closing sub-step of **Phase 0** ("0d — Route") — NOT a new numbered phase and NOT an un-numbered step. There is **no** `route.md.j2`.
- The architecture-tier adversarial plan review is named **"Plan Soundness Review"** and is layered *after* the existing all-tier `◆ PLAN GATE` (completeness). Do not conflate the two.
- The G5 stale-reference guard (`tests/test_cli.py::test_no_stale_stack_references`) must still pass: new `.md` templates carry no `@vitals`/`backend-coder`/`Playwright`/etc. (`ade-routing.json` is `.json`, outside that guard's `.md` glob, but keep its example paths stack-neutral.)
- Source spec: `docs/superpowers/specs/2026-06-20-g4-blast-radius-routing-design.md`. Companion: `CONTEXT.md` (glossary), `docs/adr/0001-hybrid-blast-radius-routing-classifier.md`. These two were written during grilling — do not recreate them.

---

## File Structure

**New files**
- `src/ade/templates/hooks/check-escalation-paths.py.j2` — the deterministic Ship-time escalation hook.
- `src/ade/templates/ade-routing.json.j2` — seeded routing config (escalation globs + orchestrator keywords/thresholds).
- `src/ade/templates/agents/plan-reviewer.md.j2` — architecture-tier, fresh-context, read-only plan reviewer.

**Edited files**
- `src/ade/templates/hooks/_hooklib.py.j2` — add branch/task-id, routing-tier, config-load, glob-match helpers.
- `src/ade/cli.py` — render the new hook; seed `ade-routing.json`; add both to `doctor`.
- `src/ade/templates/claude_settings.json.j2`, `src/ade/templates/pre-commit-config.yaml.j2` — wire the hook.
- `src/ade/templates/skills/phases/00-intent.md.j2` — the "0d — Route" sub-step + tier vocab.
- `src/ade/templates/skills/ade-full.md.j2` — Phase-0 routing announce/confirm, per-phase masking, Plan Soundness Review, forced-escalation rules, circuit breaker.
- `src/ade/templates/skills/ade-code.md.j2`, `src/ade/templates/skills/ade-review.md.j2` — honor tier masking.
- `src/ade/templates/claude_md_section.md.j2` — document tiers + routing pointer + hook.
- `docs/ade-architecture-design.md` — routing section, hook-layer, subagent catalog, circuit-breaker.
- `tests/test_hooks.py`, `tests/test_cli.py` — new + updated tests.

---

## Task 1: `_hooklib` helpers + the `check-escalation-paths` hook

**Files:**
- Modify: `src/ade/templates/hooks/_hooklib.py.j2`
- Create: `src/ade/templates/hooks/check-escalation-paths.py.j2`
- Test: `tests/test_hooks.py`

**Interfaces:**
- Produces (in `_hooklib`): `current_branch() -> str`, `current_task_id() -> str | None`, `routing_tier(task_id: str) -> str | None`, `load_routing_config() -> dict`, `glob_match(path: str, pattern: str) -> bool`, `any_glob(path: str, patterns: list[str]) -> bool`.
- Produces (hook): `check-escalation-paths.py` rendering to `.claude/hooks/`. Routing artifact contract: `.ade/tasks/<task-id>/routing.md` contains a line `Tier: <trivial|standard|architecture>`. Config contract: `.claude/ade-routing.json` has `escalation_globs.architecture` / `escalation_globs.standard` lists.

- [ ] **Step 1: Add the new-hook fixture support + failing tests**

In `tests/test_hooks.py`, update the templates tuple (line 10) so the fixture renders the new hook:
```python
HOOK_TEMPLATES = (
    "_hooklib.py",
    "block-mixed-commit.py",
    "check-leftover-stub.py",
    "check-escalation-paths.py",
)
```

Add these helpers + tests at the end of `tests/test_hooks.py`:
```python
def _route(repo: Path, task_id: str, tier: str) -> None:
    """Put the repo on an ade/<task-id> branch with a routing.md recording the tier."""
    _git(repo, "checkout", "-q", "-b", f"ade/{task_id}")
    rd = repo / ".ade" / "tasks" / task_id
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "routing.md").write_text(f"Tier: {tier}\n", encoding="utf-8")


def test_escalation_hook_blocks_below_floor(hook_repo: Path) -> None:
    _route(hook_repo, "feat-x", "standard")
    _write_stage(hook_repo, "src/db/migrations/001_add.sql", "CREATE TABLE t (id int);\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "src/db/migrations/001_add.sql")
    assert result.returncode == 2, result.stderr
    assert "architecture" in result.stderr


def test_escalation_hook_allows_when_floor_met(hook_repo: Path) -> None:
    _route(hook_repo, "feat-x", "architecture")
    _write_stage(hook_repo, "src/db/migrations/001_add.sql", "CREATE TABLE t (id int);\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "src/db/migrations/001_add.sql")
    assert result.returncode == 0, result.stderr


def test_escalation_hook_noop_off_ade_branch(hook_repo: Path) -> None:
    # hook_repo is on the default branch (not ade/*); migration must NOT be blocked.
    _write_stage(hook_repo, "src/db/migrations/001_add.sql", "CREATE TABLE t (id int);\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "src/db/migrations/001_add.sql")
    assert result.returncode == 0, result.stderr


def test_escalation_hook_baseline_holds_without_config(hook_repo: Path) -> None:
    # No .claude/ade-routing.json at all; baseline must still block an auth change at trivial.
    _route(hook_repo, "feat-x", "trivial")
    _write_stage(hook_repo, "src/auth/login.py", "def login():\n    return True\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "src/auth/login.py")
    assert result.returncode == 2, result.stderr
    assert "standard" in result.stderr


def test_escalation_hook_config_extends_baseline(hook_repo: Path) -> None:
    _route(hook_repo, "feat-x", "standard")
    cfg = hook_repo / ".claude" / "ade-routing.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text('{"escalation_globs": {"architecture": ["*.weird"]}}\n', encoding="utf-8")
    _write_stage(hook_repo, "thing.weird", "x\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "thing.weird")
    assert result.returncode == 2, result.stderr


def test_escalation_hook_malformed_config_falls_back_to_baseline(hook_repo: Path) -> None:
    _route(hook_repo, "feat-x", "trivial")
    cfg = hook_repo / ".claude" / "ade-routing.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("{ not json", encoding="utf-8")
    _write_stage(hook_repo, "src/auth/login.py", "def login():\n    return True\n")
    result = _run_hook(hook_repo, "check-escalation-paths.py", "src/auth/login.py")
    assert result.returncode == 2, result.stderr  # baseline still enforced
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `pytest tests/test_hooks.py -v -k escalation`
Expected: FAIL — `check-escalation-paths.py` template does not exist, so the fixture render raises (or the hook is missing).

- [ ] **Step 3: Add helpers to `_hooklib.py.j2`**

In `src/ade/templates/hooks/_hooklib.py.j2`, add `import fnmatch` to the import block (after `import json`). Then append these functions at the end of the file (after `gather()`):

```python
def current_branch() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, check=False,
        encoding="utf-8", errors="replace",
    )
    return out.stdout.strip() if out.returncode == 0 else ""


def current_task_id() -> str | None:
    """ADE routes work on `ade/<task-id>` branches; return <task-id> or None."""
    b = current_branch()
    prefix = "ade/"
    return b[len(prefix):] if b.startswith(prefix) else None


def routing_tier(task_id: str) -> str | None:
    """Read the tier recorded by Phase-0 routing in .ade/tasks/<id>/routing.md."""
    path = os.path.join(".ade", "tasks", task_id, "routing.md")
    text = _read(path)
    if not text:
        return None
    m = re.search(r"(?im)^\s*Tier:\s*(trivial|standard|architecture)\b", text)
    return m.group(1).lower() if m else None


def load_routing_config() -> dict:
    """Parse .claude/ade-routing.json; {} on missing or malformed (caller uses baseline)."""
    path = os.path.join(".claude", "ade-routing.json")
    raw = _read(path)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.stderr.write("ADE hook: ade-routing.json is malformed; using baseline only.\n")
        return {}
    return data if isinstance(data, dict) else {}


def glob_match(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path.replace("\\", "/"), pattern)


def any_glob(path: str, patterns: list[str]) -> bool:
    return any(glob_match(path, p) for p in patterns)
```

- [ ] **Step 4: Create the hook `check-escalation-paths.py.j2`**

Create `src/ade/templates/hooks/check-escalation-paths.py.j2`:
```python
#!/usr/bin/env python3
"""Block an ADE-routed task from committing escalation-path changes below its floor (G4).

Scoped to ADE-routed work: acts only on an `ade/<task-id>` branch with a routing.md.
A hardcoded baseline of escalation globs is enforced even if .claude/ade-routing.json is
missing or malformed; the config may only EXTEND the baseline, never shrink it.
"""
from __future__ import annotations

import sys

import _hooklib as h

# Floors. fnmatch '*' spans '/', so patterns are '*'-style (not '**'). Over-inclusive is
# the safe direction for a security floor. Config can only add to these.
BASELINE_GLOBS: dict[str, list[str]] = {
    "architecture": [
        "*/migrations/*", "*.sql", "*schema.*", "*openapi.*", "*.proto",
        "*/routes/*", "*/api/*", "docs/adr/*", "*/models/*",
    ],
    "standard": [
        "*/auth/*", "*secret*", "*crypto*", "*/security/*", "*.env*", "*credential*",
    ],
}
TIER_RANK = {"trivial": 0, "standard": 1, "architecture": 2}


def _escalation_globs() -> dict[str, list[str]]:
    globs = {floor: list(pats) for floor, pats in BASELINE_GLOBS.items()}
    cfg = h.load_routing_config().get("escalation_globs", {})
    if isinstance(cfg, dict):
        for floor in ("architecture", "standard"):
            extra = cfg.get(floor)
            if isinstance(extra, list):
                globs[floor].extend(str(g) for g in extra)
    return globs


def main() -> int:
    files, _ = h.gather()
    if not files:
        return 0
    task_id = h.current_task_id()
    if task_id is None:
        return 0  # not an ADE-routed branch — not our business
    tier = h.routing_tier(task_id)
    if tier is None:
        return 0  # routing never recorded — treat as non-ADE, no-op
    rank = TIER_RANK.get(tier, TIER_RANK["standard"])  # unknown tier → conservative
    globs = _escalation_globs()
    violations: list[tuple[str, str]] = []
    for f in files:
        if rank < TIER_RANK["architecture"] and h.any_glob(f, globs["architecture"]):
            violations.append((f, "architecture"))
        elif rank < TIER_RANK["standard"] and h.any_glob(f, globs["standard"]):
            violations.append((f, "standard"))
    if violations:
        lines = "\n  ".join(f"{path}  (needs floor: {floor})" for path, floor in violations)
        sys.stderr.write(
            f"ADE hook: task routed '{tier}' but the diff touches escalation paths:\n  "
            + lines
            + "\nRe-route this task up to the required floor before committing "
            "(routing is the closing sub-step of Phase 0).\n"
        )
        return h.BLOCK
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_hooks.py -v`
Expected: PASS (all hook tests, including the 6 new escalation tests and the pre-existing G1/G2 ones).

- [ ] **Step 6: Lint and commit**

```bash
ruff check src/ade/templates/hooks/check-escalation-paths.py.j2 src/ade/templates/hooks/_hooklib.py.j2 tests/test_hooks.py
git add src/ade/templates/hooks/_hooklib.py.j2 src/ade/templates/hooks/check-escalation-paths.py.j2 tests/test_hooks.py
git commit -m "feat: add deterministic escalation-paths hook for routing floors (G4)"
```
(Note: ruff lints the `.j2` files as if Python — they are valid Python with no Jinja interpolation, like the existing hooks. If ruff cannot parse a `.j2`, skip those two paths in the ruff command; the rendered-hook tests are the real check.)

---

## Task 2: Seed `.claude/ade-routing.json`

**Files:**
- Create: `src/ade/templates/ade-routing.json.j2`
- Modify: `src/ade/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: nothing (static defaults).
- Produces: `.claude/ade-routing.json` (seed-if-missing). Read by the orchestrator (Phase 0) and the hook (Task 1).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py`:
```python
def test_init_seeds_ade_routing_file(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    routing = python_project / ".claude" / "ade-routing.json"
    assert routing.exists()
    data = json.loads(routing.read_text())
    assert "escalation_globs" in data
    assert "architecture" in data["escalation_globs"]
    assert "keywords" in data


def test_init_ade_routing_seed_if_missing_preserves_edits(python_project: Path) -> None:
    routing = python_project / ".claude" / "ade-routing.json"
    routing.parent.mkdir(parents=True, exist_ok=True)
    routing.write_text('{"escalation_globs": {"architecture": ["*.custom"]}}\n')
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert "*.custom" in routing.read_text()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_cli.py -v -k ade_routing`
Expected: FAIL — `ade-routing.json` not generated.

- [ ] **Step 3: Create the config template**

Create `src/ade/templates/ade-routing.json.j2` (static; the leading comment lives in the spec, JSON has no comments):
```json
{
  "escalation_globs": {
    "architecture": [
      "*/migrations/*", "*.sql", "*schema.*", "*openapi.*", "*.proto",
      "*/routes/*", "*/api/*", "docs/adr/*", "*/models/*"
    ],
    "standard": [
      "*/auth/*", "*secret*", "*crypto*", "*/security/*", "*.env*", "*credential*"
    ]
  },
  "size_thresholds": { "architecture_file_count": 10 },
  "keywords": {
    "architecture": ["schema", "migration", "public api", "breaking change", "data model"],
    "standard": ["auth", "authentication", "authorization", "secret", "credential", "crypto", "security", "permission", "data loss"]
  }
}
```

- [ ] **Step 4: Wire the seed into `cli.py`**

In `src/ade/cli.py`, in `init`, immediately after the `.claude/ade-stack.md` seed block (the block ending at line 236 with the "Kept existing .claude/ade-stack.md" print) and before the `# Update CLAUDE.md with ADE section` comment, add:
```python
    # Seed .claude/ade-routing.json (G4) — routing config, seed-if-missing, user-owned.
    routing_dest = project_dir / ".claude" / "ade-routing.json"
    if _render_and_write_if_missing(env, "ade-routing.json.j2", routing_dest, ctx):
        rprint("  [green]+[/green] Created .claude/ade-routing.json")
    else:
        rprint("  [dim]= Kept existing .claude/ade-routing.json[/dim]")
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_cli.py -v -k ade_routing`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ade/templates/ade-routing.json.j2 src/ade/cli.py tests/test_cli.py
git commit -m "feat: seed .claude/ade-routing.json routing config (G4)"
```

---

## Task 3: Render + wire + doctor the escalation hook

**Files:**
- Modify: `src/ade/cli.py`, `src/ade/templates/claude_settings.json.j2`, `src/ade/templates/pre-commit-config.yaml.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: the hook from Task 1.
- Produces: `.claude/hooks/check-escalation-paths.py` rendered + wired in both substrates; `doctor` checks it.

- [ ] **Step 1: Write/extend the failing tests**

In `tests/test_cli.py`, extend `test_init_claude_mode_emits_settings_and_hooks` (after the existing `check-leftover-stub.py` assertion, ~line 215) with:
```python
    assert (python_project / ".claude" / "hooks" / "check-escalation-paths.py").exists()
    assert "check-escalation-paths.py" in settings.read_text()
```
Extend `test_init_copilot_mode_emits_precommit_config` (after the `ade-block-mixed-commit` assertion) with:
```python
    assert "ade-check-escalation-paths" in cfg.read_text()
    assert (python_project / ".claude" / "hooks" / "check-escalation-paths.py").exists()
```
Add a doctor test:
```python
def test_doctor_checks_escalation_hook(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    (python_project / ".claude" / "hooks" / "check-escalation-paths.py").unlink()
    with patch("ade.cli._check_command", return_value=True):
        result = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert result.exit_code == 1
    assert "FAIL" in result.output
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_cli.py -v -k "escalation_hook or claude_mode_emits or copilot_mode_emits"`
Expected: FAIL — hook not rendered/wired/checked yet.

- [ ] **Step 3: Render the hook in `cli.py`**

In `src/ade/cli.py` `_render_hooks` (line 109), extend the tuple:
```python
    for name in (
        "_hooklib.py",
        "block-mixed-commit.py",
        "check-leftover-stub.py",
        "check-escalation-paths.py",
    ):
```

- [ ] **Step 4: Add the doctor check**

In `src/ade/cli.py` `doctor`, in `required_paths` (after the `check-leftover-stub.py` entry, line 323), add:
```python
        (".claude/hooks/check-escalation-paths.py", "Commit hook: check-escalation-paths (G4)"),
```

- [ ] **Step 5: Wire claude substrate**

In `src/ade/templates/claude_settings.json.j2`, add a third command to the `hooks` array:
```json
          { "type": "command", "command": "python .claude/hooks/check-leftover-stub.py --stdin-json" },
          { "type": "command", "command": "python .claude/hooks/check-escalation-paths.py --stdin-json" }
```
(Insert the escalation line after the leftover-stub line; mind the comma.)

- [ ] **Step 6: Wire copilot substrate**

In `src/ade/templates/pre-commit-config.yaml.j2`, append after the `ade-check-leftover-stub` hook:
```yaml
      - id: ade-check-escalation-paths
        name: ADE — no escalation-path changes below routed floor
        entry: python .claude/hooks/check-escalation-paths.py
        language: system
        stages: [pre-commit]
```

- [ ] **Step 7: Run the tests + full suite**

Run: `pytest tests/test_cli.py -v -k "escalation_hook or claude_mode_emits or copilot_mode_emits or settings_merge or doctor_checks_hook"`
Expected: PASS. (The merge-idempotency test `test_init_settings_merge_is_idempotent` asserts on `block-mixed-commit`'s count — unaffected — but run it to be safe.)

Run: `pytest -q`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add src/ade/cli.py src/ade/templates/claude_settings.json.j2 src/ade/templates/pre-commit-config.yaml.j2 tests/test_cli.py
git commit -m "feat: render, wire, and doctor the escalation hook (G4)"
```

---

## Task 4: The `plan-reviewer` agent (architecture tier)

**Files:**
- Create: `src/ade/templates/agents/plan-reviewer.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `.claude/agents/plan-reviewer.md` (model `sonnet`, read-only tools). Dispatched only in the architecture-tier Plan Soundness Review (documented in Task 6).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:
```python
def test_init_generates_plan_reviewer_agent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agent = python_project / ".claude" / "agents" / "plan-reviewer.md"
    assert agent.exists()
    content = agent.read_text()
    assert "model:" in content and "sonnet" in content
    assert "plan" in content.lower()
    assert "refute" in content.lower() or "adversarial" in content.lower()
    assert "acceptance criteria" in content.lower()
    # read-only: no Write/Edit/Bash in the tool list
    assert "Write" not in content and "Edit" not in content and "Bash" not in content
    # language-agnostic
    assert "@vitals" not in content
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_cli.py::test_init_generates_plan_reviewer_agent -v`
Expected: FAIL — agent not generated.

- [ ] **Step 3: Create the agent template**

Create `src/ade/templates/agents/plan-reviewer.md.j2`:
```markdown
---
model: sonnet
tools: [Read, Grep, Glob]
---
You are an adversarial plan reviewer for an architecture-tier (high-blast-radius) change.
You run in a fresh context and were NOT given the planning reasoning — you see only the
spec and the plan file. Your job is to try to REFUTE the plan against the spec, not to
agree with it. Read-only: you never edit files.

You receive: the finalized spec and the plan at `.ade/tasks/<task-id>/plan.md`.

Check the plan for these REJECT conditions and report each one you find:
- **Hallucinated reference** — a file path, module, or symbol the plan names that does not
  exist in the repo (verify with Grep/Glob).
- **Weak acceptance criteria** — criteria that are vague, procedural, or not expressible as
  an automated test (the suite is the acceptance mechanism).
- **Uncovered criterion** — a spec acceptance criterion with no task that implements it.
- **Scope creep** — the plan solves more than the spec asks (adjacent work folded in).
- **Missing edge cases** — fewer than two edge cases for non-trivial behavior.
- **Missing ADR** — a hard-to-reverse / surprising decision with no ADR proposed.

Output a structured verdict:
- For each finding: the REJECT condition, the offending plan location, and why.
- End with `VERDICT: APPROVE` (no blocking findings) or `VERDICT: REJECT` (one or more).

You do not fix anything — the orchestrator routes REJECTs back to planning (max 2
iterations, then escalate to the user).
```

- [ ] **Step 4: Run the test + commit**

Run: `pytest tests/test_cli.py::test_init_generates_plan_reviewer_agent -v`
Expected: PASS.

```bash
git add src/ade/templates/agents/plan-reviewer.md.j2 tests/test_cli.py
git commit -m "feat: add architecture-tier plan-reviewer agent (G4)"
```

---

## Task 5: `00-intent.md.j2` — the "0d — Route" sub-step

**Files:**
- Modify: `src/ade/templates/skills/phases/00-intent.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `00-intent.md` documenting routing as the closing sub-step of Phase 0, with the tier vocabulary and the announce/confirm gate.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:
```python
def test_intent_skill_has_route_substep(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    intent = (
        python_project / ".claude" / "skills" / "ade" / "phases" / "00-intent.md"
    ).read_text()
    assert "0d — Route" in intent or "0d - Route" in intent
    for tier in ("trivial", "standard", "architecture"):
        assert tier in intent
    assert "ade-routing.json" in intent
    assert "forced-escalation" in intent.lower() or "escalation" in intent.lower()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_cli.py::test_intent_skill_has_route_substep -v`
Expected: FAIL.

- [ ] **Step 3: Add the routing sub-step**

In `src/ade/templates/skills/phases/00-intent.md.j2`, after the `## Task ID Convention` section at the end of the file, append:
```markdown
## 0d — Route (closing sub-step of Phase 0)

Once intent is captured, assign the task a **routing tier** from `Type` + `Affected Areas`
+ `Estimated Scope`. This masks which later phases run. There are three tiers:

- **trivial** — a tiny, self-contained change (a copy/comment/config one-liner, or a small
  isolated fix). Cut-down path: lightweight inline research, short inline plan, no
  design-check, single review pass, no retro — but ALWAYS author-separated TDD, the
  deterministic quality gate, and the merge gate.
- **standard** — the full nine-phase flow. The default.
- **architecture** — standard plus extra rigor: at least one ADR and an adversarial Plan
  Soundness Review before code.

### Classification

1. **Forced-escalation first (deterministic).** Read `.claude/ade-routing.json`. If any
   declared affected area (or the intent text) matches an `escalation_globs.architecture`
   path or an `architecture` keyword → tier is **architecture**. Else if it matches an
   `escalation_globs.standard` path or a `standard` keyword (security/auth/secrets/crypto/
   data-loss) → floor is **standard** (never trivial). If the config is missing or
   unparseable, treat the change as **≥ standard** (conservative).
2. **Size judgment (only within the non-forced band).** A change with no escalation match
   and a small, single-area scope (≈ size `S`) → **trivial**; otherwise **standard**.

A forced-escalation floor can never be overridden downward — and the
`check-escalation-paths` commit hook enforces it against the real diff at Ship time, so a
mis-route is caught even though Phase 0 has no diff yet.

### Record, announce, gate

- Write the tier + a one-line rationale to `.ade/tasks/<task-id>/routing.md` as a line
  `Tier: <trivial|standard|architecture>` (the hook reads this), and update `status.md`
  with `Routed: <tier>`.
- **Announce** the tier + rationale.
- **trivial / standard:** auto-proceed (announced); the user may interject to re-tier up.
- **architecture, or any forced-escalation:** require explicit user confirmation before
  proceeding. Overriding **up** is always allowed; overriding **down out of a forced
  floor** is refused.

> Routing accuracy depends on the intent: name security/auth/schema/public-API impact
> explicitly in `Affected Areas` when present.
```

- [ ] **Step 4: Run the test + full suite**

Run: `pytest tests/test_cli.py::test_intent_skill_has_route_substep -v`
Expected: PASS.
Run: `pytest tests/test_cli.py::test_no_stale_stack_references -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ade/templates/skills/phases/00-intent.md.j2 tests/test_cli.py
git commit -m "docs: add 0d-Route sub-step + tier vocabulary to Phase 0 (G4)"
```

---

## Task 6: `ade-full.md.j2` — routing announce, phase masking, Plan Soundness Review

**Files:**
- Modify: `src/ade/templates/skills/ade-full.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `ade-full.md` carrying the Phase-0 routing announce/confirm, per-phase masking annotations, the architecture Plan Soundness Review (after the PLAN GATE), the forced-escalation rules, and a routing circuit-breaker line.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:
```python
def test_ade_full_describes_routing_and_tiers(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    full = (python_project / ".claude" / "skills" / "ade" / "ade-full.md").read_text()
    for tier in ("trivial", "standard", "architecture"):
        assert tier in full
    assert "Plan Soundness Review" in full
    assert "skipped for" in full.lower() or "skip for" in full.lower()  # masking annotations
    assert "ade-routing.json" in full or "forced-escalation" in full.lower()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_cli.py::test_ade_full_describes_routing_and_tiers -v`
Expected: FAIL.

- [ ] **Step 3: Add the routing announce + gate to Phase 0**

In `src/ade/templates/skills/ade-full.md.j2`, in the `## Phase 0 — INTENT` section, replace the line:
```markdown
**Exit criteria:** Goal and acceptance criteria clearly stated. Intent file saved.
```
with:
```markdown
**Then route (closing sub-step 0d):** assign a tier — `trivial` / `standard` /
`architecture` — from Type + Affected Areas + Scope, applying the forced-escalation rules
in `.claude/ade-routing.json` first (security/auth/secrets/crypto/data-loss → floor
`standard`; schema/migration/public-API/ADR-or-model → `architecture`; config unparseable →
treat as ≥ standard). Record `Tier: <tier>` to `.ade/tasks/<task-id>/routing.md`, announce
it, and — for `architecture` or any forced-escalation — get explicit user confirmation
before Phase 1. The tier masks which phases run (see each phase heading). See
[phases/00-intent.md](phases/00-intent.md) for the full routing rules.

**Exit criteria:** Goal and acceptance criteria clearly stated. Intent file saved. Tier
assigned, recorded, and (if architecture/forced) confirmed.
```

- [ ] **Step 4: Annotate the maskable phase headings**

Add a masking note under each of these headings (immediately after the heading line):

`## Phase 1 — RESEARCH` →
```markdown

*(trivial: a single lightweight inline scout — no grill/CoVe. standard/architecture: full R1–R5.)*
```
`## Phase 2 — PLAN` →
```markdown

*(trivial: short inline plan, no Plan agent.)*
```
`## Phase 3 — DESIGN CHECK` →
```markdown

*(skipped for `trivial`.)*
```
`## Phase 6 — REVIEW` →
```markdown

*(trivial: a single quick review pass instead of the full fan.)*
```
`## Phase 7 — DOCUMENTATION` →
```markdown

*(trivial: only if a doc trigger fires. architecture: required.)*
```
`## Phase 9 — RETROSPECTIVE` →
```markdown

*(skipped for `trivial`.)*
```

- [ ] **Step 5: Add the Plan Soundness Review after the PLAN GATE**

In `ade-full.md.j2`, immediately after the `## ◆ PLAN GATE ◆` section block (after its body, before `## Phase 3 — DESIGN CHECK`), insert:
```markdown
## ★ PLAN SOUNDNESS REVIEW (architecture tier only) ★

For `architecture`-routed tasks only, after the PLAN GATE's completeness check passes,
dispatch the fresh-context `plan-reviewer` subagent (it never sees the planning reasoning).
It tries to refute the plan against the spec — hallucinated paths, weak/uncovered
acceptance criteria, scope creep, missing edge cases, missing ADR for a hard-to-reverse
decision — and returns `VERDICT: APPROVE | REJECT`.

- On REJECT: fix the plan and re-review. **Max 2 iterations**, then escalate to the user.
- `trivial` / `standard` tasks skip this step.

This is distinct from the PLAN GATE: the gate is a structural completeness check (all 6
sections present) for every tier; this is an adversarial correctness check for architecture
tasks only.
```

- [ ] **Step 6: Add the routing circuit breaker**

In the `## Circuit Breakers` list, add:
```markdown
- Plan Soundness Review (architecture): max 2 iterations
```

- [ ] **Step 7: Run the test + guard + suite**

Run: `pytest tests/test_cli.py -v -k "routing_and_tiers or phase_content or no_live_verification or no_stale"`
Expected: PASS.
Run: `pytest -q`
Expected: green.

- [ ] **Step 8: Commit**

```bash
git add src/ade/templates/skills/ade-full.md.j2 tests/test_cli.py
git commit -m "docs: wire routing, phase masking, and Plan Soundness Review into ade-full (G4)"
```

---

## Task 7: Composite skills + `claude_md_section` tier awareness

**Files:**
- Modify: `src/ade/templates/skills/ade-code.md.j2`, `src/ade/templates/skills/ade-review.md.j2`, `src/ade/templates/claude_md_section.md.j2`

**Interfaces:**
- Produces: the composite code/review skills honor tier masking; the always-loaded CLAUDE.md section documents the tiers, the routing config, and the new hook.

- [ ] **Step 1: `ade-code.md.j2` — note design-check masking**

In `src/ade/templates/skills/ade-code.md.j2`, after the `## Phase 3 — DESIGN CHECK` heading's first line, add:
```markdown
*(skipped for `trivial`-routed tasks — go straight to Implement.)*
```

- [ ] **Step 2: `ade-review.md.j2` — note review masking + Plan Soundness Review**

In `src/ade/templates/skills/ade-review.md.j2`, under `## Phase 6 — REVIEW`, after the Hard requirement line, add:
```markdown
*(Tier masking: `trivial` runs a single quick review pass instead of the full fan;
`architecture` additionally had a Plan Soundness Review before code, in Phase 2.)*
```

- [ ] **Step 3: `claude_md_section.md.j2` — document routing**

In `src/ade/templates/claude_md_section.md.j2`, immediately after the `**Phase 0 — INTENT**` block (the bullet list ending with `Save to .ade/tasks/<task-id>/intent.md`), add:
```markdown

**Routing (closing sub-step of Phase 0):** assign a tier — `trivial` / `standard` /
`architecture` — that masks which phases run. `standard` is the full flow; `trivial` cuts
ceremony (keeps TDD + quality gate + merge gate); `architecture` adds an ADR + a Plan
Soundness Review. Forced-escalation (security/auth/secrets/schema/migration/public-API)
raises the tier deterministically and is enforced by the `check-escalation-paths` hook.
Rules + globs live in `.claude/ade-routing.json`.
```

Then in the `### Circuit Breaker` list, add:
```markdown
- Plan Soundness Review (architecture): max 2 iterations
```

- [ ] **Step 4: Run the guard + suite**

Run: `pytest tests/test_cli.py -v -k "no_stale or creates_claude_md or skills_have_phase_content"`
Expected: PASS.
Run: `pytest -q`
Expected: green.

- [ ] **Step 5: Commit**

```bash
git add src/ade/templates/skills/ade-code.md.j2 src/ade/templates/skills/ade-review.md.j2 src/ade/templates/claude_md_section.md.j2
git commit -m "docs: honor routing tiers in composite skills + CLAUDE.md section (G4)"
```

---

## Task 8: Architecture doc

**Files:**
- Modify: `docs/ade-architecture-design.md`

**Interfaces:**
- Produces: the architecture doc documents routing, the new hook, the plan-reviewer agent, and the routing circuit breaker.

- [ ] **Step 1: Note routing in the SDLC table caption / human-gates line**

In `docs/ade-architecture-design.md`, on the human-gates line (the one reading `Human gates: after R5 (ready-for-development), after Phase 2 (plan completeness), after Phase 8 (merge decision).`), append:
```markdown
 For `architecture`-routed tasks, an additional confirmation gate follows Phase-0 routing.
```

- [ ] **Step 2: Add the routing section**

After the `## The 9-phase SDLC` table block (before `## Phase 1 — Research (detailed)`), insert:
```markdown
## Blast-radius routing (G4)

The closing sub-step of Phase 0 assigns a **tier** that masks which phases run:

- **trivial** — tiny self-contained change: lightweight inline research, no design-check,
  single review pass, no retro — but always author-separated TDD, the deterministic quality
  gate, and the merge gate.
- **standard** — the full nine-phase flow (default).
- **architecture** — standard + ≥1 ADR + an adversarial Plan Soundness Review before code.

**Hybrid classifier.** The orchestrator judges trivial-vs-standard from the intent; a
deterministic rule set decides **forced-escalation** — security/auth/secrets/crypto/
data-loss force a floor of `standard`, and schema/migrations/public-API/ADR-or-model force
`architecture`, regardless of estimated size. Rules + globs live in the user-owned
`.claude/ade-routing.json`.

**Two-layer enforcement.** Phase 0 applies the rules to the *declared* affected areas (no
diff exists yet). The `check-escalation-paths` commit hook re-checks the *actual* diff at
Ship time against a hardcoded baseline (which config can only extend) — the non-evadable
guarantee, scoped to ADE-routed tasks (`ade/<task-id>` branches). See
`docs/adr/0001-hybrid-blast-radius-routing-classifier.md`.

The Phase-0 S/M/L scope estimate now *feeds* the router rather than being purely
informational.
```

- [ ] **Step 3: Add the hook to the hook-layer section**

In the `### Checks` list under `## Deterministic hook layer (G2)`, add:
```markdown
- **`check-escalation-paths.py`** — for an ADE-routed task (`ade/<task-id>` branch), rejects
  a commit whose diff touches escalation paths (security/auth/secrets, schema/migrations,
  public-API) below the task's routed floor. Baseline globs are compiled in;
  `.claude/ade-routing.json` may only extend them. No-op off an `ade/*` branch.
```

- [ ] **Step 4: Add the plan-reviewer to the subagent catalog**

In the subagent catalog table, after the `test-runner` row, add:
```markdown
| `plan-reviewer` | sonnet | Read, Grep, Glob | Phase 2 (architecture tier) |
```

- [ ] **Step 5: Add the routing circuit breaker**

In the `## Circuit breakers (consolidated)` table, add a row:
```markdown
| Plan Soundness Review (architecture) | 2 iterations | Escalate to user |
```

- [ ] **Step 6: Commit**

```bash
git add docs/ade-architecture-design.md
git commit -m "docs: document blast-radius routing in the architecture doc (G4)"
```

---

## Task 9: Final verification + mark spec implemented

**Files:**
- Modify: `docs/superpowers/specs/2026-06-20-g4-blast-radius-routing-design.md`

- [ ] **Step 1: Full suite + lint + guard**

Run: `pytest -q`
Expected: all green (the new escalation tests, routing-config seed, plan-reviewer, intent route sub-step, ade-full routing, doctor, and the still-passing G5 stale-reference guard).

Run: `ruff check src/ tests/ && ruff format --check src/ tests/`
Expected: clean. If `ruff format --check` flags files, run `ruff format src/ tests/` and re-run the suite.

- [ ] **Step 2: Manual end-to-end render check**

Run a real init into a temp dir and confirm the routing tree renders:
```bash
python -m ade init --project-dir /tmp/g4-check 2>&1 | tail -20
ls /tmp/g4-check/.claude/ade-routing.json /tmp/g4-check/.claude/hooks/check-escalation-paths.py /tmp/g4-check/.claude/agents/plan-reviewer.md
grep -c "trivial\|architecture" /tmp/g4-check/.claude/skills/ade/ade-full.md
rm -rf /tmp/g4-check
```
Expected: all three paths exist; grep count > 0.

- [ ] **Step 3: Mark the spec implemented**

In `docs/superpowers/specs/2026-06-20-g4-blast-radius-routing-design.md`, change the status line to:
```markdown
**Status:** Implemented
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-06-20-g4-blast-radius-routing-design.md
git commit -m "docs: mark G4 spec implemented"
```

---

## Self-Review

**Spec coverage** (spec section → task):
- §3.1 Routing as Phase-0 sub-step → Task 5 (00-intent), Task 6 (ade-full announce). ✅
- §3.2 per-tier phase map + Plan Soundness Review → Task 6 (masking annotations + review gate). ✅
- §3.3 `ade-routing.json` (config, extend-only) → Task 2 (template+seed), Task 1 (hook union). ✅
- §3.4 `check-escalation-paths` hook (task-id from branch, baseline ∪ config, malformed→baseline, scoped no-op) → Task 1; wiring/doctor → Task 3. ✅
- §3.5 `plan-reviewer` agent → Task 4. ✅
- §3.6 phase-skill & composite ripple → Tasks 6, 7. ✅
- §3.7 cli & detection (seed, render, wire, doctor; detect.py untouched) → Tasks 2, 3. ✅
- §3.8 docs → Task 8. ✅
- §5 tests (hook block/allow/no-op/baseline/extend, routing seed, plan-reviewer, intent sub-step, ade-full routing, doctor) → distributed; guard re-checked in Tasks 5–7 and Task 9. ✅
- §6 edge cases (no diff at P0, mis-route caught by hook, non-ADE no-op, malformed config baseline, override rules) → covered by Task 1 tests + Task 5 prose. ✅

**Placeholder scan:** none — every code step has full content; every doc step has exact old→new or append text.

**Type/name consistency:** `_hooklib` helper names (`current_task_id`, `routing_tier`, `load_routing_config`, `any_glob`) are defined in Task 1 and used by the hook in the same task. Routing artifact line format `Tier: <tier>` is identical in the hook (Task 1), the tests (Task 1), and the 00-intent prose (Task 5). Config key `escalation_globs.{architecture,standard}` is identical across the template (Task 2), the hook union (Task 1), and the tests (Task 1). Tier names `trivial`/`standard`/`architecture` and "Plan Soundness Review" are used identically everywhere. The hook filename `check-escalation-paths.py` matches across Task 1 (render in test fixture), Task 3 (cli render + wiring + doctor), and Task 8 (doc).

**Known intentional choices:** `detect.py` is untouched (config defaults are stack-neutral, per spec §3.7). The `ade-routing.json` example globs use fnmatch `*`-style (not the spec's illustrative `**/` strings) because the hook uses `fnmatch.fnmatchcase`; this is the spec's intent, finalized — noted in Global Constraints.
