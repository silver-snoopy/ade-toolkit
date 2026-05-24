# ADE — Agentic Development Environment

A Python bootstrapper that scaffolds AI-driven SDLC skills and subagent definitions for [Claude Code](https://claude.com/claude-code).

`ade init` generates a `.claude/` tree with subagent definitions, skill files, slash commands, and bootstrap project documentation (`CONTEXT.md`, `docs/adr/`, `docs/specs/`). Claude Code is the runtime — ADE does not run agents, execute code, or manage state.

## What it generates

```
your-project/
├── .claude/
│   ├── agents/
│   │   ├── backend-coder.md        # Sonnet — backend implementation
│   │   ├── code-reviewer.md         # Sonnet — read-only logic review
│   │   ├── frontend-coder.md        # Sonnet — UI implementation
│   │   ├── scout.md                 # Haiku — codebase scope exploration
│   │   ├── security-reviewer.md     # Sonnet — OWASP review
│   │   ├── spec-verifier.md         # Sonnet — CoVe independent verifier
│   │   ├── synthesizer.md           # Sonnet — research consolidation + spec revision
│   │   ├── test-runner.md           # Haiku — build + tests
│   │   └── web-researcher.md        # Sonnet — grounded web research with citations
│   ├── skills/ade/
│   │   ├── ade-full.md              # Complete 10-phase cycle
│   │   ├── ade-plan.md              # Phases 0-2
│   │   ├── ade-code.md              # Phases 3-5
│   │   ├── ade-review.md            # Phases 6-8
│   │   ├── ade-ship.md              # Phases 9-10
│   │   ├── ade-status.md            # Task dashboard
│   │   ├── phases/                  # Per-phase detailed skill files
│   │   └── vendored/
│   │       └── mattpocock-grill-with-docs/   # MIT, attributed
│   └── commands/                    # Slash commands (/ade-full, /ade-plan, …)
├── .ade/
│   └── tasks/                       # Ephemeral per-task working state
├── docs/
│   ├── adr/                         # Architecture Decision Records
│   │   └── 0001-record-architecture-decisions.md
│   └── specs/                       # Permanent specs (one per task)
│       └── README.md
├── CONTEXT.md                       # Domain glossary (user-owned, ADE-seeded)
└── CLAUDE.md                        # ADE workflow section appended
```

`ade init` only seeds `CONTEXT.md`, `docs/adr/0001-…`, and `docs/specs/README.md` if they don't already exist. The rest of `.claude/` is regenerated on every init.

## Install

```bash
pip install ade-toolkit
```

## Quick start

```bash
cd your-project
ade init                # Scaffold ADE skills, agents, and bootstrap docs
ade doctor              # Verify prerequisites and project state
claude                  # Start Claude Code
/ade-full add auth      # Run the full 10-phase SDLC cycle
```

## The 10-phase SDLC

| Phase | Role | Model | Output |
|-------|------|-------|--------|
| 0. Intent | Orchestrator | Opus | `.ade/tasks/<id>/intent.md` |
| 1. Research | R1–R5 (see below) | Opus + Sonnet + Haiku | `docs/specs/{date}_{slug}.spec.md`, `CONTEXT.md` updates, `docs/adr/NNNN-*.md` |
| 2. Plan | Orchestrator | Opus | `.ade/tasks/<id>/plan.md` |
| 3. Design check | Subagent in worktree | Sonnet | Stubs |
| 4. Implement | 1–3 subagents in worktree | Sonnet | Code |
| 5. Quality gate | Subagent | Haiku | Lint, format, build, tests |
| 6. Review | `pr-review-toolkit` (preferred) or 3 parallel subagents (fallback) | Sonnet | Findings (Critical / Important / Suggestions / Positive) |
| 7. Verify | Orchestrator | Opus | Live evidence per acceptance criterion |
| 8. Docs | Subagent | Sonnet | Architecture / API / capabilities updates |
| 9. Ship | Orchestrator | Opus | Commit + PR |
| 10. Retro | Orchestrator | Opus | `.ade/tasks/<id>/retro.json`, worktree cleanup |

**Human gates** after R5 (ready-for-development), Phase 2 (plan), and Phase 9 (merge).

**Circuit breakers**: max 2 design iterations, max 3 code-review cycles, max 3 QA fixes, max 2 verify rejections, max 3 R2.1 retrieval cycles.

## Research phase (Phase 1) — five sub-steps

ADE's Research phase is the most rigorous part of the pipeline. It produces three artifacts that compound across tasks: the permanent spec, an updated domain glossary (`CONTEXT.md`), and zero or more ADRs.

- **R1 — Intent**: Phase 0 output (type, goal, acceptance criteria). Scope estimate is informational only — it does not route the phase.
- **R2 — Investigate**:
  - **R2.1 Code scouting (iterative retrieval, max 3 cycles)**. Two `scout` subagents in parallel — `current-state` + `available-surface`. Findings scored 0.0–1.0; stop criterion is ≥3 high-relevance (≥0.8) findings with no critical gaps and no terminology mismatch. If unmet, the orchestrator extracts vocabulary from cycle-1 results and re-dispatches.
  - **R2.2 Confidence check**. The orchestrator decides whether web research is needed, justifies the decision in writing, and skips R2.3 if scouts resolved all open questions internally.
  - **R2.3 Web research (conditional)**. One `web-researcher` subagent per topic, parallel. Tier 0 by default (WebSearch + WebFetch + Context7 MCP). Tier 1 (Tavily, Exa) only if env vars are set or user passes `--deep`. Citation invariants and prompt-injection trust tagging are enforced in the agent definition.
- **R3 — Specify**:
  - **R3.1** `synthesizer` consolidates research bundles into a draft spec (single-writer pattern).
  - **R3.2** Orchestrator interviews the user using a 10-category ambiguity taxonomy (Functional Scope, Data Model, UX Flow, Non-Functional, Integration, Edge Cases, Constraints, Terminology, Completion Signals, Misc). One question at a time, multi-choice with recommended + 1 alternative, **hard cap: 5 questions**. Spec written to `docs/specs/{YYYY-MM-DD}_{slug}.spec.md`.
- **R4 — Refine**: invokes the vendored `grill-with-docs` skill against the spec. Updates `CONTEXT.md` glossary inline; creates ADRs sparingly (three-criteria gate: hard-to-reverse, surprising, real trade-off). Always runs; trivial when the spec already uses CONTEXT.md vocabulary.
- **R5 — Verify (Chain of Verification, factor+revise)**: extract 8–15 verification claims from the spec; dispatch one `spec-verifier` subagent per claim. **Each verifier receives only the claim — never the spec itself** (the structural defining property of factor+revise). `synthesizer` (Role B) revises the spec for material discrepancies.

## Architecture

```
Claude Opus  (orchestrator)
├── Owns: intent, R2.2 confidence, R3.2 interview, R5 claim extraction, plan, review verdicts, verify, ship, retro
├── Dispatches: subagents for parallel work
└── Never: writes application code, edits the spec directly during R3.2 (uses Edit through user answers)

Claude Sonnet  (subagents)
├── web-researcher  (R2.3, IPI-hardened)
├── synthesizer     (R3.1 consolidation, R5 revision)
├── spec-verifier   (R5 — never receives the spec)
├── backend-coder / frontend-coder (Phase 4, in worktrees)
└── code-reviewer / security-reviewer (Phase 6 fallback)

Claude Haiku  (subagents)
├── scout         (R2.1, ~15 file reads, ~10k tokens, ~800-token summary)
└── test-runner   (Phase 5)
```

No runtime framework. Skills and agents are Markdown files. `ade init` writes them. Claude Code is the runtime — its native Agent tool dispatches subagents, native worktree support isolates implementation, native Edit/Write/Bash handle the work.

## Orchestrator invariants

1. The orchestrator **never writes application code** — only dispatches subagents.
2. The orchestrator **owns the plan, not the code** — reads code to review it.
3. The orchestrator **gates quality, not creates it** — dispatches fixes for findings; never silently fixes them.
4. Subagents **edit, never overwrite** existing files (Edit over Write).
5. Subagents **own specific files** — no two agents edit the same file in Phase 4.
6. **Circuit breakers are hard limits** — escalate to the user; do not retry silently.
7. The R5 `spec-verifier` **never sees the spec text** — this is a structural guarantee, not a prompt rule.

## Composition model

ADE vendors a small set of external skills into its template tree, with original LICENSE files preserved:

- `mattpocock-grill-with-docs` (MIT) — used in R4 for domain alignment, glossary, and ADR capture

ADE references peer-installable Claude Code plugins by name (graceful degradation: phase still works via inline fallback):

- `pr-review-toolkit` — preferred mechanism for Phase 6 multi-aspect review

Anthropic does not support declarative skill peer-dependencies, so ADE's distribution model is "scaffold self-contained, reference by name where peers exist."

## Prerequisites

- [Claude Code](https://claude.com/claude-code) CLI
- Git
- Python 3.11+ (for the bootstrapper only)

## CLI commands

| Command | What it does |
|---------|-------------|
| `ade init` | Scaffold ADE into current project (idempotent — preserves user-owned bootstrap files) |
| `ade doctor` | Check external tools, ADE project state, and recommended plugins |
| `ade status` | List active tasks under `.ade/tasks/` |

## License

MIT
