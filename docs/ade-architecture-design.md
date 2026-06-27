# ADE Architecture

This document describes ADE's current architecture: what `ade init` produces, how the resulting Claude Code installation runs the 9-phase SDLC, and the invariants that govern orchestration.

ADE is a *scaffolder*, not a runtime. The Python package writes skills, worker definitions, hook wiring, and documentation seeds into the target project, then exits. The selected harness (Claude Code, Gemini CLI, GitHub Copilot, or OpenAI Codex) is the runtime: subagent dispatch, worktree isolation, file I/O, and shell execution are all native to each harness.

See `docs/superpowers/specs/2026-06-21-platform-agnostic-ade-design.md` and `docs/adr/0003-platform-agnostic-skills-first.md` for the design rationale behind v3.

## Architecture at a glance

### Bootstrapper (ade-toolkit Python package)

```
src/ade/
├── cli.py              → init / migrate / eval / doctor / status
├── detect.py           → stack detection (unchanged)
├── eval.py             → static skill-quality checks (frontmatter, description cap)
└── harnesses/          → thin per-harness adapter layer
    ├── __init__.py     → TARGETS registry + selected_targets()
    ├── base.py         → HarnessTarget (frozen dataclass: skills_dirs, workers_dir, hook_substrate, …)
    ├── workers.py      → render_worker(target, env, name, ctx) → (relpath, content)
    ├── hooks.py        → emit_hooks(target, env, project_dir, ctx) — per-substrate wiring
    └── memory.py       → emit_memory_pointer(target, env, project_dir, ctx)
```

`ade init --agent <harness>` accepts `claude`, `gemini`, `copilot`, `codex`, a comma-separated list, or `all` (default `claude`).

### Generated output (target project after `ade init --agent all`)

```
.claude/
├── skills/            → phase skills (SKILL.md folders, shared with .agents/skills/)
├── agents/            → worker subagent definitions (14 × .md)
├── hooks/             → deterministic commit hooks + _hooklib.py (G1/G2/G4)
└── settings.json      → PreToolUse hook wiring (claude harness)

.gemini/
├── skills/            → phase skills (SKILL.md folders, shared with .agents/skills/)
├── agents/            → worker subagent definitions (14 × .md)
├── hooks/             → deterministic hooks (same scripts, gemini wiring)
└── settings.json      → PreToolUse hook wiring (gemini harness)

.github/
├── skills/            → phase skills (SKILL.md folders, shared with .agents/skills/)
├── agents/            → worker subagent definitions (14 × .agent.md)
├── hooks/             → deterministic hooks (copilot wiring)
└── copilot-instructions.md   → thin ADE memory pointer

.codex/
├── agents/            → worker subagent definitions (14 × .toml)
└── hooks/             → deterministic hooks (codex wiring, hooks.json / config.toml)

.agents/
└── skills/            → shared SKILL.md folders (Copilot + Gemini read this directly)
    ├── ade-intent/SKILL.md
    ├── ade-research/SKILL.md
    ├── ade-plan/SKILL.md
    ├── ade-design-check/SKILL.md
    ├── ade-implement/SKILL.md
    ├── ade-quality-gate/SKILL.md
    ├── ade-review/SKILL.md
    ├── ade-docs/SKILL.md
    ├── ade-ship/SKILL.md
    ├── ade-retro/SKILL.md
    ├── ade-pipeline/SKILL.md   → end-to-end driver (user-invoked; sequences Phases 0→9)
    ├── ade-pr-review/SKILL.md
    └── grill-with-docs/SKILL.md  → vendored (MIT, attributed)

.ade/
├── ade-routing.json   → blast-radius routing config, seed-if-missing (G4; user-owned)
├── ade-stack.md       → detected stack commands, seed-if-missing (user-owned)
├── .gitignore         → ignores .ade/tasks/ and .ade/worktrees/ (ephemeral state)
└── tasks/             → ephemeral per-task working state (gitignored)

AGENTS.md              → canonical harness-neutral instruction superset (ADE-generated)
CLAUDE.md              → thin ADE memory pointer (Claude harness)
GEMINI.md              → thin ADE memory pointer (Gemini harness)

docs/
├── adr/               → ADRs (sequential, immutable once accepted)
├── specs/             → permanent specs (one per task, date-prefixed filename)
├── learnings/         → compound-loop learnings sink (G3)
└── review-calibration.md → accreting review finding-class corpus (G3)

CONTEXT.md             → domain glossary (user-owned after seed)
```

## The 9-phase SDLC

| Phase | Purpose | Primary actor | Output |
|---|---|---|---|
| 0 — Intent | Extract structured requirements | Orchestrator | `.ade/tasks/<id>/intent.md` |
| 1 — Research | Produce verified durable spec | R1–R5 (see below) | `docs/specs/{date}_{slug}.spec.md`, `CONTEXT.md` updates, `docs/adr/NNNN-*.md` |
| 2 — Plan | Write implementation plan | Orchestrator | `.ade/tasks/<id>/plan.md` (6 mandatory sections) |
| 3 — Design check | Generate stubs in worktree, then blind-review them | Sonnet subagent (stubs) + `stub-reviewer` (blind) | Stub files matching plan; reviewer `APPROVE`/`REJECT` |
| 4 — Implement | Author-separated TDD: write failing tests then drive them to green | `test-writer` (RED) → `implementer` (GREEN) | Tests + code in worktree |
| 5 — Quality gate | Lint, format, build, tests | Haiku subagent | Pass/fail with fix loop (max 3) |
| 6 — Review | Multi-aspect code review | `pr-review-toolkit` (preferred) or 3 parallel Sonnet subagents (fallback) | Findings table (Critical / Important / Suggestions / Positive) |
| 7 — Docs | Update affected documentation | Sonnet subagent | Architecture / API / capabilities updates |
| 8 — Ship | Commit, push, PR | Orchestrator | PR URL |
| 9 — Retro | Metrics + cleanup | Orchestrator | `.ade/tasks/<id>/retro.json` |

Human gates: after R5 (ready-for-development), after Phase 2 (plan completeness), after Phase 8 (merge decision). For `architecture`-routed tasks, an additional confirmation gate follows Phase-0 routing.

## Blast-radius routing (G4)

The closing sub-step of Phase 0 assigns a **tier** that masks which phases run:

- **trivial** — tiny self-contained change: lightweight inline research, no design-check,
  single review pass, no retro — but always author-separated TDD, the deterministic quality
  gate, and the merge gate.
- **standard** — the full nine-phase flow (default), including a lightweight Plan Soundness
  Review (fresh-context coverage matrix) before code.
- **architecture** — standard + ≥1 ADR + a full adversarial Plan Soundness Review (refutation)
  before code.

**Hybrid classifier.** The orchestrator judges trivial-vs-standard from the intent; a
deterministic rule set decides **forced-escalation** — security/auth/secrets/crypto/
data-loss force a floor of `standard`, and schema/migrations/public-API/ADR-or-model force
`architecture`, regardless of estimated size. Rules + globs live in the user-owned
`.ade/ade-routing.json`.

**Two-layer enforcement.** Phase 0 applies the rules to the *declared* affected areas (no
diff exists yet). The `check-escalation-paths` commit hook re-checks the *actual* diff at
Ship time against a hardcoded baseline (which config can only extend) — the non-evadable
guarantee, scoped to ADE-routed tasks (`ade/<task-id>` branches). See
`docs/adr/0001-hybrid-blast-radius-routing-classifier.md`.

The Phase-0 S/M/L scope estimate now *feeds* the router rather than being purely
informational.

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

#### R3.3 — Threat pass (conditional)

A fast, single-shot, static, read-only design-time security + privacy pass, inserted between the R3.2 interview and the R4 grill. **It runs only when the change warrants it** — when the Phase-0 routing tier is `architecture`, when a forced-escalation fired (the `security` or new `data_classification` category), or when the orchestrator conservatively judges a new trust boundary. A `standard`-by-size change (no escalation) and `trivial` skip it — no security theater on a rename.

The orchestrator dispatches one blind `threat-modeler` (sonnet, read-only), passing the draft spec + affected code but **withholding its design reasoning** (the same blind-reviewer guarantee as the R5 `spec-verifier`). The worker runs Shostack's four questions over the change's delta; for each trust boundary it classifies the cross-boundary data (four sensitivity tiers — `public | internal | confidential | restricted` — plus an orthogonal `PII` flag), elicits STRIDE-lite + abuse-case threats (plus a Linking/Identifying/Data-Disclosure/Unawareness privacy prompt for PII-flagged boundaries), and assigns each a mitigation or an accepted residual risk. A hard no-boilerplate guardrail drops any generic, change-agnostic threat.

The orchestrator (single writer) records the pass to `.ade/tasks/<id>/threat-model.md` and folds the verdict into the spec: material mitigations become acceptance criteria (rides Phase-4 TDD + the Phase-6 security lens — no new phase), trust-boundary decisions become ADRs, and accepted residual risks land in an "Accepted residual risks" section surfaced at the ready-for-development gate. The method and its grounding are in ADR-0005 and `docs/research/threat-modeling-frameworks-2026-06.md`.

### R4 — Refine (grill-with-docs)

Invoke the vendored `grill-with-docs` skill against the spec. Skill location: `.claude/skills/grill-with-docs/SKILL.md` (also under `.agents/skills/grill-with-docs/SKILL.md` for multi-harness projects).

Phase-prompt framing wraps the skill so the spec is treated as the "plan" the skill grills, with explicit instructions to revise the spec inline alongside the skill's native side effects (CONTEXT.md updates, ADR drafts).

`grill-with-docs` outputs:

- **CONTEXT.md updates** — incrementally, inline. Glossary entries follow the format in `grill-with-docs/CONTEXT-FORMAT.md`.
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

## Phases 2–9 (current state)

These phases retain the structure that predates the v5 Research rewrite. They are functional and produce useful work, but they would benefit from the same rigor pass applied to Phase 1. A future thread will rework them.

- **Phase 2 — Plan**: 6 mandatory sections (Context, Ordered task list, Files, Dependencies, Test strategy, Risk areas). Primary input: the spec from R5.
- **Phase 3 — Design check**: Subagent in worktree generates file stubs from plan; a blind
  `stub-reviewer` (sees spec + plan + stubs, never the author's reasoning) then rejects
  wrong-but-compiling contracts. Standard + architecture tiers. Max 2 iterations (shared).
- **Phase 4 — Implement**: Author-separated TDD. Phase 4a: `test-writer` writes failing tests covering the plan's acceptance criteria and commits them alone (RED). Phase 4b: one or more `implementer` subagents (disjoint file assignments) drive those tests to GREEN, never editing test files. Build dependencies before dependents (the task DAG defines order). The `block-mixed-commit` hook enforces the commit boundary between phases.
- **Phase 5 — Quality gate**: Lint, format, build, tests. Fix loop max 3.
- **Phase 6 — Review**: `pr-review-toolkit` preferred; fallback is 3 parallel subagents (Logic / Conventions / Security). Findings classified Critical / Important / Suggestions / Positive. Review-fix cycle max 3.
- **Phase 7 — Docs**: Architecture, capabilities, API docs, CLAUDE.md updates.
- **Phase 8 — Ship**: Commit, push, open PR. Human gate.
- **Phase 9 — Retro**: Metrics, learnings, worktree cleanup.

## Stack configuration (`.ade/ade-stack.md`)

`ade init` detects each language's build/lint/format/test commands and seeds them into
`.ade/ade-stack.md` (seed-if-missing, user-owned thereafter). Phase skills reference
this file generically rather than hardcoding commands, which is what makes the pipeline
stack-neutral. Three slot states keep it honest: a real command; `none` for a
known-language slot that does not apply (e.g. python has no build), which phases skip; and
`# set your <slot> command` for an unknown/undetected stack, which the user fills in. The
orchestrator reads the file and injects the concrete command into each subagent's dispatch
prompt; for a multi-language change it runs the block for each changed language.

The routing config (`.ade/ade-routing.json`) and stack config (`.ade/ade-stack.md`) are
both emitted to `.ade/` (v3 layout). `ade migrate` moves them from the v2 `.claude/`
location, preserving any user edits.

## Deterministic hook layer (G2)

Three Python scripts committed under `.claude/hooks/` act as a hard gate on commit integrity. Because they live inside the repository (not in gitignored `.ade/`), they are present inside every git worktree without any extra setup step.

### Checks

- **`block-mixed-commit.py`** — rejects any commit that contains both test files and non-test source files in the same changeset. This enforces the Phase 4a/4b author separation at the VCS level. Bypass: include `[test-refactor]` in the commit message for the narrow case of a refactor that must touch both together.
- **`check-leftover-stub.py`** — rejects committed non-test source files that still contain stub markers (`NotImplementedError`, `TODO: implement`, or `Not implemented`). This prevents stubs from being accidentally shipped as real implementation.
- **`check-escalation-paths.py`** — for an ADE-routed task (`ade/<task-id>` branch), rejects
  a commit whose diff touches escalation paths (security/auth/secrets, schema/migrations,
  public-API) below the task's routed floor. Baseline globs are compiled in;
  `.ade/ade-routing.json` may only extend them. No-op off an `ade/*` branch.

All three scripts share common detection logic via `_hooklib.py` (also in `.claude/hooks/`), so they work identically regardless of which substrate wires them.

### Scope and boundaries

These hooks fire on the harness's PreToolUse(Bash) path, so they gate commits made by an
ADE-driven agent session — not every commit reaching the repository. Two limits are worth
stating plainly:

- **`check-escalation-paths` is scoped to ADE-routed branches.** It enforces the blast-radius
  floor only when a task is on an `ade/<task-id>` branch with a recorded routing tier; it
  no-ops on direct-to-main commits, non-ADE branches, and any commit made outside an ADE
  agent session. This is a deliberate boundary (the floor is meaningless without a routed
  tier), not a guarantee that escalation paths are protected repository-wide.
- **`block-mixed-commit` and `check-leftover-stub` are unconditional within an ADE session**
  but, like all PreToolUse hooks, only run for commits issued through the wired harness.

To extend any of these into a repository-wide policy that also covers human commits, CI, and
non-ADE tooling, wire the same scripts as a `git pre-commit` hook (the
`.pre-commit-config.yaml` fallback) or a server-side check — the PreToolUse wiring alone does
not cover those paths.

### Wiring — native PreToolUse hooks on all four harnesses

All four harnesses ship native PreToolUse (blocking) hooks, all consuming the same JSON-over-stdin contract that ADE's `_hooklib` already uses. `ade init` wires the three hook scripts into each selected harness's native hook system via the `harnesses/hooks.py` adapter:

- **`--agent claude`** (default): writes `.claude/settings.json` with PreToolUse(Bash) entries.
- **`--agent gemini`**: writes `.gemini/settings.json` with PreToolUse(Bash) entries.
- **`--agent copilot`**: writes `.github/hooks/*.json` (`preToolUse` deny entries). `_hooklib` handles Copilot's camelCase field names via the per-harness envelope parser.
- **`--agent codex`**: writes `hooks.json` / `[hooks]` in `config.toml` under `.codex/hooks/`. Current Codex releases support explicit subagent workflows and project-scoped custom agents, so Codex should no longer be described as intrinsically degraded. ADE still needs parity tests and procedural verification that its phase prompts spawn the intended Codex custom agents rather than falling back to in-context conventions; Codex's native PreToolUse hooks continue to enforce the hard gates (G1/G2/G4).

`git pre-commit` (`.pre-commit-config.yaml`) is demoted to an **optional belt-and-suspenders fallback** for non-ADE commits or CI, not the primary gate.

### Failure behavior

All three hooks are a **hard gate**: a violation rejects the commit with a human-readable explanation. The orchestrator does not retry past a hook failure — the violation must be corrected before the commit is retried.

## Subagent catalog

All subagents are defined as Markdown files under `.claude/agents/` with YAML frontmatter declaring model and tool surface.

| Agent | Model | Tools | Used in |
|---|---|---|---|
| `scout` | haiku | Read, Grep, Glob, Bash | R2.1 |
| `web-researcher` | sonnet | WebSearch, WebFetch, Read | R2.3 |
| `synthesizer` | sonnet | Read, Write | R3.1, R5.3 |
| `spec-verifier` | sonnet | Read, Grep, Glob | R5.2 |
| `test-writer` | sonnet | Read, Write, Edit, Bash, Glob, Grep | Phase 4a |
| `implementer` | sonnet | Read, Write, Edit, Bash, Glob, Grep | Phase 4b |
| `code-reviewer` | sonnet | Read, Glob, Grep | Phase 6 fallback |
| `security-reviewer` | sonnet | Read, Glob, Grep | Phase 6 fallback |
| `test-runner` | haiku | Read, Bash | Phase 5 |
| `plan-reviewer` | sonnet | Read, Grep, Glob | Phase 2 (standard: coverage matrix; architecture: full refutation) |
| `stub-reviewer` | sonnet | Read, Grep, Glob | Phase 3 (blind stub review, standard + architecture) |
| `threat-modeler` | sonnet | Read, Grep, Glob | R3.3 (blind threat pass, conditional) |
| `pr-reviewer` | sonnet | Read, Grep, Glob, Bash | `ade-pr-review` skill (GitHub PR loop) |
| `compounder` | sonnet | Read, Grep, Glob | Phase 9 (Codify) |

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
| `docs/specs/{date}_{slug}.spec.md` | R3.1 + R3.2 + R4 + R5.3 | Phase 2 | **Permanent (versioned)** |
| `CONTEXT.md` | `grill-with-docs` (R4) inline | All subsequent phases, future tasks | **Permanent (additive)** |
| `docs/adr/NNNN-*.md` | `grill-with-docs` (R4) sparingly | Future tasks (reference) | **Permanent (immutable once accepted)** |
| `.ade/tasks/<id>/plan.md` | Phase 2 | Phases 3–8 | Ephemeral |
| `.ade/tasks/<id>/status.md` | All phases (orchestrator updates) | `ade status` | Ephemeral |
| `.ade/tasks/<id>/retro.json` | Phase 9 | (reference, future calibration) | Ephemeral |

The line between ephemeral and permanent maps to ownership: `.ade/tasks/` is per-task working state, gitignored. `docs/` is project-owned, version-controlled, durable.

## Composition model

Anthropic does not support declarative peer-dependencies for Claude Code skills ([anthropics/claude-code#27113](https://github.com/anthropics/claude-code/issues/27113), closed as not planned). ADE's distribution model is shaped by that constraint:

- **Vendor with attribution** for skills ADE depends on structurally. Source files are in `src/ade/templates/skills/grill-with-docs/`, original LICENSE preserved, vendoring source noted. Currently vendored:
  - `grill-with-docs` (MIT, copyright 2026 Matt Pocock) — used in R4 for domain alignment, glossary, and ADR capture
- **Reference by name** for plugins that improve quality but aren't structurally required. ADE phase prompts use a "preferred mechanism + native fallback" pattern. The phase still works without the plugin installed; quality is lower. Currently referenced:
  - `pr-review-toolkit` (Phase 6 multi-aspect review)

Vendored skills resolve identically to user-installed plugin skills at runtime — each harness walks its skills directories (including `.agents/skills/`) for SKILL.md discovery, so the location doesn't affect resolution.

## Bootstrap and `ade init` lifecycle

`ade init` is idempotent and divides outputs into two categories by ownership:

**ADE-owned (regenerated every init)**:
- Per-harness skills dirs (`<harness>/skills/<skill>/SKILL.md`)
- Shared skills dir (`.agents/skills/<skill>/SKILL.md`)
- Per-harness worker defs (`<harness>/agents/<worker>.md|.agent.md|.toml`)
- Per-harness hook wiring (`<harness>/settings.json` or hooks config)
- Hook scripts (`<harness>/hooks/*.py`)
- `AGENTS.md` (root canonical instruction file)
- Per-harness memory pointers (thin ADE block in `CLAUDE.md`, `GEMINI.md`, etc.)
- `.ade/.gitignore`

**User-owned (seeded once, never overwritten)**:
- `CONTEXT.md`
- `docs/adr/0001-record-architecture-decisions.md`
- `docs/specs/README.md`
- `docs/learnings/README.md`
- `docs/review-calibration.md`
- `.ade/ade-routing.json`
- `.ade/ade-stack.md`

The CLI helper `_render_and_write_if_missing` enforces the user-owned contract: if the destination already exists, the file is preserved verbatim. Second-init output marks these as `= Kept existing <path>` rather than `+ Created <path>`.

**`ade migrate`** (idempotent) upgrades a v2 ADE tree to v3: moves `.claude/ade-routing.json` and `.claude/ade-stack.md` to `.ade/`, removes stale `.claude/skills/ade/` and `.claude/commands/`, strips the old CLAUDE.md ADE heading, then runs the full v3 emission.

**`ade eval`** statically checks all generated skills under `.claude/skills/` and `.agents/skills/` for missing YAML frontmatter and oversized descriptions (Codex's 8 KB discovery-list cap, ≤350 characters per skill). Exits 0 on PASS, 1 if any errors.

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
| Phase 4 commit hooks (`block-mixed-commit`, `check-leftover-stub`) | N/A (hard gate) | Reject commit; orchestrator must correct before retry |
| Plan Soundness Review (architecture, full refutation) | 2 iterations | Escalate to user |
| Plan Soundness Review (standard, coverage matrix) | 1 iteration | Escalate to user |

## CLI surface

| Command | Purpose | Project-dir aware? |
|---|---|---|
| `ade init` | Generate per-harness trees + seed user-owned docs (`--agent` list or `all`) | Yes (`--project-dir`, default `.`) |
| `ade migrate` | Upgrade a v2 ADE tree to the v3 layout (idempotent) | Yes (`--project-dir`, default `.`) |
| `ade eval` | Statically check generated skills (frontmatter, description cap) | Yes (`--project-dir`, default `.`) |
| `ade doctor` | Verify external tools, project state, list recommended plugins | Yes (`--project-dir`, default `.`) |
| `ade status` | List active tasks under `.ade/tasks/` | Yes (`--project-dir`, default `.`) |

`ade doctor` checks three categories:

1. **External tools** — `claude` (required), `git` (required), `pre-commit` (optional)
2. **Project state** — required ADE artifacts (agents, skills, vendored grill-with-docs, Research phase skill); user-owned bootstrap artifacts as WARN (may be intentionally removed)
3. **Recommended plugins** — informational hints for peer-installable plugins (e.g., `pr-review-toolkit`) with install commands

Exit codes: 0 on all-pass or warnings-only; 1 if any required check fails.
