# ADE Toolkit

## Project Overview

ADE (Agentic Development Environment) is a Python bootstrapper that scaffolds AI-driven SDLC skills and subagent definitions for Claude Code, Gemini CLI, GitHub Copilot, and OpenAI Codex.

`ade init --agent <harness>` generates per-harness skills trees (one `SKILL.md` per phase + `ade-pipeline` driver), worker subagent definitions, deterministic hook wiring, the shared `AGENTS.md` root instruction file, `.ade/` user-config, and seeds project documentation artifacts (`CONTEXT.md`, `docs/adr/`, `docs/specs/`, `docs/learnings/`) — everything needed to run a structured **9-phase SDLC (Phases 0–9)** across all four harnesses. The pipeline features blast-radius routing (G4), author-separated TDD with a deterministic hook layer (G1/G2), and a compound learnings loop (G3). `--agent` accepts `claude`, `gemini`, `copilot`, `codex`, a comma-separated list, or `all` (default: `claude`).

## Architecture

- **No runtime framework** — no CrewAI, no Ollama, no custom agent runtime
- **Skills are Markdown** — one `<skill>/SKILL.md` folder per phase, emitted to each harness's skills directory (and the shared `.agents/skills/`)
- **Workers are Markdown (or TOML for Codex)** — per-harness worker subagent definitions (`.md` / `.agent.md` / `.toml`) carry model + tool assignments and live in each harness's workers directory
- **The bootstrapper only scaffolds** — it doesn't run agents, execute code, or manage state
- **Each harness IS the runtime** — Claude Code, Gemini CLI, Copilot, or Codex dispatches subagents, handles worktree isolation, and runs file I/O natively
- **External skills are vendored with attribution** under `src/ade/templates/skills/grill-with-docs/` (currently `grill-with-docs`, MIT)

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
│   ├── cli.py                          # CLI: init, migrate, eval, doctor, status
│   ├── detect.py                       # Project stack auto-detection
│   ├── eval.py                         # Static skill-quality checks (frontmatter, description cap)
│   ├── harnesses/                      # Thin per-harness adapter layer
│   │   ├── __init__.py                 # TARGETS registry + selected_targets()
│   │   ├── base.py                     # HarnessTarget frozen dataclass
│   │   ├── workers.py                  # render_worker() → (relpath, content)
│   │   ├── hooks.py                    # emit_hooks() — per-substrate wiring
│   │   └── memory.py                   # emit_memory_pointer() — thin ADE block
│   └── templates/
│       ├── agents/                     # 12 worker subagent definition templates
│       ├── skills/                     # One <skill>/SKILL.md.j2 folder per phase
│       │   ├── ade-intent/SKILL.md.j2
│       │   ├── ade-research/SKILL.md.j2
│       │   ├── ade-plan/SKILL.md.j2
│       │   ├── ade-design-check/SKILL.md.j2
│       │   ├── ade-implement/SKILL.md.j2
│       │   ├── ade-quality-gate/SKILL.md.j2
│       │   ├── ade-review/SKILL.md.j2
│       │   ├── ade-docs/SKILL.md.j2
│       │   ├── ade-ship/SKILL.md.j2
│       │   ├── ade-retro/SKILL.md.j2
│       │   ├── ade-pipeline/SKILL.md.j2  # End-to-end driver (user-invoked)
│       │   ├── ade-pr-review/SKILL.md.j2
│       │   └── grill-with-docs/          # Vendored external skill (MIT, attributed)
│       ├── hooks/                      # Deterministic commit hooks (block-mixed-commit, check-leftover-stub, check-escalation-paths, _hooklib)
│       ├── bootstrap/                  # User-owned seeds (CONTEXT.md, ADR-0001, specs/README, learnings/README, review-calibration)
│       ├── AGENTS.md.j2               # Root canonical instruction file (harness-neutral)
│       ├── memory_pointer.md.j2       # Thin per-harness ADE block for memory files
│       ├── claude_settings.json.j2    # Claude hook wiring
│       ├── gemini_settings.json.j2    # Gemini hook wiring
│       ├── copilot_hooks.json.j2      # Copilot hook wiring
│       ├── codex_hooks.json.j2        # Codex hook wiring
│       ├── stack.md.j2                # Seeds .ade/ade-stack.md (detected stack commands)
│       ├── ade-routing.json.j2        # Seeds .ade/ade-routing.json (routing tiers)
│       └── ade_gitignore.j2
├── docs/
│   ├── ade-architecture-design.md      # Current architecture (v3)
│   └── theme-metaphor-research.md      # Parking doc for future thread
├── tests/
└── pyproject.toml
```

## Development Commands

```bash
uv sync --extra dev       # Install in dev mode (uv-managed)
uv run pytest             # Run tests
uv run ruff check src/ tests/   # Lint
uv run ruff format src/ tests/  # Format
```

## Conventions

- Python 3.11+; `from __future__ import annotations` at top of every module
- Ruff for linting and formatting (line-length 99)
- Type hints on all public functions
- Tests in `tests/` mirroring `src/` structure
- Conventional commits with `Co-Authored-By` trailer
- User-owned project artifacts (`CONTEXT.md`, `docs/adr/`, `docs/specs/`, `.ade/ade-routing.json`, `.ade/ade-stack.md`) are seeded once by `ade init` and never overwritten thereafter — see `_render_and_write_if_missing` in `cli.py`
- ADE-owned artifacts (skills, worker defs, `AGENTS.md`, per-harness memory pointers, hook scripts) are regenerated on every `ade init`
- `ade migrate` (idempotent) upgrades v2 trees to v3: moves config to `.ade/`, removes stale `.claude/commands/`, regenerates skills
- `ade eval` statically checks generated skills (missing YAML frontmatter, oversized descriptions per Codex 8 KB discovery cap)
