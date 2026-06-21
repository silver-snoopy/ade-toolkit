# ADE — Agentic Development Environment

A Python bootstrapper that scaffolds AI-driven SDLC skills and subagent definitions for [Claude Code](https://claude.com/claude-code).

`ade init` generates a `.claude/` tree — subagent definitions, skill files, slash commands, deterministic commit hooks, stack/routing config — plus bootstrap project documentation (`CONTEXT.md`, `docs/adr/`, `docs/specs/`, `docs/learnings/`). Claude Code is the runtime — ADE does not run agents, execute code, or manage state.

The pipeline runs a **9-phase SDLC (Phases 0–9)** with Opus as orchestrator and Sonnet/Haiku worker subagents. Its signature properties: blast-radius **routing** that scales ceremony to change size, **author-separated TDD** (the agent that writes the tests is never the one that writes the code), a **deterministic hook layer** that gates commit integrity off the model loop, and a **compound loop** that codifies each task's learnings for the next one.

## What it generates

```
your-project/
├── .claude/
│   ├── agents/                        # 12 subagent definitions (model + tools in frontmatter)
│   │   ├── scout.md                   # Haiku  — codebase scouting (R2.1)
│   │   ├── web-researcher.md          # Sonnet — grounded web research, IPI-hardened (R2.3)
│   │   ├── synthesizer.md             # Sonnet — spec draft + CoVe revision (R3.1, R5)
│   │   ├── spec-verifier.md           # Sonnet — CoVe verifier, never sees the spec (R5)
│   │   ├── test-writer.md             # Sonnet — writes FAILING tests only (Phase 4a)
│   │   ├── implementer.md             # Sonnet — language-agnostic impl, never edits tests (Phase 4b)
│   │   ├── plan-reviewer.md           # Sonnet — adversarial plan review (architecture tier)
│   │   ├── code-reviewer.md           # Sonnet — logic / correctness review (Phase 6 fallback)
│   │   ├── security-reviewer.md       # Sonnet — OWASP review (Phase 6 fallback)
│   │   ├── pr-reviewer.md             # Sonnet — GitHub PR review-and-fix loop (/ade-pr-review)
│   │   ├── test-runner.md             # Haiku  — build + tests (Phase 5)
│   │   └── compounder.md              # Sonnet — Codify: learnings + calibration (Phase 9)
│   ├── skills/ade/
│   │   ├── ade-full.md                # Complete cycle, Phases 0–9
│   │   ├── ade-plan.md                # Phases 0–2 (Intent + Research + Plan)
│   │   ├── ade-code.md                # Phases 3–5 (Design + Implement + Quality gate)
│   │   ├── ade-review.md              # Phases 6–7 (Review + Docs)
│   │   ├── ade-ship.md                # Phases 8–9 (Ship + Retro)
│   │   ├── ade-pr-review.md           # GitHub PR review-and-fix loop
│   │   ├── ade-status.md              # Task dashboard
│   │   ├── feature-spec.md            # Spec template
│   │   ├── phases/                    # 10 per-phase skill files (00-intent … 09-retro)
│   │   └── vendored/
│   │       └── mattpocock-grill-with-docs/   # MIT, attributed
│   ├── commands/                      # Slash commands (/ade-full, /ade-plan, /ade-pr-review, …)
│   ├── hooks/                         # Deterministic commit-integrity hooks (Python)
│   │   ├── block-mixed-commit.py      # blocks commits mixing tests + impl (Phase 4)
│   │   ├── check-leftover-stub.py     # blocks shipped stub markers
│   │   ├── check-escalation-paths.py  # blocks commits above the routed tier's floor
│   │   └── _hooklib.py                # shared detection logic
│   ├── settings.json                  # PreToolUse hook wiring (--agent claude)
│   ├── ade-stack.md                   # Detected stack commands (build/lint/format/test) — seeded
│   └── ade-routing.json               # Blast-radius routing config — seeded
├── .ade/
│   └── tasks/                         # Ephemeral per-task working state
├── docs/
│   ├── adr/0001-record-architecture-decisions.md   # Architecture Decision Records
│   ├── specs/README.md                # Permanent specs (one per task)
│   ├── learnings/README.md            # Compound-loop learnings sink
│   └── review-calibration.md          # Accreting review finding-class corpus
├── CONTEXT.md                         # Domain glossary (user-owned, ADE-seeded)
└── CLAUDE.md                          # ADE workflow section appended
```

`ade init` only **seeds if missing** the user-owned artifacts (`CONTEXT.md`, `docs/adr/0001-…`, `docs/specs/README.md`, `docs/learnings/README.md`, `docs/review-calibration.md`, `.claude/ade-stack.md`, `.claude/ade-routing.json`). The rest of `.claude/` is regenerated on every init. With `--agent copilot`, hooks are wired through a `.pre-commit-config.yaml` instead of `.claude/settings.json`.

## Install

```bash
pip install ade-toolkit
```

## Quick start

```bash
cd your-project
ade init                # Scaffold ADE skills, agents, hooks, and bootstrap docs
ade doctor              # Verify prerequisites and project state
claude                  # Start Claude Code
/ade-full add auth      # Run the full 9-phase SDLC cycle
```

## The 9-phase SDLC

| Phase | Actor | Model | Output |
|-------|-------|-------|--------|
| 0. Intent **(+ route)** | Orchestrator | Opus | `.ade/tasks/<id>/intent.md`, `routing.md` (tier) |
| 1. Research | R1–R5 (see below) | Opus + Sonnet + Haiku | `docs/specs/{date}_{slug}.spec.md`, `CONTEXT.md` updates, `docs/adr/NNNN-*.md` |
| 2. Plan | Orchestrator (+ `plan-reviewer` on architecture tier) | Opus (+ Sonnet) | `.ade/tasks/<id>/plan.md` (6 sections) |
| 3. Design check *(skipped for `trivial`)* | Subagent in worktree | Sonnet | Stubs matching the plan |
| 4. Implement **(author-separated TDD)** | `test-writer` (RED) → `implementer`(s) (GREEN) | Sonnet | Failing tests, then code — committed separately, hook-enforced |
| 5. Quality gate | `test-runner` | Haiku | Lint, format, build, tests (fix loop max 3) |
| 6. Review | `pr-review-toolkit` (preferred) or parallel reviewers (fallback) | Sonnet | Findings (Critical / Important / Suggestions / Positive) + acceptance-coverage gate |
| 7. Docs *(required on architecture tier)* | Subagent | Sonnet | Architecture / API / capabilities updates |
| 8. Ship | Orchestrator | Opus | Commit + PR |
| 9. Retro **(+ Codify)** | Orchestrator + `compounder` | Opus + Sonnet | `retro.json`, `docs/learnings/`, `docs/review-calibration.md`, worktree cleanup |

**Human gates** after R5 (ready-for-development), Phase 2 (plan), and Phase 8 (merge). On the `architecture` tier, an additional confirmation gate follows Phase-0 routing.

**Circuit breakers**: max 3 R2.1 retrieval cycles, max 2 design iterations, max 3 quality-gate fixes, max 3 review-fix cycles. Every loop escalates to the user on exhaustion — never a silent retry.

## Blast-radius routing

The closing sub-step of Phase 0 assigns a **tier** that masks which phases run, so a one-line change doesn't pay for the full ceremony:

- **`trivial`** — skips Design check (Phase 3) and Codify (Phase 9); Review collapses to a single quick pass.
- **`standard`** — the full flow (default).
- **`architecture`** — adds a Plan Soundness Review (`plan-reviewer`) before any code, requires an ADR, and forces a confirmation gate after routing.

Routing is hybrid: the orchestrator judges trivial-vs-standard within a free band, but **forced-escalation rules in `.claude/ade-routing.json` always win** — security / auth / secrets / crypto / data-loss floor at `standard`; schema / migration / public-API / model changes floor at `architecture`; an unparseable config is treated as `≥ standard`. The `check-escalation-paths` hook is a deterministic Ship-time backstop against the real diff.

## Research phase (Phase 1) — five sub-steps

ADE's Research phase is the most rigorous part of the pipeline. It produces three artifacts that compound across tasks: the permanent spec, an updated domain glossary (`CONTEXT.md`), and zero or more ADRs.

- **R1 — Intent**: Phase 0 output (type, goal, acceptance criteria). The S/M/L scope estimate now *feeds the router* but does not gate Phase 1 itself.
- **R2 — Investigate**:
  - **R2.1 Code scouting (iterative retrieval, max 3 cycles)**. Two `scout` subagents in parallel — `current-state` + `available-surface`. Findings scored 0.0–1.0; stop criterion is ≥3 high-relevance (≥0.8) findings with no critical gaps and no terminology mismatch. If unmet, the orchestrator extracts vocabulary from cycle-1 results and re-dispatches. Scouts also grep `docs/learnings/` for prior discoveries (the compound loop, read side).
  - **R2.2 Confidence check**. The orchestrator decides whether web research is needed, justifies the decision in writing, and skips R2.3 if scouts resolved all open questions internally.
  - **R2.3 Web research (conditional)**. One `web-researcher` subagent per topic, parallel. Tier 0 by default (WebSearch + WebFetch + Context7 MCP). Tier 1 (Tavily, Exa) only if env vars are set or the user passes `--deep`. Citation invariants and prompt-injection trust tagging are enforced in the agent definition.
- **R3 — Specify**:
  - **R3.1** `synthesizer` consolidates research bundles into a draft spec (single-writer pattern).
  - **R3.2** Orchestrator interviews the user using a 10-category ambiguity taxonomy (Functional Scope, Data Model, UX Flow, Non-Functional, Integration, Edge Cases, Constraints, Terminology, Completion Signals, Misc). One question at a time, multi-choice with recommended + 1 alternative, **hard cap: 5 questions**. Spec written to `docs/specs/{YYYY-MM-DD}_{slug}.spec.md`.
- **R4 — Refine**: invokes the vendored `grill-with-docs` skill against the spec. Updates `CONTEXT.md` glossary inline; creates ADRs sparingly (three-criteria gate: hard-to-reverse, surprising, real trade-off). Always runs; trivial when the spec already uses CONTEXT.md vocabulary.
- **R5 — Verify (Chain of Verification, factor+revise)**: extract 8–15 verification claims from the spec; dispatch one `spec-verifier` subagent per claim. **Each verifier receives only the claim — never the spec itself** (the structural defining property of factor+revise). `synthesizer` (Role B) revises the spec for material discrepancies.

## Author-separated TDD + deterministic hooks

Phase 4 splits implementation across two structurally distinct agents:

1. **`test-writer`** writes one failing test per automatable acceptance criterion and commits them alone (`test:`).
2. One or more **`implementer`** subagents (disjoint file assignments) drive those tests to green and commit alone (`feat:`/`fix:`). The orchestrator does **not** pass the test-writer's reasoning to the implementer, and the implementer is forbidden from editing test files.

Three Python hooks under `.claude/hooks/` (sharing `_hooklib.py`) enforce this off the model loop — wired as PreToolUse(Bash) under `--agent claude`, or as git pre-commit hooks under `--agent copilot`:

- **`block-mixed-commit.py`** — rejects a commit containing both test and non-test source files (bypass: `[test-refactor]` in the message). Makes the Phase 4a/4b separation a hard VCS-level guarantee.
- **`check-leftover-stub.py`** — rejects committed non-test source still containing stub markers (`NotImplementedError`, `TODO: implement`, `Not implemented`).
- **`check-escalation-paths.py`** — on an `ade/<task-id>` branch, rejects a commit whose diff touches escalation paths below the task's routed floor. Baseline globs are compiled in; `ade-routing.json` may only extend them. No-op off an `ade/*` branch.

## Compound loop

Each task deposits durable, reloadable knowledge so the next one is cheaper (recorded in ADR 0002 as a passive, non-gating loop):

- **Phase 9 / Codify** dispatches the read-only `compounder` subagent, which writes a per-task discovery to `docs/learnings/` and merges recurring finding-classes into `docs/review-calibration.md` (with a frequency metric that re-orders, but never promotes, severity).
- **Phase 1 / R2.1** scouts read `docs/learnings/` back; **Phase 6** reviewers read `docs/review-calibration.md` fresh to prioritize their attention. The metric tunes the review gate without gating it.

## Architecture

```
Claude Opus  (orchestrator)
├── Owns: intent + routing, R2.2 confidence, R3.2 interview, R5 claim extraction,
│         plan, review verdicts, ship, retro
├── Dispatches: subagents for parallel work
└── Never: writes application code; edits the spec directly during R3.2

Claude Sonnet  (subagents)
├── web-researcher   (R2.3, IPI-hardened)
├── synthesizer      (R3.1 consolidation, R5 revision)
├── spec-verifier    (R5 — never receives the spec)
├── plan-reviewer    (Phase 2, architecture tier)
├── test-writer      (Phase 4a — failing tests only)
├── implementer      (Phase 4b — code only, in worktrees)
├── code-reviewer / security-reviewer (Phase 6 fallback)
├── pr-reviewer      (/ade-pr-review GitHub loop)
└── compounder       (Phase 9 Codify, read-only)

Claude Haiku  (subagents)
├── scout            (R2.1, ~15 file reads, ~10k tokens, ~800-token summary)
└── test-runner      (Phase 5)
```

No runtime framework. Skills and agents are Markdown files. `ade init` writes them. Claude Code is the runtime — its native Agent tool dispatches subagents, native worktree support isolates implementation, native Edit/Write/Bash handle the work, and native hooks enforce the deterministic gates.

## Orchestrator invariants

1. The orchestrator **never writes application code** — only dispatches subagents.
2. The orchestrator **owns the plan, not the code** — reads code to review it.
3. The orchestrator **gates quality, not creates it** — dispatches fixes for findings; never silently fixes them.
4. Subagents **edit, never overwrite** existing files (Edit over Write).
5. Subagents **own specific files** — no two agents edit the same file in Phase 4.
6. **Circuit breakers are hard limits** — escalate to the user; do not retry silently.
7. The R5 `spec-verifier` **never sees the spec text** — a structural guarantee, not a prompt rule.
8. The **`test-writer` and `implementer` are distinct agents** — author separation is enforced by `block-mixed-commit`, not by convention.

## Composition model

ADE vendors a small set of external skills into its template tree, with original LICENSE files preserved:

- `mattpocock-grill-with-docs` (MIT) — used in R4 for domain alignment, glossary, and ADR capture

ADE references peer-installable Claude Code plugins by name (graceful degradation: the phase still works via inline fallback):

- `pr-review-toolkit` — preferred mechanism for Phase 6 multi-aspect review

Anthropic does not support declarative skill peer-dependencies, so ADE's distribution model is "scaffold self-contained, reference by name where peers exist."

## Prerequisites

- [Claude Code](https://claude.com/claude-code) CLI
- Git
- Python 3.11+ (for the bootstrapper only)
- `pre-commit` (optional — only for `ade init --agent copilot`)

## CLI commands

| Command | What it does |
|---------|-------------|
| `ade init` | Scaffold ADE into the current project (idempotent — preserves user-owned bootstrap files). Use `--agent {claude,copilot}` to choose the hook substrate (default `claude`). |
| `ade doctor` | Check external tools, ADE project state, and recommended plugins |
| `ade status` | List active tasks under `.ade/tasks/` |

## License

MIT
