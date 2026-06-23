# Research Provenance Grading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a claim-level `provenance` grade (`CONFIRMED | CITED | ASSUMED`) to ADE's research-phase agents and skill, layered on the existing source-level `trust`, so unconfirmed claims are visibly graded and routed to the user before they lock as spec facts.

**Architecture:** Pure prose/template edits to three worker-agent templates (`scout`, `web-researcher`, `synthesizer`) and the `ade-research` skill, plus a new ADR. No Python logic changes. Tests follow the established pattern: `ade init` into a temp project, read the generated Markdown, assert on substrings.

**Tech Stack:** Jinja2 templates (`.j2`), Python 3.11 + pytest, `typer` CLI test runner.

## Global Constraints

- The grade vocabulary is exactly three values, spelled in all-caps: `CONFIRMED`, `CITED`, `ASSUMED`. The top grade is `CONFIRMED`, never `VERIFIED` (collision with the R5 Verify phase).
- `trust` (source axis: `high|medium|low`) is unchanged and is NOT replaced; `provenance` is the second, orthogonal axis.
- **Trust floor:** a `trust: low` source cannot, on its own, lift a claim above `ASSUMED`.
- **Monotonic default:** any untraceable/unsupported claim is `ASSUMED`; absent evidence never defaults to fact.
- Do not introduce the tokens `Playwright`, `docker compose`, `localhost`, `NO EXEMPTIONS`, `/10`, `qa-verify` (existing stale-reference guards forbid them).
- The canonical grade definitions live in `ade-research` SKILL + `CONTEXT.md`; agents reference them, keeping wording consistent.
- TDD, one file per task, commit after each.

**Already complete (do not redo):** `CONTEXT.md` "Research provenance" glossary group was added during the grill (commit `0b269a7`). Tasks below assume it exists.

**Test harness pattern (used by every task):**
```python
from pathlib import Path
from typer.testing import CliRunner
from ade.cli import app
runner = CliRunner()
# in a test taking the `python_project` fixture:
runner.invoke(app, ["init", "--project-dir", str(python_project)])
content = (python_project / ".claude" / "agents" / "<name>.md").read_text()
assert "<substring>" in content
```

---

### Task 1: Scout provenance (read-it vs inferred-it)

**Files:**
- Modify: `src/ade/templates/agents/scout.md.j2`
- Test: `tests/test_cli.py` (add one test)

**Interfaces:**
- Produces: generated `.claude/agents/scout.md` contains a `provenance:` schema field and a CONFIRMED/ASSUMED definition block.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:
```python
def test_scout_agent_tags_provenance(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    content = (python_project / ".claude" / "agents" / "scout.md").read_text()
    assert "provenance:" in content
    assert "CONFIRMED" in content and "ASSUMED" in content
    # framed as read-it vs inferred-it (the forcing function)
    assert "read the actual" in content.lower() or "without reading" in content.lower()
    # scouts cite the repo first-hand, so they do not emit CITED
    assert "do not emit CITED" in content or "never emit CITED" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_scout_agent_tags_provenance -q`
Expected: FAIL (`assert "provenance:" in content`).

- [ ] **Step 3: Edit the template**

In `src/ade/templates/agents/scout.md.j2`, add `provenance` to each finding in the `## Findings` schema block — change:
```markdown
- path: <repo-relative path>
  lines: <start-end>
  relevance: <0.0-1.0>
  summary: <one sentence on why this is relevant>
```
to:
```markdown
- path: <repo-relative path>
  lines: <start-end>
  relevance: <0.0-1.0>
  provenance: <CONFIRMED|ASSUMED>
  summary: <one sentence on why this is relevant>
```
Then insert this block immediately after the `## Relevance scoring` section (before `## Output schema`):
```markdown
## Provenance (how you know each finding)

Tag every finding with `provenance` — a forcing function against name-based guessing:

- **CONFIRMED** — you read the actual code that shows it. First-hand evidence.
- **ASSUMED** — you inferred it from a name, signature, or comment **without reading the body**, or it is an Open Question. Inference is not fact; never label it CONFIRMED.

You read the repo first-hand, so scouts do not emit CITED (citing the repo itself is first-hand = CONFIRMED). If your read budget ran out before you opened a file you are describing, that finding is ASSUMED.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_scout_agent_tags_provenance -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ade/templates/agents/scout.md.j2 tests/test_cli.py
git commit -m "feat(research): scout tags finding provenance (read-it vs inferred-it)"
```

---

### Task 2: Web-researcher claim-level provenance + trust floor

**Files:**
- Modify: `src/ade/templates/agents/web-researcher.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: generated `.claude/agents/web-researcher.md` carries a claim-level `provenance` distinct from source `trust`, plus the trust-floor rule.

- [ ] **Step 1: Write the failing test**
```python
def test_web_researcher_claim_provenance_and_trust_floor(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    content = (python_project / ".claude" / "agents" / "web-researcher.md").read_text()
    assert "provenance" in content
    assert "CONFIRMED" in content and "CITED" in content and "ASSUMED" in content
    # source trust is retained, not replaced
    assert "trust: high" in content
    # trust floor: a trust:low source cannot lift a claim above ASSUMED
    low = content.lower()
    assert "trust floor" in low or ("trust: low" in content and "above" in low and "assumed" in low)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_web_researcher_claim_provenance_and_trust_floor -q`
Expected: FAIL (`assert "CONFIRMED" in content`).

- [ ] **Step 3: Edit the template**

In `src/ade/templates/agents/web-researcher.md.j2`, add a `provenance` line to each source in the `## Sources` schema (after `trust: high | medium | low`):
```markdown
   - trust: high | medium | low
   - provenance: CONFIRMED | CITED | ASSUMED
```
Then insert this section immediately after the `## Security and trust` section (before `## Output schema`):
```markdown
## Provenance (claim-level — a second axis, distinct from source trust)

`trust` rates the SOURCE; `provenance` rates the CLAIM. Tag every finding:

- **CONFIRMED** — corroborated by ≥2 independent sources, or a verbatim quote from a `trust: high` primary source.
- **CITED** — exactly one source that **actually supports** the claim. A citation that does not support the statement is NOT CITED — it is ASSUMED.
- **ASSUMED** — no fetchable/supporting source, or your own inference.

**Trust floor (security):** a `trust: low` source — including any page you flagged for prompt-injection — **cannot, on its own, lift a claim above ASSUMED**. A claim reaches CITED or CONFIRMED only with support from a `trust: medium`-or-better source, or ≥2 independent sources. This keeps injected content out of locked spec facts.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_web_researcher_claim_provenance_and_trust_floor -q`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add src/ade/templates/agents/web-researcher.md.j2 tests/test_cli.py
git commit -m "feat(research): web-researcher claim-level provenance + trust floor"
```

---

### Task 3: Synthesizer — carry grades, monotonic default, routing, Assumptions section

**Files:**
- Modify: `src/ade/templates/agents/synthesizer.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: scout `provenance` (Task 1), web `provenance` (Task 2).
- Produces: generated `synthesizer.md` carries grades, applies monotonic default + trust floor, replaces `[unverified]` with `[ASSUMED]`, routes material `[ASSUMED]`/conflicts to Open Questions, and gathers residual ASSUMED into an "Assumptions" section.

- [ ] **Step 1: Write the failing test**
```python
def test_synthesizer_provenance_rules(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    content = (python_project / ".claude" / "agents" / "synthesizer.md").read_text()
    # legacy ad-hoc marker is gone, replaced by the grade
    assert "[unverified]" not in content
    assert "[ASSUMED]" in content
    # monotonic default + routing + assumptions section
    low = content.lower()
    assert "monotonic" in low or "never" in low and "fact" in low
    assert "Open Questions" in content
    assert "## Assumptions" in content or "Assumptions" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_synthesizer_provenance_rules -q`
Expected: FAIL (`assert "[unverified]" not in content` — it is still present).

- [ ] **Step 3: Edit the template**

In `src/ade/templates/agents/synthesizer.md.j2`:

(a) Replace the Role A trust-weighting bullet:
```markdown
- Apply trust weighting: prefer `trust: high` sources over `trust: medium`; treat `trust: low` sources as needing user confirmation.
```
with:
```markdown
- Carry each claim's `provenance` (`CONFIRMED`/`CITED`/`ASSUMED`) co-located with the claim and its citation. Apply trust weighting AND the **trust floor**: a `trust: low` source cannot, on its own, lift a claim above `ASSUMED`.
- **Monotonic default:** any claim you cannot trace to first-hand evidence or a supporting source is `[ASSUMED]` — never state it as a bare fact.
- **Route material `[ASSUMED]` claims into "Open Questions for User"** (material = changes architecture, data model, testing, UX, operations, or compliance if wrong). Two sources that disagree are also an Open Question. You may promote `CITED`→`CONFIRMED` when a second independent source corroborates.
```

(b) Add an `## Assumptions` entry to the draft-spec structure — change:
```markdown
## Out of Scope
- Explicit non-goals.
```
to:
```markdown
## Assumptions
- Residual `[ASSUMED]` claims the interview did not resolve — explicit, labeled, never stated elsewhere as fact.

## Out of Scope
- Explicit non-goals.
```

(c) Replace the `[unverified]` instruction in the "Both roles" section:
```markdown
- If you cannot trace a claim to a source, mark it `[unverified]` rather than dropping the citation entirely.
```
with:
```markdown
- If you cannot trace a claim to first-hand evidence or a supporting source, mark it `[ASSUMED]` (the monotonic default) rather than stating it as fact. At lock, gather residual `[ASSUMED]` claims into the spec's Assumptions section; keep `CITED` claims' `[n]` citation; leave `CONFIRMED` claims unmarked.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_synthesizer_provenance_rules -q`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add src/ade/templates/agents/synthesizer.md.j2 tests/test_cli.py
git commit -m "feat(research): synthesizer carries provenance, monotonic default, Assumptions section"
```

---

### Task 4: ade-research skill — canonical grading subsection + R2/R3/R5 wiring

**Files:**
- Modify: `src/ade/templates/skills/ade-research/SKILL.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: generated `.claude/skills/ade-research/SKILL.md` defines the two axes + three grades once, prioritizes material `ASSUMED` within the 5-question cap, and points R5 CoVe at `CITED`/`ASSUMED` first.

- [ ] **Step 1: Write the failing test**
```python
def test_ade_research_defines_provenance(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    content = (python_project / ".claude" / "skills" / "ade-research" / "SKILL.md").read_text()
    assert "Provenance grading" in content
    assert "CONFIRMED" in content and "CITED" in content and "ASSUMED" in content
    # ASSUMED prioritized within the existing 5-question cap
    low = content.lower()
    assert "assumed" in low and ("5 question" in low or "five question" in low or "5-question" in low or "cap" in low)
    # R5 CoVe targets the lowest-grounded claims first
    assert "CITED" in content and "CoVe" in content or "spec-verifier" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_ade_research_defines_provenance -q`
Expected: FAIL (`assert "Provenance grading" in content`).

- [ ] **Step 3: Edit the template**

In `src/ade/templates/skills/ade-research/SKILL.md.j2`:

(a) Add a canonical subsection (place it near the top of the R2/R3 area, e.g. just before `### R3.2 — Orchestrator interview`):
```markdown
### Provenance grading (two axes)

Every research claim is graded on two orthogonal axes:

- **`trust`** — the SOURCE axis (`high|medium|low`), set by `web-researcher`; also the prompt-injection signal.
- **`provenance`** — the CLAIM axis, set by scouts/web and carried by the synthesizer:
  - **CONFIRMED** — first-hand observed (a scout read the code) or corroborated by ≥2 independent sources.
  - **CITED** — exactly one source that actually supports the claim.
  - **ASSUMED** — inference or untraceable. **Monotonic default:** when in doubt, ASSUMED — absent evidence is never a fact. **Trust floor:** a `trust: low` source alone cannot lift a claim above ASSUMED.

(`CONFIRMED` is deliberately not "verified" — that word names this phase's R5 step.)
```

(b) In `### R3.2 — Orchestrator interview`, add to the asking rules (alongside the existing 5-question cap):
```markdown
- **Prioritize material `ASSUMED` claims and source conflicts** within the 5-question cap — an un-grounded "fact" is higher-risk than an open design choice, so it outranks ambiguity-taxonomy gaps. A claim the user confirms becomes `CONFIRMED`; any `ASSUMED` claim left unresolved at the cap stays labeled in the spec's Assumptions section — never silently promoted.
```

(c) In the R5 Verify section, add:
```markdown
- **Prioritize `CITED` and `ASSUMED` claims** for verification (lowest-grounded, highest payoff); the verifiers remain blind to the spec. A user-confirmed `CONFIRMED` claim is a reusable verifier-assertion — do not re-litigate it.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_ade_research_defines_provenance -q`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add src/ade/templates/skills/ade-research/SKILL.md.j2 tests/test_cli.py
git commit -m "feat(research): ade-research defines provenance grades + R3/R5 wiring"
```

---

### Task 5: ADR-0004 — two-axis research provenance

**Files:**
- Create: `src/ade/templates/bootstrap/` is NOT the target — ADRs live in the repo: `docs/adr/0004-two-axis-research-provenance.md`
- Test: `tests/test_cli.py` is not appropriate (the ADR is a repo doc, not generated). Use a lightweight repo-doc test in `tests/test_cli.py` guarded by repo path, OR assert via a plain file check. See Step 1.

**Interfaces:**
- Produces: `docs/adr/0004-two-axis-research-provenance.md` exists, names the two axes, the trust-floor deviation, and the rejected single-axis alternative.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py` (reads the repo doc directly, relative to the test file):
```python
def test_adr_0004_exists_and_records_two_axes() -> None:
    repo = Path(__file__).resolve().parents[1]
    adr = repo / "docs" / "adr" / "0004-two-axis-research-provenance.md"
    assert adr.exists()
    text = adr.read_text()
    assert "trust" in text and "provenance" in text
    assert "CONFIRMED" in text and "CITED" in text and "ASSUMED" in text
    assert "trust floor" in text.lower()
    assert "Admiralty" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_adr_0004_exists_and_records_two_axes -q`
Expected: FAIL (file missing).

- [ ] **Step 3: Create the ADR**

Create `docs/adr/0004-two-axis-research-provenance.md` following the style of `0001`–`0003`:
```markdown
# 4. Two-axis research provenance grading

Date: 2026-06-23

## Status

Accepted

## Context

ADE's research phase (Phase 1) produces a spec from internal code-scout findings and web-research findings. Previously, a fact from an unconfirmed blog, a first-hand code read, and a pure inference all looked identical once they landed in the draft spec; only an ad-hoc `[unverified]` marker existed. The adversarial review (`docs/ade-sdlc-adversarial-review-suggestions-2026-06.md`, cleanup #4) flagged that `ASSUMED` claims could silently lock as spec facts.

A deep-research survey (`docs/research/provenance-and-evidence-grading-frameworks-2026-06.md`, 24/25 claims adversarially verified) found that separating **source reliability** from **claim credibility** is a doctrine-level standard: NATO's Admiralty Code (STANAG 2511) mandates the two be judged independently, GRADE mirrors it, and W3C PROV confirms that provenance models deliberately carry no grading of their own.

## Decision

Grade research on two orthogonal axes:

- **`trust`** (existing) — the SOURCE axis: `high | medium | low`. ≈ Admiralty reliability A–F. Also the prompt-injection signal.
- **`provenance`** (new) — the CLAIM axis: `CONFIRMED | CITED | ASSUMED`. ≈ Admiralty credibility 1–6.
  - **CONFIRMED** — first-hand observed or corroborated by ≥2 independent sources (Admiralty credibility-1, "confirmed by other sources"). Named `CONFIRMED`, not `VERIFIED`, to avoid colliding with the R5 Verify (Chain-of-Verification) phase.
  - **CITED** — exactly one source that actually supports the claim.
  - **ASSUMED** — inference or untraceable.

Two safety rules:
- **Monotonic default** (from in-toto): missing/unsupported evidence is `ASSUMED`, never a fact.
- **Trust floor** — ADE's one deliberate departure from Admiralty's strict axis-independence: a `trust: low` source cannot, on its own, lift a claim above `ASSUMED`. This blocks injection-laundering of untrusted web content into locked spec facts.

Material `ASSUMED` claims (and source conflicts) route into the R3 interview, prioritized within the 5-question cap; unresolved ones stay labeled in the spec's Assumptions section.

## Consequences

- Research evidence is auditable: each claim shows how it is known, separate from how trustworthy its source is.
- Caveat (Irwin & Mandel 2019): rigid scales can create false objectivity and collapse onto a diagonal. Mitigated by exactly three crisp levels, revisable grades, and no over-claimed precision.
- Rejected alternative: a trust-only single axis (simpler, but cannot distinguish a first-hand code read from an inference attributed to a high-trust source).
- The two-axis model and its terms are recorded in `CONTEXT.md`.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_adr_0004_exists_and_records_two_axes -q`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add docs/adr/0004-two-axis-research-provenance.md tests/test_cli.py
git commit -m "docs(adr): ADR-0004 two-axis research provenance grading"
```

---

### Task 6: Cross-cutting naming guard + full suite/eval

**Files:**
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: Tasks 1–5 (generated tree).

- [ ] **Step 1: Write the failing test (guard)**
```python
def test_no_verified_grade_token_in_generated_tree(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    root = python_project / ".claude"
    confirmed_seen = False
    for path in root.rglob("*.md"):
        text = path.read_text()
        # the all-caps VERIFIED grade token must never appear (collides with R5 Verify)
        assert "VERIFIED" not in text, f"stray VERIFIED grade token in {path}"
        if "CONFIRMED" in text:
            confirmed_seen = True
    assert confirmed_seen, "CONFIRMED grade not present anywhere in the generated tree"
```

- [ ] **Step 2: Run the guard**

Run: `uv run pytest tests/test_cli.py::test_no_verified_grade_token_in_generated_tree -q`
Expected: PASS (Tasks 1–4 introduced CONFIRMED, none introduced all-caps VERIFIED). If it FAILS on a stray `VERIFIED`, fix that template to `CONFIRMED`.

- [ ] **Step 3: Full suite + eval + stale guard**

Run:
```bash
uv run pytest -q
uv run ruff check src/ tests/
# fresh-tree eval + stale-reference guard
D="$(mktemp -d)"; ( cd "$D" && git init -q . && uv run --project "$OLDPWD" ade init --agent all >/dev/null 2>&1 ); \
  uv run --project "$(pwd)" ade eval
```
Expected: all green; `ade eval` prints `PASS — skills well-formed.`

- [ ] **Step 4: Commit**
```bash
git add tests/test_cli.py
git commit -m "test(research): guard against stray VERIFIED grade token; confirm CONFIRMED present"
```

---

## Self-Review

**Spec coverage** (spec §4 files → tasks):
- `scout.md.j2` → Task 1 ✓
- `web-researcher.md.j2` → Task 2 ✓
- `synthesizer.md.j2` → Task 3 ✓
- `ade-research/SKILL.md.j2` → Task 4 ✓
- `docs/adr/0004-…` → Task 5 ✓
- `CONTEXT.md` → already done (grill, `0b269a7`) ✓
- Naming guard (spec §5) → Task 6 ✓

**Spec rules → coverage:** two-axis (T2/T4/T5), CONFIRMED-not-VERIFIED (T6 guard + everywhere), trust floor (T2/T3/T4/T5), monotonic default (T3/T4), CITED-must-support (T2), ASSUMED→R3 within 5-cap (T4), CoVe targets CITED/ASSUMED (T4), Assumptions section at lock (T3), scout read-vs-inferred (T1). All covered.

**Placeholder scan:** none — every step has concrete test code or concrete template content.

**Type/string consistency:** grade tokens are uniformly `CONFIRMED|CITED|ASSUMED`; the bracket form `[ASSUMED]` is used consistently for the synthesizer marker; `provenance:` (lowercase key) used in all agent schemas.
