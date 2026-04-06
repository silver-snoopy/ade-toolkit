# ADE Toolkit

## Project Overview

ADE (Agentic Development Environment) is a thin Python bootstrapper that scaffolds AI-driven SDLC skills and subagent definitions for Claude Code.

`ade init` generates `.claude/agents/`, `.claude/skills/ade/`, and `.claude/commands/` — everything Claude Code needs to run a structured 10-phase development workflow with Opus as orchestrator and Sonnet/Haiku as workers.

## Architecture (v4)

- **No runtime framework** — no CrewAI, no Ollama, no custom agent runtime
- **Skills are Markdown** — `.claude/skills/ade/*.md` define the SDLC phases
- **Agents are Markdown** — `.claude/agents/*.md` define subagent roles and model assignments
- **The bootstrapper only scaffolds** — it doesn't run agents, execute code, or manage state
- **Claude Code IS the runtime** — subagents, worktrees, Edit/Write/Bash are all native

## Project Structure

```
ade-toolkit/
├── src/ade/
│   ├── cli.py            # CLI: init, doctor, status
│   ├── detect.py         # Project stack auto-detection
│   └── templates/
│       ├── agents/       # Subagent definition templates
│       ├── skills/       # SDLC skill templates
│       ├── commands/     # Slash command templates
│       ├── claude_md_section.md.j2
│       └── ade_gitignore.j2
├── docs/
│   ├── orchestrator-invariants.md
│   ├── ade-architecture-design.md  # v3 spec (historical)
│   └── ade-research-findings.md    # v3 research (historical)
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
