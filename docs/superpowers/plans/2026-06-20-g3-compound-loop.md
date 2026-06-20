# G3 — Compound Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ADE's Phase 9 compound — each task deposits durable knowledge (a `docs/learnings/` Learning + a `docs/review-calibration.md` finding-class corpus) that Phase 1 and Phase 6 read back, so the next task is cheaper.

**Architecture:** Pure scaffolder change — no runtime code. Three new Jinja2 templates (a `compounder` subagent, two seeded bootstrap artifacts), `cli.py` wiring to seed + doctor-check the artifacts, and prose edits to four phase skills (09-retro adds a "Codify" sub-step; 06-review reads the corpus + persists its output; 01-research reads learnings back) plus two composite skills and two docs. Everything is prose-driven and non-gating (see ADR 0002); no new hook.

**Tech Stack:** Python 3.11+, Typer, Jinja2, pytest, ruff (line-length 99). Templates render from `src/ade/templates/` into a target project's tree.

## Global Constraints

- Python 3.11+; type hints on all public functions; ruff line-length 99. (Copy verbatim from `CLAUDE.md`.)
- Conventional commits; commit trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- `pytest` green before every commit; `ruff check src/ tests/` and `ruff format src/ tests/` clean.
- **User-owned artifacts are seed-if-missing, never overwritten** — use `_render_and_write_if_missing` (`cli.py:50`). Applies to the two new bootstrap artifacts.
- **Stale-reference guard** (`tests/test_cli.py::test_no_stale_stack_references`) scans `.claude/**/*.md` + `CLAUDE.md` and forbids: `@vitals`, `-w @`, `backend-coder`, `frontend-coder`, `Playwright`, `docker compose`, `localhost`, `NO EXEMPTIONS`, `07-verify`, `qa-verify`, `/10`. Every new/edited `.md.j2` rendering under `.claude/` (the `compounder` agent and all skill edits) must contain none of these. (The two `docs/` bootstrap files render outside this scan but keep them clean anyway.)
- **Terminology (from `CONTEXT.md` Compound loop section, hardened during grill):** the artifact is a **Learning** (not "solution"); the metric is the **review-findings signal** (not "SLI"); the Phase-9 sub-step is **Codify**; **frequency orders the corpus, never promotes severity**.
- Agents auto-render via `_render_template_dir(env, "agents/", ...)` (`cli.py:206`), which strips `.j2` and converts `_`→`-`. A new `agents/compounder.md.j2` needs **no** `cli.py` change to be emitted.
- Run a single test with: `cd /Users/Daniel_Sallai/dev/ade-toolkit && python -m pytest tests/test_cli.py::<name> -v`. Run all with `python -m pytest`.

---

### Task 1: Seed the two compound artifacts (`docs/learnings/`, `docs/review-calibration.md`)

**Files:**
- Create: `src/ade/templates/bootstrap/learnings-README.md.j2`
- Create: `src/ade/templates/bootstrap/review-calibration.md.j2`
- Modify: `src/ade/cli.py` — `bootstrap_targets` list (`cli.py:259-266`) and doctor `bootstrap_paths` list (`cli.py:354-358`)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `_render_and_write_if_missing(env, template_name, dest, context) -> bool` (`cli.py:50`); the `init` / `doctor` Typer commands; the `python_project` fixture and `runner = CliRunner()` already in `tests/test_cli.py`.
- Produces: rendered `docs/learnings/README.md` and `docs/review-calibration.md` in any `ade init`-ed project; two new doctor WARN checks.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py` (place near the other seed tests, e.g. after `test_init_ade_routing_seed_if_missing_preserves_edits`):

```python
def test_init_seeds_learnings_dir(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    readme = python_project / "docs" / "learnings" / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "Why this matters" in content
    assert "Learning" in content
    # boundary vs ADR is spelled out so future agents pick the right artifact
    assert "ADR" in content


def test_init_learnings_seed_if_missing_preserves_edits(python_project: Path) -> None:
    readme = python_project / "docs" / "learnings" / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text("# my edited learnings index\n")
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert "my edited learnings index" in readme.read_text()


def test_init_seeds_review_calibration(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    corpus = python_project / "docs" / "review-calibration.md"
    assert corpus.exists()
    content = corpus.read_text()
    assert "finding-class" in content.lower()
    assert "Frequency" in content
    assert "Severity" in content


def test_init_review_calibration_seed_if_missing_preserves_edits(python_project: Path) -> None:
    corpus = python_project / "docs" / "review-calibration.md"
    corpus.parent.mkdir(parents=True, exist_ok=True)
    corpus.write_text("# my edited corpus\n")
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert "my edited corpus" in corpus.read_text()


def test_doctor_checks_compound_artifacts(python_project: Path) -> None:
    """Doctor passes but WARNs when the seeded compound artifacts are removed."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    (python_project / "docs" / "review-calibration.md").unlink()

    with patch("ade.cli._check_command", return_value=True):
        result = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    assert "WARN" in result.output
    assert "review-calibration" in result.output
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_cli.py::test_init_seeds_learnings_dir tests/test_cli.py::test_init_seeds_review_calibration tests/test_cli.py::test_doctor_checks_compound_artifacts -v`
Expected: FAIL — files not created (`assert False`), and doctor output lacks `review-calibration`.

- [ ] **Step 3: Create the learnings README template**

Create `src/ade/templates/bootstrap/learnings-README.md.j2`:

```markdown
# Learnings

This directory holds durable, per-task **Learnings** produced by the Codify sub-step of
ADE's Phase 9 (Retrospective). A Learning captures something the task *discovered* — a
non-obvious mechanism, a failed approach worth remembering, or a sharp gotcha — and **why it
matters**, so the next task's Research phase (Phase 1) reads it back and is cheaper.

A Learning is distinct from:

- an **ADR** (`docs/adr/`) — a decision you committed to. Rule of thumb: *if you chose it,
  it's an ADR; if you found it out, it's a Learning.*
- a **spec** (`docs/specs/`) — the WHAT/plan for a task, written before implementation.

## Naming convention

`{YYYY-MM-DD}_{slug}.md` — date-prefixed for chronological ordering; the slug is a 2–4 word
kebab-case summary. One file per task, written **only when the task yielded a transferable
insight** — routine tasks produce none, which keeps this directory high-signal.

## Template

```
# <one-line problem statement>

## Context
2-3 sentences: what the task was, what you were trying to do.

## What we tried
- Approach X — expected Y, found Z.

## What we learned
The concrete finding. Specifics — names, paths, numbers.

## Why this matters
The underlying mechanism — the part that transfers to the next task. A principle, not an
anecdote.

## Gotchas
Sharp edges someone applying this should know.

## Related
- Spec / ADRs / glossary terms touched.
```
```

- [ ] **Step 4: Create the review-calibration corpus template**

Create `src/ade/templates/bootstrap/review-calibration.md.j2`:

```markdown
# Review calibration corpus

A single, accreting list of the review **finding-classes** that recur in *this* project.
Phase 6 review agents read this file **fresh at the start of every review** and prioritize
the highest-frequency classes — so the issues this codebase keeps producing get caught
proactively. The corpus *is* the tuning; review prompts are never rewritten.

Written by the Codify sub-step of Phase 9 (via the `compounder` subagent): each task folds
its review findings in. **Frequency orders this list (most-recurring first); it never
promotes a class's severity.** Starts empty — an empty corpus is simply a no-op.

## Finding-classes

<!-- Each finding-class, most-frequent first:

### <class name>
- Severity: blocker | fix-before-merge | nice-to-have   (from the finding's own badness)
- Frequency: <N> tasks
- Signal: <greppable description of what to look for>
- Example: <task slug / file#anchor / short quote>

-->

_(empty — the compound loop fills this in as tasks complete.)_
```

- [ ] **Step 5: Wire seeding into `cli.py` `init`**

In `src/ade/cli.py`, extend the `bootstrap_targets` list (`cli.py:259-266`) with two entries:

```python
    bootstrap_targets = [
        ("bootstrap/CONTEXT.md.j2", project_dir / "CONTEXT.md"),
        (
            "bootstrap/adr-0001-record-architecture-decisions.md.j2",
            project_dir / "docs" / "adr" / "0001-record-architecture-decisions.md",
        ),
        ("bootstrap/specs-README.md.j2", project_dir / "docs" / "specs" / "README.md"),
        ("bootstrap/learnings-README.md.j2", project_dir / "docs" / "learnings" / "README.md"),
        ("bootstrap/review-calibration.md.j2", project_dir / "docs" / "review-calibration.md"),
    ]
```

(The existing loop at `cli.py:267-273` already renders seed-if-missing + prints the created/kept line for each entry — no other `init` change needed.)

- [ ] **Step 6: Wire doctor checks into `cli.py` `doctor`**

In `src/ade/cli.py`, extend the `bootstrap_paths` list (`cli.py:354-358`) with two entries:

```python
    bootstrap_paths = [
        ("CONTEXT.md", "Domain glossary (CONTEXT.md)"),
        ("docs/adr", "ADR directory (docs/adr/)"),
        ("docs/specs", "Specs directory (docs/specs/)"),
        ("docs/learnings", "Learnings directory (docs/learnings/)"),
        ("docs/review-calibration.md", "Review calibration corpus (docs/review-calibration.md)"),
    ]
```

(The existing loop at `cli.py:359-365` already emits WARN + increments `warnings` for each missing path — no other `doctor` change needed.)

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python -m pytest tests/test_cli.py::test_init_seeds_learnings_dir tests/test_cli.py::test_init_learnings_seed_if_missing_preserves_edits tests/test_cli.py::test_init_seeds_review_calibration tests/test_cli.py::test_init_review_calibration_seed_if_missing_preserves_edits tests/test_cli.py::test_doctor_checks_compound_artifacts -v`
Expected: PASS (5 passed).

- [ ] **Step 8: Run the full suite + lint**

Run: `python -m pytest && ruff check src/ tests/ && ruff format --check src/ tests/`
Expected: all green (existing `test_no_stale_stack_references` still passes — new files are under `docs/`).

- [ ] **Step 9: Commit**

```bash
git add src/ade/templates/bootstrap/learnings-README.md.j2 \
        src/ade/templates/bootstrap/review-calibration.md.j2 \
        src/ade/cli.py tests/test_cli.py
git commit -m "feat(g3): seed docs/learnings/ and review-calibration corpus at init

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: The `compounder` subagent

**Files:**
- Create: `src/ade/templates/agents/compounder.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: the `_render_template_dir(env, "agents/", ...)` auto-render (`cli.py:206`) — emits `.claude/agents/compounder.md`.
- Produces: a read-only sonnet subagent the Phase-9 Codify step (Task 3) dispatches; its contract is two outputs — a corpus-merge instruction block (always) and a Learning body or the literal `NO LEARNING — <reason>` (conditional).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py` (near the other `test_init_generates_*_agent` tests):

```python
def test_init_generates_compounder_agent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agent_path = python_project / ".claude" / "agents" / "compounder.md"
    assert agent_path.exists()
    content = agent_path.read_text()
    assert "model: sonnet" in content
    # read-only: no Write/Edit/Bash in the tools line
    assert "tools: [Read, Grep, Glob]" in content
    # contract terms
    assert "calibration" in content.lower()
    assert "Learning" in content
    assert "why it matters" in content.lower()
    assert "NO LEARNING" in content
    # never promotes severity by frequency
    assert "never" in content.lower() and "frequency" in content.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_init_generates_compounder_agent -v`
Expected: FAIL — `.claude/agents/compounder.md` does not exist.

- [ ] **Step 3: Create the compounder agent template**

Create `src/ade/templates/agents/compounder.md.j2`:

```markdown
---
model: sonnet
tools: [Read, Grep, Glob]
---
You are the compounder for ADE's Codify sub-step (the closing sub-step of Phase 9 —
Retrospective). You run in a fresh context and turn one completed task's review findings and
discoveries into durable, reloadable knowledge. Read-only: you never edit files — you return
content and instructions, and the orchestrator owns the write path.

You receive these file paths:
- `.ade/tasks/<task-id>/review.md` — the persisted Phase 6 Review Output (the findings).
- `.ade/tasks/<task-id>/retro.json` — per-task metrics (finding counts, iterations).
- the finalized spec and the task diff.
- `docs/review-calibration.md` — the current calibration corpus (may be empty).
- optionally, a temp file of prior-PR bot comments the orchestrator gathered.

Produce TWO outputs.

## 1. Calibration corpus merge (ALWAYS)

For each finding in `review.md` (and any prior-PR bot comments provided), update the corpus:
- Match the finding to an existing finding-class by its `Signal`. On a match, increment that
  class's `Frequency` by one and append a one-line example (task slug / file#anchor).
- If nothing matches, add a new finding-class: a short class name; a `Severity` assigned
  from the finding's own badness (`blocker` | `fix-before-merge` | `nice-to-have`) — NOT from
  how often it recurs; a `Frequency` of 1; a greppable `Signal`; and one example.
- NEVER change an existing class's `Severity` based on its `Frequency`. Frequency orders the
  corpus (most-recurring first); it never promotes severity.
- If `review.md` has zero findings, the merge is a no-op.

Output the merge as explicit instructions the orchestrator can apply: which classes to
increment, which to add, and the resulting most-frequent-first ordering.

## 2. Learning (CONDITIONAL)

Write a Learning ONLY when the task yielded a genuinely transferable insight — a non-obvious
mechanism, a failed approach worth remembering, or a sharp gotcha. A Learning records a thing
you DISCOVERED, not a decision you committed to (that is an ADR). If nothing rises above
routine, output exactly `NO LEARNING — <one-line reason>` and write nothing else for this
section. Quality over volume: a noisy learnings sink degrades the next task's research.

When you do write one, return this structure (the orchestrator saves it to
`docs/learnings/{YYYY-MM-DD}_{slug}.md`):

```
# <one-line problem statement>

## Context
2-3 sentences: what the task was, what you were trying to do.

## What we tried
- Approach X — expected Y, found Z.

## What we learned
The concrete finding. Specifics — names, paths, numbers.

## Why this matters
The underlying mechanism — the part that transfers to the next task. A principle, not an
anecdote.

## Gotchas
Sharp edges someone applying this should know.

## Related
- Spec: docs/specs/<...>
- ADRs: docs/adr/<...>
- Glossary terms: <CONTEXT.md terms touched>
```
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_cli.py::test_init_generates_compounder_agent -v`
Expected: PASS.

- [ ] **Step 5: Run the stale-reference guard + full suite**

Run: `python -m pytest tests/test_cli.py::test_no_stale_stack_references tests/test_cli.py -q && ruff check src/ tests/`
Expected: all green (the agent text contains none of the forbidden tokens).

- [ ] **Step 6: Commit**

```bash
git add src/ade/templates/agents/compounder.md.j2 tests/test_cli.py
git commit -m "feat(g3): add read-only compounder subagent for the Codify step

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Phase 9 — the Codify sub-step

**Files:**
- Modify: `src/ade/templates/skills/phases/09-retro.md.j2` (append the Codify section)
- Modify: `src/ade/templates/skills/ade-ship.md.j2` (`ade-ship.md.j2:19-32` Phase 9 block)
- Modify: `src/ade/templates/skills/ade-full.md.j2` (`ade-full.md.j2:338` Phase 9 heading)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: the `compounder` agent from Task 2; `docs/review-calibration.md` + `docs/learnings/` from Task 1; `.ade/tasks/<task-id>/review.md` (persisted by Task 4 — referenced by name here, produced there).
- Produces: the Phase-9 Codify procedure read by the orchestrator at runtime.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
def test_retro_skill_describes_codify_step(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    retro = (
        python_project / ".claude" / "skills" / "ade" / "phases" / "09-retro.md"
    ).read_text()
    assert "Codify" in retro
    assert "docs/learnings/" in retro
    assert "docs/review-calibration.md" in retro
    assert "compounder" in retro
    # conditional learning + trivial exclusion are explicit
    assert "NO LEARNING" in retro or "no Learning" in retro
    assert "trivial" in retro.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_retro_skill_describes_codify_step -v`
Expected: FAIL — `09-retro.md` has no "Codify" content.

- [ ] **Step 3: Append the Codify sub-step to `09-retro.md.j2`**

Append to the end of `src/ade/templates/skills/phases/09-retro.md.j2` (after the existing "Task Directory Structure (Final)" section):

```markdown
## Codify — the closing sub-step (skipped for `trivial`)

The retrospective above looks *back* (per-task metrics). **Codify** turns that reflection
*forward* into durable, reloadable knowledge so the next task is cheaper. It is **skipped
entirely for the `trivial` tier** (consistent with routing); standard and architecture tiers
always run it.

1. **Gather inputs.** Confirm `.ade/tasks/<task-id>/review.md` exists (Phase 6 persists it).
   Optionally fetch bot comments from a recently-merged *prior* PR
   (`gh pr view <n> --comments`) into a temp file — best-effort; skip silently if `gh`, a
   prior PR, or bots are absent. (Bot reviews for *this* task's PR arrive asynchronously,
   after Codify runs, so they fold into a *later* task's Codify, not this one.)

2. **Dispatch the `compounder` subagent** (sonnet, read-only) via the Agent tool. Pass the
   file paths: `review.md`, `retro.json`, the spec, the diff, `docs/review-calibration.md`,
   and the optional prior-PR comments file. It returns (a) corpus-merge instructions and
   (b) a Learning body or the literal `NO LEARNING — <reason>`.

3. **Apply the corpus merge (always).** Update `docs/review-calibration.md` per the
   compounder's instructions: increment matched finding-classes' `Frequency` and append
   examples; add new classes (severity from the finding's badness, frequency 1); re-order
   most-frequent first. Never promote severity by frequency. Zero findings -> no-op.

4. **Write the Learning (only if returned).** If the compounder returned a Learning body,
   save it to `docs/learnings/{YYYY-MM-DD}_{slug}.md` (today's date; slug = the task slug).
   If it returned `NO LEARNING`, write nothing and note "routine — no Learning" in the retro.

5. **Surface the review-findings signal.** Report the per-task finding count and any class
   that has reached multi-task frequency — e.g. "6 findings; class 'silent-fallback' now seen
   in 3 tasks." This is a health signal, not a gate.

**Exit criteria:** corpus merged; Learning written or explicitly skipped; signal surfaced.
```

- [ ] **Step 4: Update the `ade-ship.md.j2` Phase 9 block**

In `src/ade/templates/skills/ade-ship.md.j2`, replace the Phase 9 block (`ade-ship.md.j2:19-32`) so it adds Codify after the retro record. Change:

```markdown
## Phase 9 — RETROSPECTIVE
Record to `.ade/tasks/<task-id>/retro.json`:
- Cycle time per phase
- Iteration counts (design check, review, QA fix)
- Circuit breaker triggers
- What worked, what didn't
- Follow-up items

Clean up worktree: `git worktree remove .ade/worktrees/<task-id>`

**Exit criteria:** Retro saved. Worktree cleaned up.
```

to:

```markdown
## Phase 9 — RETROSPECTIVE
Record to `.ade/tasks/<task-id>/retro.json`:
- Cycle time per phase
- Iteration counts (design check, review, QA fix)
- Circuit breaker triggers
- What worked, what didn't
- Follow-up items

### Codify (skipped for `trivial`)
Dispatch the `compounder` subagent (read-only) with `.ade/tasks/<task-id>/review.md`,
`retro.json`, the spec, the diff, and `docs/review-calibration.md`. Then:
- **Always** merge its findings into `docs/review-calibration.md` (increment/append
  finding-classes; frequency orders the corpus, never promotes severity).
- **If** it returns a Learning, save it to `docs/learnings/{YYYY-MM-DD}_{slug}.md`; otherwise
  note "routine — no Learning".
- Surface the review-findings signal (finding count + recurring classes).
See `phases/09-retro.md` for the full procedure.

Clean up worktree: `git worktree remove .ade/worktrees/<task-id>`

**Exit criteria:** Retro saved. Corpus merged; Learning written or skipped. Worktree cleaned up.
```

- [ ] **Step 5: Annotate the `ade-full.md.j2` Phase 9 heading**

In `src/ade/templates/skills/ade-full.md.j2`, find the Phase 9 heading (`ade-full.md.j2:338`):

```markdown
## Phase 9 — RETROSPECTIVE
```

Replace with:

```markdown
## Phase 9 — RETROSPECTIVE *(Codify sub-step skipped for `trivial`)*
```

Then, immediately after the existing retro `retro.json` block in that section (after `ade-full.md.j2:344`'s saved-fields list, before the status-update line at `ade-full.md.j2:353`), insert:

```markdown

**Codify (standard/architecture only):** dispatch the `compounder` subagent (read-only) with
`.ade/tasks/<task-id>/review.md`, `retro.json`, the spec, the diff, and
`docs/review-calibration.md`. Always merge findings into `docs/review-calibration.md`
(frequency orders, never promotes severity); write `docs/learnings/{date}_{slug}.md` only
when a transferable Learning is returned. Surface the review-findings signal. Full procedure
in `phases/09-retro.md`.
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python -m pytest tests/test_cli.py::test_retro_skill_describes_codify_step -v`
Expected: PASS.

- [ ] **Step 7: Run the stale-reference guard + full suite + lint**

Run: `python -m pytest && ruff check src/ tests/`
Expected: all green (the inserted prose contains no forbidden tokens — note the literal "no-op" and "/learnings/" are fine; do not introduce "/10").

- [ ] **Step 8: Commit**

```bash
git add src/ade/templates/skills/phases/09-retro.md.j2 \
        src/ade/templates/skills/ade-ship.md.j2 \
        src/ade/templates/skills/ade-full.md.j2 tests/test_cli.py
git commit -m "feat(g3): add Codify sub-step to Phase 9 (retro -> compound)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Phase 6 — read the corpus + persist the review output

**Files:**
- Modify: `src/ade/templates/skills/phases/06-review.md.j2` (insert a corpus-read section after "Review Scope" `06-review.md.j2:11-16`; append a persist-output section after "Review Output Format" `06-review.md.j2:160-191`)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `docs/review-calibration.md` from Task 1.
- Produces: `.ade/tasks/<task-id>/review.md` (the persisted Review Output) — the input Task 3's Codify step reads.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py`:

```python
def test_review_reads_calibration(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    review = (
        python_project / ".claude" / "skills" / "ade" / "phases" / "06-review.md"
    ).read_text()
    assert "docs/review-calibration.md" in review
    assert "fresh" in review.lower()


def test_review_persists_output(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    review = (
        python_project / ".claude" / "skills" / "ade" / "phases" / "06-review.md"
    ).read_text()
    assert ".ade/tasks/<task-id>/review.md" in review
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_cli.py::test_review_reads_calibration tests/test_cli.py::test_review_persists_output -v`
Expected: FAIL — neither string present in `06-review.md`.

- [ ] **Step 3: Insert the calibration-read section**

In `src/ade/templates/skills/phases/06-review.md.j2`, immediately after the "## Review Scope" block (after `06-review.md.j2:16`, the line ending `...or are "just tests."`) and before "## Review Mechanism", insert:

```markdown
## Calibration corpus — read first

Before reviewing, read `docs/review-calibration.md` **fresh**. It lists the finding-classes
that recur in this project, most-frequent first. Prioritize checking the diff against the top
classes — these are the issues this codebase keeps producing. Every tier reads the corpus
(including `trivial`); an empty corpus simply means there is nothing to prioritize yet.

```

- [ ] **Step 4: Append the persist-output section**

In `src/ade/templates/skills/phases/06-review.md.j2`, after the "## Review Output Format" fenced block (after `06-review.md.j2:191`) and before "## Iteration Limit", insert:

```markdown
## Persist the Review Output

Write the Review Output (above) to `.ade/tasks/<task-id>/review.md`. The Codify sub-step of
Phase 9 reads this file to compound the findings into `docs/review-calibration.md`. Persist it
even when the verdict is clean (an empty findings set is a valid, useful signal).

```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_cli.py::test_review_reads_calibration tests/test_cli.py::test_review_persists_output -v`
Expected: PASS.

- [ ] **Step 6: Confirm the existing review-skill test still passes**

Run: `python -m pytest tests/test_cli.py::test_review_skill_has_acceptance_coverage_gate tests/test_cli.py::test_no_stale_stack_references -v`
Expected: PASS (insertions don't touch the acceptance-gate wording and add no forbidden tokens).

- [ ] **Step 7: Commit**

```bash
git add src/ade/templates/skills/phases/06-review.md.j2 tests/test_cli.py
git commit -m "feat(g3): Phase 6 reads calibration corpus and persists review.md

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Phase 1 — read learnings back

**Files:**
- Modify: `src/ade/templates/skills/phases/01-research.md.j2` (the "Project:" inputs line `01-research.md.j2:10` and the R2.1 scout-dispatch context line `01-research.md.j2:39`)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `docs/learnings/` from Task 1.
- Produces: the instruction that R2.1 scouts grep `docs/learnings/` — the read-back that closes the compound loop.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
def test_research_reads_learnings(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    research = (
        python_project / ".claude" / "skills" / "ade" / "phases" / "01-research.md"
    ).read_text()
    assert "docs/learnings/" in research
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_research_reads_learnings -v`
Expected: FAIL — `docs/learnings/` not referenced in `01-research.md`.

- [ ] **Step 3: Add learnings to the project inputs line**

In `src/ade/templates/skills/phases/01-research.md.j2`, change line 10:

```markdown
- Project: `CONTEXT.md`, `docs/adr/*`, codebase
```

to:

```markdown
- Project: `CONTEXT.md`, `docs/adr/*`, `docs/learnings/*`, codebase
```

- [ ] **Step 4: Extend the R2.1 scout-dispatch context**

In `src/ade/templates/skills/phases/01-research.md.j2`, change the scout-context line (`01-research.md.j2:39`):

```markdown
Pass the task description (from intent.md) and any relevant CONTEXT.md vocabulary as context. Each scout writes its output to `.ade/tasks/<task-id>/research/scout-<scope>-cycle<N>.md`.
```

to:

```markdown
Pass the task description (from intent.md) and any relevant CONTEXT.md vocabulary as context. Also tell the scouts to grep `docs/learnings/` for prior Learnings touching this task's area and to cite any that apply — past discoveries make this task cheaper. Each scout writes its output to `.ade/tasks/<task-id>/research/scout-<scope>-cycle<N>.md`.
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_cli.py::test_research_reads_learnings -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite + lint**

Run: `python -m pytest && ruff check src/ tests/`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/ade/templates/skills/phases/01-research.md.j2 tests/test_cli.py
git commit -m "feat(g3): Phase 1 scouts read docs/learnings/ back (closes the loop)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Documentation — CLAUDE.md section + architecture doc

**Files:**
- Modify: `src/ade/templates/claude_md_section.md.j2` (the Phase 9 line `claude_md_section.md.j2:98-99`)
- Modify: `docs/ade-architecture-design.md` (new "## Compound loop (G3)" section)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: nothing new — documents the mechanism built in Tasks 1–5.
- Produces: the generated `CLAUDE.md` ADE section mentioning the compound loop; the repo architecture doc's G3 section.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
def test_claude_md_section_describes_compound_loop(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    claude_md = (python_project / "CLAUDE.md").read_text()
    assert "docs/learnings/" in claude_md
    assert "review-calibration.md" in claude_md
    assert "Codify" in claude_md
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_claude_md_section_describes_compound_loop -v`
Expected: FAIL — the generated CLAUDE.md section has no compound-loop content.

- [ ] **Step 3: Update the `claude_md_section.md.j2` Phase 9 line**

In `src/ade/templates/claude_md_section.md.j2`, change (`claude_md_section.md.j2:98-99`):

```markdown
**Phase 9 — RETROSPECTIVE**: Record metrics and learnings.
Save to `.ade/tasks/<task-id>/retro.json`. Clean up worktree.
```

to:

```markdown
**Phase 9 — RETROSPECTIVE**: Record metrics to `.ade/tasks/<task-id>/retro.json`, then
**Codify** (standard/architecture tiers): a read-only `compounder` subagent folds review
findings into `docs/review-calibration.md` (frequency orders the corpus, never promotes
severity) and writes a `docs/learnings/{date}_{slug}.md` when the task yielded a transferable
insight. Phase 1 reads `docs/learnings/` back and Phase 6 reads `docs/review-calibration.md`
fresh — the compound loop. Clean up worktree.
```

- [ ] **Step 4: Add the architecture-doc section**

Append to `docs/ade-architecture-design.md` a new section (place it after the blast-radius routing / G4 section so the gap order reads G4 → G3-as-shipped; if unsure, append at the end of the body before any appendix):

```markdown
## Compound loop (G3)

ADE's Phase 9 was historically an ephemeral, per-task `retro.json` that dead-ended. G3
promotes it with a **Codify** sub-step that deposits durable, reloadable knowledge so each
task makes the next cheaper. Two version-controlled artifacts live in the target project,
joining `CONTEXT.md` (terminology) and ADRs (decisions):

- **`docs/learnings/{date}_{slug}.md`** — a per-task **Learning**: a mechanism-focused record
  of something the task *discovered* (incl. failed approaches) and *why it matters*. Written
  only when there is a genuinely transferable insight (routine tasks produce none). A Learning
  is a *discovery*; an ADR is a *decision* — *if you chose it, it's an ADR; if you found it
  out, it's a Learning.*
- **`docs/review-calibration.md`** — a single accreting **calibration corpus** of recurring
  review **finding-classes** (severity from badness, frequency, greppable signal, example),
  ordered most-frequent-first.

**Data flow (the loop):**
1. **Phase 9 / Codify** (standard + architecture; skipped for `trivial`): a read-only
   `compounder` subagent (sonnet) reads the persisted Phase-6 `review.md`, `retro.json`, the
   spec, and the diff, then returns a corpus merge (always applied) and a Learning (written
   only if transferable). The orchestrator owns the writes.
2. **Phase 1 / Research** R2.1 scouts grep `docs/learnings/` for prior discoveries in the
   task's area.
3. **Phase 6 / Review** agents read `docs/review-calibration.md` fresh every run and
   prioritize the project's top recurring finding-classes.

The **review-findings signal** (per-task finding count, plus best-effort bot comments on
*prior* merged PRs) is surfaced at Retro as a health number whose only durable effect is
incrementing finding-class frequency. It is **not** a gate — the loop is passive,
prose-driven, and non-gating (see ADR 0002), deliberately diverging from LeRisque's gating
SLI and from G4's enforcement hook (G3 guards no security boundary; it accrues knowledge).

### Subagent

- **`compounder`** (sonnet, read-only `[Read, Grep, Glob]`) — distills a task's findings and
  discoveries into the calibration-corpus merge and a conditional Learning during Codify.
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_cli.py::test_claude_md_section_describes_compound_loop -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite + lint (final gate)**

Run: `python -m pytest && ruff check src/ tests/ && ruff format --check src/ tests/`
Expected: all green, including `test_no_stale_stack_references` (the generated CLAUDE.md section adds no forbidden tokens — verify it contains no `/10`, `localhost`, etc.).

- [ ] **Step 7: Commit**

```bash
git add src/ade/templates/claude_md_section.md.j2 docs/ade-architecture-design.md tests/test_cli.py
git commit -m "docs(g3): document the compound loop in CLAUDE.md section + architecture doc

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage** (against `docs/superpowers/specs/2026-06-20-g3-compound-loop-design.md`):
- §3.1 learnings sink + README → Task 1 (template) + Task 6 (boundary doc). ✓
- §3.2 calibration corpus + merge rule (freq orders, no promotion) → Task 1 (template) + Task 2 (compounder merge contract). ✓
- §3.3 review-findings signal + prior-PR best-effort → Task 3 (Codify steps 1 & 5). ✓
- §3.4 compounder subagent (sonnet, read-only, two outputs, conditional Learning) → Task 2. ✓
- §3.5 ripple: 09-retro → Task 3; 06-review (read corpus + persist review.md) → Task 4; 01-research → Task 5; ade-ship + ade-full → Task 3; claude_md_section → Task 6. ✓
- §3.6 cli init seed + doctor checks → Task 1. ✓ (`detect.py` no change — correct, none planned.)
- §3.7 architecture doc + CONTEXT/ADR → Task 6 (architecture doc); CONTEXT.md + ADR 0002 already written during grill (committed `7363577`). ✓
- §5 tests: all listed tests mapped (seeds, calibration, compounder, codify, research, review-reads, review-persists, doctor) → Tasks 1–6, plus the claude_md_section test. ✓
- §6 edge cases (empty corpus no-op, conditional Learning, trivial skip, no-gh, parallel, seed-if-missing) → covered by seed-if-missing tests (Task 1) + prose in Tasks 3/4 + the empty-corpus default in the calibration template. ✓
- Trivial-tier exclusion → asserted in Task 3 test; Phase 6 corpus-read explicitly "every tier" in Task 4. ✓

**2. Placeholder scan:** No TBD/TODO; every code/template/prose step shows full content; commands have expected output. ✓

**3. Type/name consistency:** `compounder` (agent filename, dispatch references, doctor n/a), `docs/learnings/`, `docs/review-calibration.md`, `.ade/tasks/<task-id>/review.md`, `NO LEARNING`, "frequency orders … never promotes severity" — used identically across Tasks 2, 3, 4, 6. The compounder's output contract (Task 2) matches what Codify consumes (Task 3). ✓

No gaps found.
```
