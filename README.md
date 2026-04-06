# ADE — Agentic Development Environment

A thin bootstrapper that scaffolds AI-driven SDLC skills for [Claude Code](https://claude.com/claude-code).

ADE turns Claude Code into a structured development pipeline: 10 phases from intent capture to merged PR, with human gates, circuit breakers, and parallel subagent dispatch.

## What it does

`ade init` generates everything you need:

```
your-project/
├── .claude/
│   ├── agents/              # Subagent definitions
│   │   ├── backend-coder.md   # Sonnet — implements backend code
│   │   ├── frontend-coder.md  # Sonnet — implements UI code
│   │   ├── code-reviewer.md   # Sonnet — logic review (read-only)
│   │   ├── security-reviewer.md # Sonnet — OWASP review (read-only)
│   │   └── test-runner.md     # Haiku — runs build + tests
│   ├── skills/ade/          # SDLC workflow skills
│   │   ├── ade-full.md        # Complete 10-phase cycle
│   │   ├── ade-plan.md        # Phases 0-2 (intent + research + plan)
│   │   ├── ade-code.md        # Phases 3-5 (design + implement + QA)
│   │   ├── ade-review.md      # Phases 6-8 (review + verify + docs)
│   │   ├── ade-ship.md        # Phases 9-10 (commit + retro)
│   │   └── ade-status.md      # Task dashboard
│   └── commands/            # Slash commands (/ade-full, /ade-plan, etc.)
├── .ade/
│   └── tasks/               # Runtime state (gitignored)
└── CLAUDE.md                # ADE workflow section appended
```

## Architecture

```
Claude Opus (orchestrator)
├── Plans, reviews, verifies, ships
├── Dispatches subagents for parallel work
└── Never writes application code

Claude Sonnet (subagents)
├── Implements code in git worktrees
├── Reviews code (3-lens: logic, conventions, security)
└── Each agent owns specific files — no overlap

Claude Haiku (subagents)
├── Runs build + test commands
└── Fast, cheap verification
```

No CrewAI. No Ollama. No custom agent runtime. Just Claude Code skills and subagent definitions — Markdown files that leverage Claude Code's native capabilities.

## Install

```bash
pip install ade-toolkit
```

## Quick start

```bash
cd your-project
ade init              # Scaffold ADE skills and agents
ade doctor            # Verify prerequisites (Claude Code, git)
claude                # Start Claude Code
/ade-full add auth    # Run the full SDLC cycle
```

## The 10-phase SDLC

| Phase | Actor | Model | What happens |
|-------|-------|-------|-------------|
| 0. Intent | Orchestrator | Opus | Extract requirements |
| 1. Research | 3 parallel subagents | Sonnet | Explore codebase |
| 2. Plan | Orchestrator | Opus | Write implementation plan |
| 3. Design check | Subagent (worktree) | Sonnet | Create file stubs |
| 4. Implement | 1-3 subagents (worktree) | Sonnet | Write code |
| 5. Quality gate | Subagent | Haiku | Build + test |
| 6. Review | 3 parallel subagents | Sonnet | Logic + conventions + security |
| 7. Verify | Orchestrator | Opus | Run tests, capture evidence |
| 8. Docs | Subagent | Sonnet | Update documentation |
| 9. Ship | Orchestrator | Opus | Commit, PR |
| 10. Retro | Orchestrator | Opus | Metrics, learnings, cleanup |

Human gates after research (Phase 1), plan (Phase 2), and merge (Phase 9).

Circuit breakers: max 2 design iterations, max 3 code-review cycles, max 3 QA fixes.

## Orchestrator rules

1. The orchestrator **never writes application code** — only dispatches subagents
2. The orchestrator owns the plan, not the code
3. The orchestrator gates quality — reviews findings, dispatches fixes, never fixes silently
4. Subagents own specific files — no two agents edit the same file
5. Circuit breakers are hard limits — escalate to human, don't retry

## Prerequisites

- [Claude Code](https://claude.com/claude-code) CLI
- Git
- Python 3.11+ (for the bootstrapper only)

## CLI commands

| Command | Description |
|---------|-------------|
| `ade init` | Scaffold ADE into current project |
| `ade doctor` | Check prerequisites |
| `ade status` | Show active task status |

## Design influences

- [gstack](https://github.com/garrytan/gstack) — skills-only architecture, process > tools
- [Octobots](https://github.com/arozumenko/octobots) — external state, session isolation
- [Metaswarm](https://github.com/dsifry/metaswarm) — independent validation, knowledge priming
- [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams) — native subagent dispatch

## v3 → v4 migration

v4 is a complete rewrite. If you used v3 (CrewAI + Ollama):

| v3 | v4 |
|----|-----|
| `src/ade/crew/` (CrewAI runner) | Deleted — replaced by Claude Code subagents |
| `.ade/crew/*.yaml` (agent configs) | `.claude/agents/*.md` (subagent definitions) |
| `.ade/config.yaml` | No config needed — CLAUDE.md is enough |
| Ollama + gemma4:31b | Claude Sonnet/Haiku (no local models) |
| `python -m ade.crew run` | Claude Code Agent tool (native) |
| SafeFileTool / SafeShellTool | Claude Code native Edit/Bash |

Run `ade init` in your project to generate v4 files. v3 `.ade/crew/` directories can be deleted.

## License

MIT
