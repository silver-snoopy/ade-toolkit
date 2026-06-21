# ADE Toolkit

## Project Overview

ADE (Agentic Development Environment) is a Python bootstrapper that scaffolds AI-driven SDLC skills and subagent definitions for Claude Code.

`ade init` generates `.claude/agents/`, `.claude/skills/ade/`, `.claude/commands/`, `.claude/hooks/`, stack/routing config, and seeds project documentation artifacts (`CONTEXT.md`, `docs/adr/`, `docs/specs/`, `docs/learnings/`) — everything Claude Code needs to run a structured **9-phase SDLC (Phases 0–9)** with Opus as orchestrator and Sonnet/Haiku as worker subagents. The pipeline features blast-radius routing (G4), author-separated TDD with a deterministic hook layer (G1/G2), and a compound learnings loop (G3).

## Architecture

- **No runtime framework** — no CrewAI, no Ollama, no custom agent runtime
- **Skills are Markdown** — `.claude/skills/ade/*.md` define the SDLC phases
- **Agents are Markdown** — `.claude/agents/*.md` define subagent roles and model assignments
- **The bootstrapper only scaffolds** — it doesn't run agents, execute code, or manage state
- **Claude Code IS the runtime** — subagents, worktrees, Edit/Write/Bash are all native
- **External skills are vendored with attribution** under `src/ade/templates/skills/vendored/` (currently `mattpocock-grill-with-docs`, MIT)

## Research phase (Phase 1) at a glance

The most rigorous part of the pipeline. Five sub-steps producing three permanent artifacts (spec, glossary entries, ADRs):

- **R1** Intent (from Phase 0)
- **R2** Investigate — R2.1 parallel scouts with iterative retrieval (max 3 cycles); R2.2 orchestrator confidence check; R2.3 conditional web research (Tier 0 by default)
- **R3** Specify — synthesizer drafts; orchestrator interviews user with 10-category ambiguity taxonomy (cap: 5 questions)
- **R4** Refine — vendored `grill-with-docs` against the spec
- **R5** Verify — Chain-of-Verification (factor+revise) with `spec-verifier` subagents that never see the spec

See [`docs/ade-architecture-design.md`](docs/ade-architecture-design.md) for the full architecture.

## Project Structure

```
ade-toolkit/
├── src/ade/
│   ├── cli.py                          # CLI: init, doctor, status
│   ├── detect.py                       # Project stack auto-detection
│   └── templates/
│       ├── agents/                     # 12 subagent definition templates
│       ├── skills/
│       │   ├── phases/                 # 10 per-phase skill templates (00-intent … 09-retro)
│       │   ├── ade-*.md.j2             # Composite workflow skills + feature-spec template
│       │   └── vendored/               # External skills with original LICENSE preserved
│       ├── commands/                   # Slash command templates
│       ├── hooks/                      # Deterministic commit hooks (block-mixed-commit, check-leftover-stub, check-escalation-paths, _hooklib)
│       ├── bootstrap/                  # User-owned seeds (CONTEXT.md, ADR-0001, specs/README, learnings/README, review-calibration)
│       ├── stack.md.j2                 # Seeds .claude/ade-stack.md (detected stack commands)
│       ├── ade-routing.json.j2         # Seeds .claude/ade-routing.json (routing tiers)
│       ├── claude_settings.json.j2     # Seeds/merges .claude/settings.json (hook wiring)
│       ├── claude_md_section.md.j2
│       └── ade_gitignore.j2
├── docs/
│   ├── ade-architecture-design.md      # Current architecture (this generation)
│   └── theme-metaphor-research.md      # Parking doc for future thread
├── tests/
└── pyproject.toml
```

## Development Commands

```bash
pip install -e ".[dev]"   # Install in dev mode
pytest                     # Run tests
ruff check src/ tests/     # Lint
ruff format src/ tests/    # Format
```

## Conventions

- Python 3.11+
- Ruff for linting and formatting (line-length 99)
- Type hints on all public functions
- Tests in `tests/` mirroring `src/` structure
- Conventional commits
- User-owned project artifacts (`CONTEXT.md`, `docs/adr/`, `docs/specs/`) are seeded once by `ade init` and never overwritten thereafter — see `_render_and_write_if_missing` in `cli.py`
