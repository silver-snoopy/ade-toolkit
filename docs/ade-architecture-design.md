# ADE Architecture

This document describes ADE's current architecture: what `ade init` produces, how the resulting Claude Code installation runs the 10-phase SDLC, and the invariants that govern orchestration.

ADE is a *scaffolder*, not a runtime. The Python package writes a self-contained `.claude/` tree, seeds project documentation artifacts (`CONTEXT.md`, `docs/adr/`, `docs/specs/`), and exits. Claude Code is the runtime: subagent dispatch, worktree isolation, file I/O, and shell execution all use native Claude Code capabilities.

## Architecture at a glance

```
ade-toolkit (Python)
├── ade init      → writes templates into the target project
├── ade doctor    → verifies external tools + project state
└── ade status    → reads .ade/tasks/ to summarize active work

target project after `ade init`:
.claude/
├── agents/       → 9 subagent definitions (Markdown with YAML frontmatter)
├── skills/ade/
│   ├── phases/   → 10 phase skill files (00-intent.md … 10-retro.md)
│   ├── ade-*.md  → 6 composite workflow skills (ade-full, ade-plan, …)
│   └── vendored/ → external skills vendored with attribution
└── commands/     → slash commands that invoke the composite skills

.ade/tasks/       → ephemeral per-task working state (one dir per task-id)

docs/
├── adr/          → ADRs (sequential, immutable once accepted)
└── specs/        → permanent specs (one per task, date-prefixed filename)

CONTEXT.md        → domain glossary (user-owned after seed)
CLAUDE.md         → ADE workflow section appended on init
```

## The 10-phase SDLC

| Phase | Purpose | Primary actor | Output |
|---|---|---|---|
| 0 — Intent | Extract structured requirements | Orchestrator | `.ade/tasks/<id>/intent.md` |
| 1 — Research | Produce verified durable spec | R1–R5 (see below) | `docs/specs/{date}_{slug}.spec.md`, `CONTEXT.md` updates, `docs/adr/NNNN-*.md` |
| 2 — Plan | Write implementation plan | Orchestrator | `.ade/tasks/<id>/plan.md` (6 mandatory sections) |
| 3 — Design check | Generate stubs in worktree | Sonnet subagent | Stub files matching plan |
| 4 — Implement | Author-separated TDD: write failing tests then drive them to green | `test-writer` (RED) → 1–3 implementer subagents (GREEN) | Tests + code in worktree |
| 5 — Quality gate | Lint, format, build, tests | Haiku subagent | Pass/fail with fix loop (max 3) |
| 6 — Review | Multi-aspect code review | `pr-review-toolkit` (preferred) or 3 parallel Sonnet subagents (fallback) | Findings table (Critical / Important / Suggestions / Positive) |
| 7 — Verify | Live evidence per acceptance criterion | Orchestrator | `.ade/tasks/<id>/verification/` |
| 8 — Docs | Update affected documentation | Sonnet subagent | Architecture / API / capabilities updates |
| 9 — Ship | Commit, push, PR | Orchestrator | PR URL |
| 10 — Retro | Metrics + cleanup | Orchestrator | `.ade/tasks/<id>/retro.json` |

Human gates: after R5 (ready-for-development), after Phase 2 (plan completeness), after Phase 9 (merge decision).

## Phase 1 — Research (detailed)

Phase 1 is the most rigorous and recently rebuilt part of the pipeline. It has five sub-steps producing artifacts that compound across tasks.

### R1 — Intent

Phase 0's output (`intent.md`) feeds R1 unchanged. The S/M/L scope estimate stays in `intent.md` as informational metadata only. **It does not route Phase 1.** Cost-adaptiveness comes from R2.2 (orchestrator confidence) and the trivial-when-shallow behavior of R4 and R5.

### R2 — Investigate

#### R2.1 — Code scouting with iterative retrieval

Pattern: **DISPATCH → EVALUATE → REFINE → LOOP** (max 3 cycles).

Cycle 1 dispatches two `scout` subagents in parallel:

- `scout` with `current-state` scope — "What exists related to this task? Find call sites, entry points, current behavior."
- `scout` with `available-surface` scope — "What can this feature compose with? Utilities, helpers, types, fixtures, test surfaces."

Each scout writes findings scored on the 0.0–1.0 relevance scale:

| Score | Meaning |
|---|---|
| 0.8–1.0 | Directly implements target functionality |
| 0.5–0.7 | Contains related patterns or types |
| 0.2–0.4 | Tangentially related |
| 0.0–0.2 | Not relevant (excluded from output) |

**Stop criterion** (all must hold):

1. ≥3 high-relevance findings (score ≥ 0.8) across both scouts
2. No critical gaps in `coverage_caveats`
3. No terminology mismatch flagged (e.g., scout reports "code uses `policies`, not `permissions`")

If unmet, REFINE: orchestrator extracts vocabulary signals from cycle-1 returns (actual identifiers, CONTEXT.md terms, domain language from paths) and re-dispatches scouts with refined search terms.

Hard cap of 3 cycles. After cycle 3, proceed with best-available findings; flag remaining gaps prominently for R3.

#### R2.2 — Orchestrator confidence check

The orchestrator reviews scout outputs and decides whether web research is needed. The decision rule:

> Web research is needed if (a) the user explicitly requested it at R1, OR (b) any scout `open_questions[]` references an external library, framework, API, service name, or domain concept not present in `CONTEXT.md`, OR (c) scouts found that the task fundamentally depends on infrastructure not visible in the local codebase.

The decision (with justification) is written to `.ade/tasks/<id>/research/r2.2-decision.md`. If the orchestrator can't articulate specific topics for web research, it must skip R2.3 — "we should probably look around online" is not a valid trigger.

#### R2.3 — Web research (conditional)

For each topic identified at R2.2, dispatch one `web-researcher` subagent (typically 1–3 total).

**Tier 0 (default)**: WebSearch + WebFetch + Context7 MCP. Zero paid keys required.
**Tier 1 (opt-in)**: Tavily, Exa MCPs — engaged only if their API key env vars are set or user passed `--deep`.
**Tier 2 (manual)**: Firecrawl (JS rendering), Perplexity Sonar (built-in citations) — never automatic; user must configure.

The `web-researcher` agent definition enforces:

- **Citation invariants** — every claim ends with `[n]` citation; sources block has URL, retrieved_at, verbatim quote ≤150 chars
- **Trust tagging** — `high` (official docs, vendor advisories), `medium` (user-generated content), `low` (sources with detected prompt-injection signals or unidentifiable origin)
- **IPI hardening** — fetched content treated as untrusted data; instructions embedded in retrieved pages are not followed; LLM-directed content flags the source to `trust: low`

Sequencing: parallel with R2.1 if user opted in at R1, otherwise sequential after R2.2 decision.

### R3 — Specify

#### R3.1 — Synthesizer drafts

`synthesizer` subagent (Role A — research consolidation):

- Input: research bundles in `.ade/tasks/<id>/research/` (scout-*.md, web-*.md if any)
- Pattern: single-writer (no parallelization for synthesis — disjoint reports are a documented failure mode)
- Dedupes hot anchors and shared URLs; applies trust weighting; preserves citation chains
- Output: draft spec at `docs/specs/{YYYY-MM-DD}_{slug}.spec.md`

Slug is derived from `intent.md` goal (2–4 kebab-case words). On same-day collision: auto-incrementing `_2`, `_3` suffix before `.spec.md`.

#### R3.2 — Orchestrator interview

The orchestrator refines the draft through Socratic Q&A with the user, scanning the draft against a **10-category ambiguity taxonomy**:

1. Functional Scope
2. Data Model
3. UX Flow
4. Non-Functional Attributes (performance, scale, availability)
5. Integration (external systems, APIs)
6. Edge Cases
7. Constraints (regulatory, technical, time)
8. Terminology
9. Completion Signals
10. Misc

For each material gap found, generate exactly one question. Format:

- Tagged with its category
- Multi-choice (2–5 options) with one marked **recommended** and paired with exactly **one alternative** (2nd best), OR short-phrase answer (≤5 words expected)
- Only asked if the answer materially impacts architecture, data modeling, testing, UX, operations, or compliance

Hard rules:

- **One question at a time.** Wait for user's answer before next question.
- **Update spec atomically after each answer** (`Edit`, not `Write`).
- **Hard cap: 5 questions total per spec.** Past 5, proceed with what you have.
- **Stop early** when no high-impact, high-uncertainty items remain.

### R4 — Refine (grill-with-docs)

Invoke the vendored `grill-with-docs` skill against the spec. Skill location: `.claude/skills/ade/vendored/mattpocock-grill-with-docs/SKILL.md`.

Phase-prompt framing wraps the skill so the spec is treated as the "plan" the skill grills, with explicit instructions to revise the spec inline alongside the skill's native side effects (CONTEXT.md updates, ADR drafts).

`grill-with-docs` outputs:

- **CONTEXT.md updates** — incrementally, inline. Glossary entries follow the format in `vendored/mattpocock-grill-with-docs/CONTEXT-FORMAT.md`.
- **ADRs (sparingly)** — `docs/adr/NNNN-slug.md`, sequential numbering. Three-criteria gate: hard-to-reverse, surprising-without-context, real trade-off. If any criterion is missing, the skill skips the ADR.

R4 **always runs**. It is *trivial* when the spec already uses CONTEXT.md vocabulary and reflects existing ADRs (Socratic loop ends quickly, zero updates). It is *substantive* when the spec introduces new terms or architectural decisions.

### R5 — Verify (Chain of Verification, factor+revise)

Built-in directive — no external skill invoked. The orchestrator runs the CoVe pattern:

**R5.1 — Extract claims.** Orchestrator reads the spec and extracts 8–15 verification claims. Each claim is a statement the spec asserts about the world or the project. Each claim is tagged with one of the 10 ambiguity categories. Written to `.ade/tasks/<id>/research/r5-claims.md`.

**R5.2 — Dispatch verifiers (the "factor" step).** For each claim, dispatch one `spec-verifier` subagent in parallel.

**Critical structural rule**: the verifier subagent MUST NOT receive the spec text. The orchestrator passes only the single claim, its category, and a pointer to the project's code and docs. This is the defining property of factor+revise CoVe — the verifier's answer must not be biased by what the spec already claims.

The `spec-verifier` agent definition treats this as a structural guarantee, not a prompt rule: if a dispatch prompt accidentally includes spec text, the verifier flags it in `Concerns` rather than answering.

Verifier output schema: `Answer` (yes/no/partial/unanswerable), `Evidence` (file paths + line ranges), `Confidence` (high/medium/low), `Concerns` (suspect questions, sparse evidence).

**R5.3 — Revise (the "revise" step).** `synthesizer` (Role B — spec revision) compares verifier outputs to spec claims:

- **Material discrepancy** (verifier evidence contradicts a claim, or surfaces an unaddressed gap) → revise spec
- **Soft signal** (low confidence, verifier concerns about the question itself) → note in spec's risks/assumptions; do not silently soften
- **No issue** (verifier confirmed claim) → no action

### Ready-for-Development gate

After R5, the orchestrator summarizes:

- Path to the finalized spec
- New CONTEXT.md entries (count + topics)
- New ADRs (count + titles)
- Verifier findings noted-but-not-revised (with rationale)

User confirms readiness. The spec is now the contract for the Development phase.

## Phases 2–10 (current state)

These phases retain the structure that predates the v5 Research rewrite. They are functional and produce useful work, but they would benefit from the same rigor pass applied to Phase 1. A future thread will rework them.

- **Phase 2 — Plan**: 6 mandatory sections (Context, Ordered task list, Files, Dependencies, Test strategy, Risk areas). Primary input: the spec from R5.
- **Phase 3 — Design check**: Subagent in worktree generates file stubs from plan. Max 2 iterations.
- **Phase 4 — Implement**: Author-separated TDD. Phase 4a: `test-writer` writes failing tests covering the plan's acceptance criteria and commits them alone (RED). Phase 4b: 1–3 implementer subagents (`backend-coder`, `frontend-coder`) drive those tests to GREEN, never editing test files. Build order: shared → backend → frontend. The `block-mixed-commit` hook enforces the commit boundary between phases.
- **Phase 5 — Quality gate**: Lint, format, build, tests. Fix loop max 3.
- **Phase 6 — Review**: `pr-review-toolkit` preferred; fallback is 3 parallel subagents (Logic / Conventions / Security). Findings classified Critical / Important / Suggestions / Positive. Review-fix cycle max 3.
- **Phase 7 — Verify**: Live evidence per acceptance criterion. Max 2 verify-reject cycles.
- **Phase 8 — Docs**: Architecture, capabilities, API docs, CLAUDE.md updates.
- **Phase 9 — Ship**: Commit, push, open PR. Human gate.
- **Phase 10 — Retro**: Metrics, learnings, worktree cleanup.

## Deterministic hook layer (G2)

Two Python scripts committed under `.claude/hooks/` act as a hard gate on commit integrity. Because they live inside the repository (not in gitignored `.ade/`), they are present inside every git worktree without any extra setup step.

### Checks

- **`block-mixed-commit.py`** — rejects any commit that contains both test files and non-test source files in the same changeset. This enforces the Phase 4a/4b author separation at the VCS level. Bypass: include `[test-refactor]` in the commit message for the narrow case of a refactor that must touch both together.
- **`check-leftover-stub.py`** — rejects committed non-test source files that still contain stub markers (`NotImplementedError`, `TODO: implement`, or `Not implemented`). This prevents stubs from being accidentally shipped as real implementation.

Both scripts share common detection logic via `_hooklib.py` (also in `.claude/hooks/`), so they work identically regardless of which substrate wires them.

### Wiring — `ade init --agent {claude,copilot}`

The hook substrate is selected once at project initialization:

- **`--agent claude`** (default): writes `.claude/settings.json` with PreToolUse(Bash) hook entries, merged idempotently into any pre-existing settings file. Claude Code runs the checks before each relevant Bash tool call.
- **`--agent copilot`**: seeds `.pre-commit-config.yaml` with pre-commit hook entries. After init, run `pre-commit install --hook-type pre-commit --hook-type commit-msg` to activate. Git runs the checks at commit time.

### Failure behavior

Both hooks are a **hard gate**: a violation rejects the commit with a human-readable explanation. The orchestrator does not retry past a hook failure — the violation must be corrected before the commit is retried.

## Subagent catalog

All subagents are defined as Markdown files under `.claude/agents/` with YAML frontmatter declaring model and tool surface.

| Agent | Model | Tools | Used in |
|---|---|---|---|
| `scout` | haiku | Read, Grep, Glob, Bash | R2.1 |
| `web-researcher` | sonnet | WebSearch, WebFetch, Read | R2.3 |
| `synthesizer` | sonnet | Read, Write | R3.1, R5.3 |
| `spec-verifier` | sonnet | Read, Grep, Glob | R5.2 |
| `test-writer` | sonnet | Read, Write, Edit, Bash, Glob, Grep | Phase 4a |
| `backend-coder` | sonnet | Read, Write, Edit, Bash, Glob, Grep | Phase 4b |
| `frontend-coder` | sonnet | Read, Write, Edit, Bash, Glob, Grep | Phase 4b |
| `code-reviewer` | sonnet | Read, Glob, Grep | Phase 6 fallback |
| `security-reviewer` | sonnet | Read, Glob, Grep | Phase 6 fallback |
| `test-runner` | haiku | Read, Bash | Phase 5 |

The orchestrator (Claude Opus in the main session) is the only actor that dispatches subagents. Subagents do not invoke other subagents — composition is orchestrator-driven.

## Artifact contracts

| Artifact | Produced by | Consumed by | Lifecycle |
|---|---|---|---|
| `.ade/tasks/<id>/intent.md` | Phase 0 | R2 through D6 | Ephemeral (per task) |
| `.ade/tasks/<id>/research/scout-*.md` | R2.1 scouts | R2.2, R3.1 | Ephemeral |
| `.ade/tasks/<id>/research/r2.2-decision.md` | R2.2 orchestrator | R2.3 (if web), R3.1 | Ephemeral |
| `.ade/tasks/<id>/research/web-*.md` | R2.3 web-researchers | R3.1 | Ephemeral |
| `.ade/tasks/<id>/research/r5-claims.md` | R5.1 orchestrator | R5.2 verifiers, R5.3 synthesizer | Ephemeral |
| `.ade/tasks/<id>/research/r5-verifier-*.md` | R5.2 verifiers | R5.3 synthesizer | Ephemeral |
| `docs/specs/{date}_{slug}.spec.md` | R3.1 + R3.2 + R4 + R5.3 | Phase 2, Phase 7 | **Permanent (versioned)** |
| `CONTEXT.md` | `grill-with-docs` (R4) inline | All subsequent phases, future tasks | **Permanent (additive)** |
| `docs/adr/NNNN-*.md` | `grill-with-docs` (R4) sparingly | Future tasks (reference) | **Permanent (immutable once accepted)** |
| `.ade/tasks/<id>/plan.md` | Phase 2 | Phases 3–7 | Ephemeral |
| `.ade/tasks/<id>/status.md` | All phases (orchestrator updates) | `ade status` | Ephemeral |
| `.ade/tasks/<id>/verification/` | Phase 7 | Phase 9 (PR evidence) | Ephemeral |
| `.ade/tasks/<id>/retro.json` | Phase 10 | (reference, future calibration) | Ephemeral |

The line between ephemeral and permanent maps to ownership: `.ade/tasks/` is per-task working state, gitignored. `docs/` is project-owned, version-controlled, durable.

## Composition model

Anthropic does not support declarative peer-dependencies for Claude Code skills ([anthropics/claude-code#27113](https://github.com/anthropics/claude-code/issues/27113), closed as not planned). ADE's distribution model is shaped by that constraint:

- **Vendor with attribution** for skills ADE depends on structurally. Source files are copied into `src/ade/templates/skills/vendored/{author-skill-name}/`, original LICENSE preserved, vendoring source noted. Currently vendored:
  - `mattpocock-grill-with-docs` (MIT, copyright 2026 Matt Pocock)
- **Reference by name** for plugins that improve quality but aren't structurally required. ADE phase prompts use a "preferred mechanism + native fallback" pattern. The phase still works without the plugin installed; quality is lower. Currently referenced:
  - `pr-review-toolkit` (Phase 6 multi-aspect review)

Vendored skills resolve identically to user-installed plugin skills at runtime — Claude Code walks `.claude/skills/**/SKILL.md` for discovery, so nesting under `vendored/` doesn't affect resolution.

## Bootstrap and `ade init` lifecycle

`ade init` is idempotent and divides outputs into two categories by ownership:

**ADE-owned (regenerated every init)**:
- `.claude/agents/*.md`
- `.claude/skills/ade/**`
- `.claude/commands/*.md`
- `.ade/.gitignore`
- The ADE section appended to `CLAUDE.md`

**User-owned (seeded once, never overwritten)**:
- `CONTEXT.md`
- `docs/adr/0001-record-architecture-decisions.md`
- `docs/specs/README.md`

The CLI helper `_render_and_write_if_missing` enforces the user-owned contract: if the destination already exists, the file is preserved verbatim. Second-init output marks these as `= Kept existing <path>` rather than `+ Created <path>`.

## Orchestrator invariants

These rules govern the orchestrator's behavior. Violations break the architecture's quality guarantees.

1. **The orchestrator never writes application code.** It plans, dispatches subagents, reviews outputs, and decides. Code changes flow through subagents.
2. **The orchestrator owns the plan, not the code.** Its artifacts are `intent.md`, `plan.md`, `status.md`, `retro.json`, and the synthesis/revision instructions it issues to the synthesizer subagent. It reads code to review it; never writes code.
3. **The orchestrator gates quality, not creates it.** Review phases must result in APPROVED, MINOR_FIXES (dispatch fixer), or MAJOR_ISSUES (escalate). Never silently fix during review.
4. **Subagents edit, never overwrite existing files.** `Edit` for existing, `Write` for new.
5. **Subagents own specific files.** No two implement-phase subagents edit the same file.
6. **Circuit breakers are hard limits.** Escalate to user; do not retry silently. Do not increase limits without explicit user action.
7. **The R5 `spec-verifier` never receives the spec text.** This is a structural guarantee enforced by the agent definition (the agent flags spec leakage in `Concerns` rather than answering).
8. **The R2.1 iterative retrieval loop has a hard cap of 3 cycles.** Past 3, proceed with best-available findings and flag remaining gaps — do not loop indefinitely on terminology mismatch.
9. **The R3.2 interview has a hard cap of 5 questions.** Stop early when no high-impact gaps remain.
10. **The Phase-4 implementer never receives the test-writer's reasoning, and never edits test files.** The `block-mixed-commit` hook enforces that tests and implementation land in separate commits.

## Circuit breakers (consolidated)

| Where | Limit | On exhaustion |
|---|---|---|
| R2.1 iterative retrieval | 3 cycles | Proceed with best-available findings; flag gaps |
| R3.2 user interview | 5 questions | Proceed with what's answered |
| Phase 3 design check | 2 iterations | Escalate to user |
| Phase 4–6 code → review loop | 3 cycles | Escalate to user |
| Phase 5 QA fix loop | 3 iterations | Escalate to user |
| Phase 7 verify → review reject | 2 cycles | Escalate to user |
| Phase 4 commit hooks (`block-mixed-commit`, `check-leftover-stub`) | N/A (hard gate) | Reject commit; orchestrator must correct before retry |

## CLI surface

| Command | Purpose | Project-dir aware? |
|---|---|---|
| `ade init` | Generate `.claude/` + seed user-owned docs | Yes (`--project-dir`, default `.`) |
| `ade doctor` | Verify external tools, project state, list recommended plugins | Yes (`--project-dir`, default `.`) |
| `ade status` | List active tasks under `.ade/tasks/` | Yes (`--project-dir`, default `.`) |

`ade doctor` checks three categories:

1. **External tools** — `claude` (required), `git` (required), `pre-commit` (optional)
2. **Project state** — required ADE artifacts (agents, skills, vendored grill-with-docs, Research phase skill); user-owned bootstrap artifacts as WARN (may be intentionally removed)
3. **Recommended plugins** — informational hints for peer-installable plugins (e.g., `pr-review-toolkit`) with install commands

Exit codes: 0 on all-pass or warnings-only; 1 if any required check fails.
