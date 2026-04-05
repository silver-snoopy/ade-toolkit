# ADE Toolkit

## Project Overview

ADE (Agentic Development Environment) is a portable toolkit that adds AI-agent-driven SDLC capabilities to any project. It consists of:

1. **`ade` CLI** — A scaffolding tool (`ade init`, `ade doctor`) that generates config files for any project
2. **CrewAI runner** — Local agent definitions that execute coding/testing via Ollama
3. **Config templates** — CLAUDE.md sections, custom commands, pre-commit configs, agent definitions

## Architecture

- **Orchestrator**: Claude Code (Max Pro subscription) — not a custom Python CLI
- **Local agents**: CrewAI + Ollama (Gemma 4 31B for coding, Qwen 2.5 Coder 14B for tests)
- **Scanning**: Pre-commit framework (Semgrep, Ruff, ESLint, Prettier)
- **Isolation**: Git worktrees per task
- **State**: File-based in `.ade/tasks/`

See `docs/ade-architecture-design.md` for full specification.

## Tech Stack

- Python 3.12+
- CrewAI (agent framework)
- Ollama (local LLM runtime)
- Pre-commit (scanning orchestration)
- Click or Typer (CLI framework)

## Project Structure

```
ade-toolkit/
├── src/ade/              # Core package
│   ├── cli.py            # CLI entry points (init, doctor)
│   ├── crew/             # CrewAI agent definitions and runner
│   ├── tools/            # Safe agent tools (SafeShellTool, SafeFileTool)
│   ├── detect.py         # Project stack auto-detection
│   ├── config.py         # Config generation and management
│   └── templates/        # Jinja2 templates for generated files
├── docs/                 # Architecture spec and research
├── tests/                # Test suite
└── pyproject.toml        # Package definition
```

## Development Commands

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
ruff format src/ tests/
```

## Conventions

- Use `ruff` for linting and formatting
- Type hints on all public functions
- Tests in `tests/` mirroring `src/` structure
- Conventional commits
