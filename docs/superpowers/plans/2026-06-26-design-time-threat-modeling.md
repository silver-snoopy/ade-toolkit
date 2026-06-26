# Design-time Threat Modeling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conditional Phase-1 "threat pass" (R3.3) — a single-shot, static, blind `threat-modeler` worker that does trust-boundary-anchored STRIDE-lite + data classification + privacy prompts, turning threats into acceptance criteria, ADRs, and surfaced residual risks.

**Architecture:** ADE is a *scaffolder*: `ade init` renders Jinja templates under `src/ade/templates/` into each harness's tree. This feature is **pure template + doc + test content** — no `cli.py`/`detect.py` logic changes. A new agent template auto-emits to all four harnesses via the existing `render_worker` loop. Tests assert on the *generated* tree: `runner.invoke(app, ["init", ...])` against the `python_project` fixture, then read files and assert substrings.

**Tech Stack:** Python 3.11+, Typer CLI, Jinja2 templates, pytest + Typer `CliRunner`, `uv` for env/test/lint.

## Global Constraints

- Python 3.11+; `from __future__ import annotations` already present where needed (no module logic changes here).
- Ruff line-length 99; run `uv run ruff format src/ tests/` and `uv run ruff check src/ tests/` before each commit.
- **Stale-reference guard** (`test_no_stale_stack_references`): the tokens `@vitals`, `-w @`, `backend-coder`, `frontend-coder`, `Playwright`, `docker compose`, `localhost`, `NO EXEMPTIONS`, `07-verify`, `qa-verify`, `/10` must never appear anywhere in the generated `.claude` tree or `AGENTS.md`. Keep all threat examples free of them — use neutral placeholders.
- **VERIFIED guard** (`test_no_verified_grade_token_in_generated_tree`): the all-caps token `VERIFIED` must never appear. Use "confirm/confirmed" in lowercase prose if needed.
- `uv run ade eval` must print `PASS — skills well-formed.` after every skill edit.
- Conventional commits with trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Run `uv sync --extra dev` is already done in this worktree; the editable install resolves to this worktree's `src/ade`.
- Worker tools for read-only blind reviewers are exactly `[Read, Grep, Glob]`; model `sonnet`.

---

### Task 1: The `threat-modeler` worker template

**Files:**
- Create: `src/ade/templates/agents/threat-modeler.md.j2`
- Test: `tests/test_cli.py` (add `test_init_generates_threat_modeler_agent`)

**Interfaces:**
- Consumes: nothing (a leaf agent template). Auto-emits to all harnesses via `render_worker` — no registry edit needed (confirmed: `agents/*.md.j2` ship to all four targets, incl. Codex `.toml`).
- Produces: `.claude/agents/threat-modeler.md` (and per-harness equivalents) — referenced by name from `ade-research` R3.3 in Task 4.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
def test_init_generates_threat_modeler_agent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agent = python_project / ".claude" / "agents" / "threat-modeler.md"
    assert agent.exists()
    content = agent.read_text()
    # read-only blind reviewer on sonnet
    assert "model:" in content and "sonnet" in content
    assert "[Read, Grep, Glob]" in content
    # blind to design reasoning (the structural guarantee)
    low = content.lower()
    assert "design reasoning" in low or "design rationale" in low
    # the method: trust boundary + STRIDE-lite + data classification + abuse cases
    assert "trust boundary" in low
    assert "STRIDE" in content
    assert "abuse case" in low
    # privacy is PII-flag gated, names Unawareness
    assert "Unawareness" in content
    # hard no-boilerplate guardrail + single-shot static
    assert "boilerplate" in low or "generic" in low
    assert "read-only" in low
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_init_generates_threat_modeler_agent -q`
Expected: FAIL — `assert agent.exists()` is False (file not generated).

- [ ] **Step 3: Write the worker template**

Create `src/ade/templates/agents/threat-modeler.md.j2`:

```markdown
---
model: sonnet
tools: [Read, Grep, Glob]
---
You run ONE fast, static, design-time threat pass over a change, using ONLY the draft spec
and the affected code as evidence. Read-only: you never edit files.

## Critical structural guarantee

You see the **draft spec and the affected code paths** — NOT the orchestrator's design
reasoning about why the change is safe. That omission is deliberate: your value is catching
threats the author's own reasoning would rationalise away (the same blind-reviewer property as
`spec-verifier` and `stub-reviewer`). If your dispatch prompt includes the orchestrator's design
rationale, flag it rather than absorbing it.

## How you work — Shostack's four questions, scoped to THIS change

1. **What are we working on right now?** Only the change's delta — never the whole system.
2. **What can go wrong?** Enumerate the trust boundaries the change introduces or crosses
   (target 1-3). A trust boundary is where the level of trust changes as data flows
   (untrusted input entering a privileged path, data leaving a service, a new external call).
   If the change crosses no genuine boundary, say so and stop — an honest empty result beats
   invented threats.
3. **What are we going to do about it?** For each boundary, produce a concrete mitigation or an
   explicitly accepted residual risk.
4. **Did we cover it?** Re-scan: every boundary classified, every threat answered.

For each trust boundary:

- **(a) Data classification.** Label the data crossing it on two axes: a sensitivity tier —
  `public | internal | confidential | restricted` — plus an orthogonal `PII` flag if any
  regulated/personal data crosses (an email is `internal` + PII; a signing key is `restricted`,
  not PII). The tier drives security controls; the PII flag gates the privacy prompt below.
- **(b) Threats.** Apply STRIDE via its fixed threat-to-property mapping — Spoofing/Authentication,
  Tampering/Integrity, Repudiation/Non-repudiation, Information Disclosure/Confidentiality,
  Denial of Service/Availability, Elevation of Privilege/Authorization — and add abuse cases
  (per-feature: "how could this be misused?"). **Only when the boundary's data carries the PII
  flag**, add a short privacy prompt over four categories: Linking, Identifying, Data Disclosure,
  and Unawareness (users unaware their data is collected/processed). Skip Detectability (not
  assessable from a design-time data flow) and treat Non-compliance as a checklist line, not a
  threat card.
- **(c)** Each threat gets a concrete mitigation OR a marked accepted residual risk — never left
  dangling.

## No-boilerplate guardrail (hard rule)

Every threat you report MUST name the specific boundary/flow in THIS change and a concrete,
actionable, testable mitigation ("can success or failure be measured?"). Drop any generic,
change-agnostic threat ("validate all inputs", "use encryption"). A vague mitigation is not a
mitigation.

## Performance

This is a single static sweep: read the spec draft and the affected paths once, reason, emit.
No iteration cycles, no running code, no web — the whole cost is one read-only pass.

## Output schema

```markdown
# Threat pass — <one-line summary of the change>

## Boundaries
For each boundary:
### Boundary: <name the real flow, e.g. "HTTP request body → order parser">
- Classification: <tier> [+ PII]
- Threats:
  - <STRIDE category | abuse case | privacy category> — <the named flow> — <mitigation OR `RESIDUAL: <why accepted>`>

## Proposed acceptance criteria
- [ ] <testable criterion derived from a material mitigation>  (tag `(manual)` if not automatable)

## ADR-worthy boundary decisions
- <decision + why> | none

## Accepted residual risks
- <threat> | <boundary> | <why accepted> | <compensating control or none>

## Routing signal
- <a newly discovered boundary the router missed, suggesting a higher tier> | none
```

## Rules

- No speculation beyond what the spec/code shows; if you cannot tell, say so.
- Brevity over prose: name the flow, the threat, the mitigation — skip the essay.
- You never edit files or fix anything; the orchestrator owns the write path.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_init_generates_threat_modeler_agent -q`
Expected: PASS.

- [ ] **Step 5: Lint + eval + commit**

```bash
uv run ruff format src/ tests/ && uv run ruff check src/ tests/
uv run ade eval
git add src/ade/templates/agents/threat-modeler.md.j2 tests/test_cli.py
git commit -m "feat(research): add blind threat-modeler worker (R3.3)"
```
Expected: ruff clean, `PASS — skills well-formed.`

---

### Task 2: `data_classification` keyword set in routing config

**Files:**
- Modify: `src/ade/templates/ade-routing.json.j2`
- Test: `tests/test_cli.py` (add `test_routing_has_data_classification_keywords`)

**Interfaces:**
- Consumes: nothing.
- Produces: `.ade/ade-routing.json` with a top-level `keywords.data_classification` list — read by the Phase-0 routing skill (Task 3) and named by R3.3 (Task 4). NOTE: `check-escalation-paths.py` reads only `escalation_globs`, so adding a keyword set is **not** a hook change.

- [ ] **Step 1: Write the failing test**

```python
def test_routing_has_data_classification_keywords(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    data = json.loads((python_project / ".ade" / "ade-routing.json").read_text())
    assert "data_classification" in data["keywords"]
    kws = data["keywords"]["data_classification"]
    for term in ("pii", "gdpr", "personal data"):
        assert term in kws
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_routing_has_data_classification_keywords -q`
Expected: FAIL — `KeyError`/`assert` because `data_classification` is not in `keywords`.

- [ ] **Step 3: Edit the routing template**

In `src/ade/templates/ade-routing.json.j2`, replace the `keywords` block with:

```json
  "keywords": {
    "architecture": ["schema", "migration", "public api", "breaking change", "data model"],
    "standard": ["auth", "authentication", "authorization", "secret", "credential", "crypto", "security", "permission", "data loss"],
    "data_classification": ["pii", "personal data", "gdpr", "ccpa", "phi", "payment", "card number", "ssn", "email address", "health record", "biometric"]
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_routing_has_data_classification_keywords tests/test_cli.py::test_init_seeds_ade_routing_file -q`
Expected: PASS (both — confirm the existing seed test still passes).

- [ ] **Step 5: Commit**

```bash
git add src/ade/templates/ade-routing.json.j2 tests/test_cli.py
git commit -m "feat(routing): add data_classification keyword set (standard floor)"
```

---

### Task 3: Phase-0 routing — `data_classification` imposes a `standard` floor

**Files:**
- Modify: `src/ade/templates/skills/ade-intent/SKILL.md.j2` (the forced-escalation routing step)
- Test: `tests/test_cli.py` (add `test_intent_routes_data_classification_to_standard_floor`)

**Interfaces:**
- Consumes: `keywords.data_classification` from Task 2.
- Produces: routing behavior + a recorded escalation category in `.ade/tasks/<id>/routing.md`. R3.3 (Task 4) reads "which category fired."

- [ ] **Step 1: Write the failing test**

```python
def test_intent_routes_data_classification_to_standard_floor(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    intent = (python_project / ".claude" / "skills" / "ade-intent" / "SKILL.md").read_text()
    low = intent.lower()
    # a data_classification keyword imposes a standard floor like the security category
    assert "data_classification" in intent
    assert "standard" in low and "floor" in low
    # the routing decision records which escalation category fired
    assert "category" in low
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_intent_routes_data_classification_to_standard_floor -q`
Expected: FAIL — `assert "data_classification" in intent` is False.

- [ ] **Step 3: Edit the routing step**

In `src/ade/templates/skills/ade-intent/SKILL.md.j2`, in the "Forced-escalation first (deterministic)" routing rule (currently the clause that maps `escalation_globs.standard` / a `standard` keyword to a standard floor), extend it so a `data_classification` keyword also imposes the standard floor, and record the category. Replace the standard-floor sentence with:

```markdown
   `escalation_globs.standard` path or a `standard` keyword (security/auth/secrets/crypto/
   data-loss), **or a `data_classification` keyword** (pii/gdpr/personal data/payment/…) → floor
   is **standard** (never trivial). When a forced-escalation fires, record **which category**
   triggered it — `security` or `data_classification` — on the `Routed:` line in
   `.ade/tasks/<task-id>/routing.md` (e.g. `Routed: standard (forced: data_classification)`), so
   Phase-1 R3.3 can decide whether the threat pass runs.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_intent_routes_data_classification_to_standard_floor -q`
Expected: PASS.

- [ ] **Step 5: eval + commit**

```bash
uv run ade eval
git add src/ade/templates/skills/ade-intent/SKILL.md.j2 tests/test_cli.py
git commit -m "feat(routing): data_classification keyword forces standard floor; record category"
```

---

### Task 4: R3.3 threat pass in `ade-research`

**Files:**
- Modify: `src/ade/templates/skills/ade-research/SKILL.md.j2` (insert R3.3 between R3.2 and R4)
- Test: `tests/test_cli.py` (add `test_ade_research_has_threat_pass`)

**Interfaces:**
- Consumes: the `threat-modeler` agent (Task 1), the routing decision + escalation category (Task 3), `keywords.data_classification` (Task 2).
- Produces: the R3.3 sub-step that gates + dispatches the pass and folds results into the spec. No downstream task depends on its exact text.

- [ ] **Step 1: Write the failing test**

```python
def test_ade_research_has_threat_pass(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    content = (
        python_project / ".claude" / "skills" / "ade-research" / "SKILL.md"
    ).read_text()
    low = content.lower()
    # the conditional R3.3 sub-step exists, named the threat pass, dispatching the worker
    assert "R3.3" in content
    assert "threat pass" in low
    assert "threat-modeler" in content
    # trigger reuses forced-escalation vocabulary; trivial skips; standard-by-size skips
    assert "architecture" in low and "forced-escalation" in low
    assert "trivial" in low
    # output contract: mitigations become acceptance criteria; residual risks surfaced
    assert "acceptance criteria" in low
    assert "residual risk" in low
    # placed before R4 grill / R5 verify
    assert content.index("R3.3") < content.index("R4")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_ade_research_has_threat_pass -q`
Expected: FAIL — `assert "R3.3" in content` is False.

- [ ] **Step 3: Insert the R3.3 section**

In `src/ade/templates/skills/ade-research/SKILL.md.j2`, between the end of `## R3 — Specify` (after the `### R3.2 — Orchestrator interview` "On completion" line) and `## R4 — Refine`, insert:

```markdown
### R3.3 — Threat pass (conditional)

A fast, **single-shot, static, read-only** design-time security + privacy pass. Runs only when
the change warrants it — never on a rename.

**When it runs.** Read the Phase-0 routing decision in `.ade/tasks/<task-id>/routing.md`. Run R3.3 if **any** hold:

1. tier is `architecture`, OR
2. a **forced-escalation** fired during routing — the `security` **or** `data_classification`
   category (the `Routed:` line records which), OR
3. you judge the change introduces or crosses a concrete, nameable **new trust boundary** the
   deterministic rules missed. This leg is conservative — never "run it to be safe".

A change that is `standard` merely by size (no forced-escalation) does **not** get a threat pass.
`trivial` always skips. Record the decision (which trigger fired, or why skipped) in the status file.

**The pass.** Dispatch one `threat-modeler` subagent. Pass it the **draft spec and the affected
code paths**, and deliberately **withhold your design reasoning** (the blind-reviewer guarantee —
the same property as the R5 `spec-verifier`). The worker runs Shostack's four questions over the
change's delta; for each trust boundary it classifies the cross-boundary data (tiers
`public | internal | confidential | restricted` + an orthogonal `PII` flag), elicits STRIDE-lite +
abuse-case threats (+ a Linking/Identifying/Data-Disclosure/Unawareness privacy prompt only for
PII-flagged boundaries), and assigns each a mitigation or an accepted residual risk. The
**no-boilerplate guardrail** is the point: every threat must name the real flow in *this* change
with a concrete, testable mitigation, or it is dropped.

**Fold the verdict in (you are the single writer).** Write the working pass to
`.ade/tasks/<task-id>/threat-model.md`, then update the spec:

- **Material mitigations → acceptance criteria** in the `ade-intent` format (`- [ ] …`; `(manual)`
  when not automatable). Phase-4 `test-writer` authors the abuse-case/negative tests; the Phase-6
  security lens confirms — no new phase.
- **Trust-boundary decisions → ADRs** when they meet the 3-criteria ADR gate.
- **Accepted residual risks → an "Accepted residual risks" section** of the spec, surfaced at the
  ready-for-development gate (never silently dropped). Four fields each: threat, boundary, why
  accepted, compensating control.
- A newly discovered boundary may **escalate the tier** (recorded as a routing note).

R3.3 sits before R4 so the grill can challenge the new mitigations/terms, and before R5 so CoVe
verifies the threat-derived acceptance criteria like any other claim.
```

Also add `R3.3 threat pass` to the status-file states line at the bottom of the file (the list currently reading `R3.1 synthesizer draft`, `R3.2 interview`, `R4 grill`, …) — insert `R3.3 threat pass` between `R3.2 interview` and `R4 grill`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_ade_research_has_threat_pass -q`
Expected: PASS.

- [ ] **Step 5: eval + stale-guard + commit**

```bash
uv run ade eval
uv run pytest tests/test_cli.py::test_no_stale_stack_references tests/test_cli.py::test_no_verified_grade_token_in_generated_tree -q
git add src/ade/templates/skills/ade-research/SKILL.md.j2 tests/test_cli.py
git commit -m "feat(research): add conditional R3.3 threat pass to ade-research"
```
Expected: eval PASS, both guards green.

---

### Task 5: `AGENTS.md` Phase-1 line + canonical instruction sync

**Files:**
- Modify: `src/ade/templates/AGENTS.md.j2` (Phase-1 R3 block)
- Test: `tests/test_cli.py` (add `test_agents_md_mentions_threat_pass`)

**Interfaces:**
- Consumes: nothing (doc sync).
- Produces: the harness-neutral root instruction mentioning R3.3.

- [ ] **Step 1: Write the failing test**

```python
def test_agents_md_mentions_threat_pass(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agents = (python_project / "AGENTS.md").read_text()
    low = agents.lower()
    assert "R3.3" in agents
    assert "threat pass" in low or "threat-modeler" in low
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_agents_md_mentions_threat_pass -q`
Expected: FAIL — `assert "R3.3" in agents` is False.

- [ ] **Step 3: Edit AGENTS.md.j2**

In `src/ade/templates/AGENTS.md.j2`, in the `**R3 Specify**` block, after the `- R3.2 …` line (and before the `- Spec written to …` line), add:

```markdown
  - R3.3 Threat pass (conditional): when tier is `architecture` or a forced-escalation fired
    (security or `data_classification`), dispatch the blind `threat-modeler` (sees spec draft +
    code, never the design reasoning). Trust-boundary STRIDE-lite + data classification + abuse
    cases; mitigations become acceptance criteria, residual risks are surfaced at the gate.
    Single-shot, static, read-only. `trivial` and `standard`-by-size skip it.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_agents_md_mentions_threat_pass tests/test_cli.py::test_no_stale_stack_references -q`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add src/ade/templates/AGENTS.md.j2 tests/test_cli.py
git commit -m "docs(agents): note R3.3 threat pass in canonical instruction file"
```

---

### Task 6: Worker-count test + architecture doc + CLAUDE.md + commit grill docs

**Files:**
- Modify: `docs/ade-architecture-design.md` (agent table row; R3.3 in Phase-1 detail; `13 → 14` counts at the four `agents/` lines)
- Modify: `CLAUDE.md` (`13 → 14` worker count; Phase-1 "at a glance" R3.3 mention)
- Add already-written (during grill): `CONTEXT.md`, `docs/adr/0005-design-time-threat-modeling.md`, `docs/research/threat-modeling-frameworks-2026-06.md`
- Test: `tests/test_cli.py` (add `test_generated_tree_has_fourteen_workers`)

**Interfaces:**
- Consumes: the `threat-modeler` template from Task 1.
- Produces: a guard that the worker count is 14, and synced human docs.

- [ ] **Step 1: Write the failing test (guards the count drift)**

```python
def test_generated_tree_has_fourteen_workers(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agents = list((python_project / ".claude" / "agents").glob("*.md"))
    assert len(agents) == 14, sorted(p.stem for p in agents)
```

- [ ] **Step 2: Run test to verify it passes (Task 1 already added the 14th worker)**

Run: `uv run pytest tests/test_cli.py::test_generated_tree_has_fourteen_workers -q`
Expected: PASS (Task 1 created the 14th agent; this test locks the count). If it reports 13, Task 1 was not applied — stop and fix.

- [ ] **Step 3: Update the architecture doc**

In `docs/ade-architecture-design.md`:
- Change each `worker subagent definitions (13 × …)` line (4 occurrences, lines ~33/39/45/50) from `13` to `14`.
- Add a row to the Subagent catalog table (after the `stub-reviewer` row):
  ```markdown
  | `threat-modeler` | sonnet | Read, Grep, Glob | R3.3 (blind threat pass, conditional) |
  ```
- In the Phase-1 detail section, after the `#### R3.2 — Orchestrator interview` block, add a short `#### R3.3 — Threat pass (conditional)` paragraph mirroring the skill: trigger (architecture / forced-escalation / judgment), the blind `threat-modeler`, trust-boundary STRIDE-lite + data classification, mitigations → acceptance criteria, residual risks surfaced.

- [ ] **Step 4: Update CLAUDE.md**

In `CLAUDE.md`:
- Change `agents/ # 12 worker subagent definition templates` — verify the actual current number in the file (the project-structure block) and bump it by one. (Grep first: `grep -n "worker subagent definition templates" CLAUDE.md`.)
- In the "Research phase (Phase 1) at a glance" section, add R3.3 to the sub-step list: `- **R3.3** Threat pass — conditional blind threat-modeler (trust-boundary STRIDE-lite + data classification); mitigations → acceptance criteria, residual risks surfaced.`

- [ ] **Step 5: Full suite + lint + eval, then commit everything**

```bash
uv run ruff format src/ tests/ && uv run ruff check src/ tests/
uv run pytest -q
uv run ade eval
git add docs/ade-architecture-design.md CLAUDE.md CONTEXT.md \
  docs/adr/0005-design-time-threat-modeling.md \
  docs/research/threat-modeling-frameworks-2026-06.md \
  docs/superpowers/specs/2026-06-24-design-time-threat-modeling-design.md \
  docs/superpowers/plans/2026-06-26-design-time-threat-modeling.md \
  tests/test_cli.py
git commit -m "docs(threat-modeling): ADR-0005, research, glossary, architecture sync; worker count 14"
```
Expected: full suite green, `PASS — skills well-formed.`

---

## Self-Review

**Spec coverage** (each §3 design element → task):
- §3.1 worker (blind, four-questions, STRIDE-lite, classification, PII-gated privacy, no-boilerplate, single-shot) → **Task 1**.
- §3.2 trigger (data_classification floor + R3.3 gate) → **Tasks 2 + 3 + 4**.
- §3.3 placement (R3.3 between R3.2 and R4) → **Task 4**.
- §3.4 classification (4-tier + PII flag) → **Tasks 1 + 4** (defined in worker + skill).
- §3.5 output contract (acceptance criteria, ADRs, residual risks, routing feedback) → **Task 4**.
- §3.6 tiers → **Tasks 3 + 4**.
- §3.7 glossary → written during grill, committed in **Task 6**.
- §3.8 Codex degradation → inherent (templates emit to Codex `.toml` unchanged; the in-context convention is described in the skill prose from Task 4). No separate task — the skill text covers it; add a sentence in Task 4's R3.3 prose if missing.
- §4 files: every Modified file has a task; ADR-0005/research/CONTEXT committed in Task 6.
- §6 test plan: covered by Tasks 1-6 tests + the two existing guards re-run.

**Placeholder scan:** every code/template step shows the full content. No TBD/TODO.

**Type/name consistency:** agent name `threat-modeler` (file `threat-modeler.md`), artifact `threat-model.md`, activity "threat pass", JSON key `keywords.data_classification`, routing line token `forced: data_classification`, classification tiers `public|internal|confidential|restricted` + `PII` flag, privacy categories `Linking, Identifying, Data Disclosure, Unawareness` — used identically across Tasks 1-6.

**One note for the executor:** Task 6 Step 3/4 edit a human doc whose exact current count wording should be grepped first (`13`/`12`) — the architecture doc says `13`, CLAUDE.md may differ; bump whatever is there by one. The `test_generated_tree_has_fourteen_workers` test is the real guard; the prose counts are cosmetic.
