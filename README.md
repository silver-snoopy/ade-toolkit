# ADE Toolkit

**Agentic Development Environment** — a portable toolkit that adds AI-agent-driven SDLC capabilities to any project.

ADE combines [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as the orchestrator with local LLMs ([Ollama](https://ollama.com/)) for high-throughput coding, using [CrewAI](https://www.crewai.com/) for the local agent network. Run `ade init` in any project and get a complete AI-assisted development workflow.

## How It Works

```
You describe a task
        |
        v
  Claude Code (orchestrator)
  Plans, reviews, finalizes
        |
        v
  CrewAI + Ollama (local agents)
  Code, test, fix — in isolated git worktrees
        |
        v
  Pre-commit (scanners)
  Semgrep, Ruff, ESLint, Prettier
        |
        v
  PR ready for human review
```

**6-phase SDLC:** Plan → Design Check → Code → Quality Gate → Review → Finalize

**Human checkpoints:** after plan approval and before PR merge. Everything else is autonomous.

## Requirements

| Component | Purpose |
|-----------|---------|
| Python 3.11+ | ADE toolkit runtime |
| [Ollama](https://ollama.com/) | Local LLM inference |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Orchestrator (Max Pro subscription) |
| [Pre-commit](https://pre-commit.com/) | Scanning framework |
| Git | Version control |
| **GPU:** NVIDIA with 24+ GB VRAM | Model inference (tested on RTX 5090 32GB) |

## Installation

```bash
# 1. Install ADE toolkit
pip install ade-toolkit

# 2. Install Ollama models
ollama pull gemma4:31b              # Primary coder (~18GB)
ollama pull qwen2.5-coder:14b      # Test generator (~10GB)
ollama pull qwen2.5-coder:32b      # Fallback model (~20GB)

# 3. Install scanning tools
pip install pre-commit ruff semgrep
npm install -g eslint prettier      # If working with JS/TS projects
```

## Quick Start

```bash
cd my-project
ade init                # Auto-detect stack, generate all configs
ade doctor              # Verify dependencies are installed
pre-commit install      # Activate git hooks

# Start using ADE
claude                  # Launch Claude Code
> /ade-full Add JWT authentication    # Run complete SDLC cycle
> /ade-plan Refactor user service     # Plan only
> /ade-status                         # Check task status
```

## What `ade init` Generates

ADE auto-detects your project's languages and generates all configuration:

```
my-project/
├── CLAUDE.md                        # ADE workflow section (appended)
├── .claude/
│   ├── commands/
│   │   ├── ade-full.md              # /ade-full — complete SDLC cycle
│   │   ├── ade-plan.md              # /ade-plan — planning phase only
│   │   ├── ade-code.md              # /ade-code — design + code + QA
│   │   ├── ade-review.md            # /ade-review — code review phase
│   │   └── ade-status.md            # /ade-status — task status
│   └── settings.json                # Claude Code permissions
├── .pre-commit-config.yaml          # Scanning tools for your stack
├── .ade/
│   ├── config.yaml                  # ADE settings and model config
│   ├── crew/                        # CrewAI agent definitions
│   │   ├── architect.yaml
│   │   ├── coder.yaml
│   │   ├── tester.yaml
│   │   └── fixer.yaml
│   └── modelfiles/                  # Ollama model configurations
│       ├── Modelfile.gemma4-ade
│       ├── Modelfile.qwen-test-ade
│       └── Modelfile.qwen-fallback-ade
```

**Language detection:** Python (`pyproject.toml`, `setup.py`), TypeScript/JavaScript (`package.json`, `tsconfig.json`), Go (`go.mod`), Rust (`Cargo.toml`).

**Smart defaults:** Ruff for Python projects, ESLint + Prettier for JS/TS projects, Semgrep and detect-secrets for all projects.

## Commands

### `ade init`

Initialize ADE in the current project. Auto-detects languages, test commands, and existing linter configs.

```bash
ade init                              # Auto-detect everything
ade init --language python,typescript # Override language detection
ade init --project-dir /path/to/proj  # Initialize a specific directory
```

### `ade doctor`

Verify all dependencies are installed and configured.

```
$ ade doctor
ADE Doctor — Checking dependencies

  PASS  Ollama (local LLM runtime)
  PASS  Claude Code CLI
  PASS  Pre-commit framework
  PASS  Git
  PASS  Ruff (Python linting)
  WARN  Semgrep (SAST scanning) — 'semgrep' not found (optional)
  PASS  All required Ollama models available

All required dependencies found.
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│              Claude Code (Max Pro)                        │
│              THE ORCHESTRATOR                             │
│  Plans, reviews, finalizes, dispatches agents            │
└────────────┬─────────────────────┬───────────────────────┘
             │ subprocess          │ hooks
             v                    v
┌────────────────────┐  ┌─────────────────────────────────┐
│  CrewAI + Ollama   │  │  Pre-commit Framework           │
│  (Local Agents)    │  │  (Deterministic Scanning)       │
│                    │  │                                  │
│  Coder: Gemma 4    │  │  Semgrep · Ruff · ESLint        │
│  Tester: Qwen 2.5  │  │  Prettier · detect-secrets      │
│  in git worktrees  │  │                                  │
└────────────────────┘  └─────────────────────────────────┘
```

**Models (hot-swap mode — one model at a time for full context):**

| Model | Role | VRAM | Context |
|-------|------|------|---------|
| Gemma 4 31B | Coding, architecture, fixing | ~18GB | 128K |
| Qwen 2.5 Coder 14B | Test generation | ~10GB | 64K |
| Qwen 2.5 Coder 32B | Fallback | ~20GB | 32K |

## Development

```bash
# Clone and install
git clone https://github.com/silver-snoopy/ade-toolkit.git
cd ade-toolkit
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
ruff format src/ tests/
```

### Project Structure

```
ade-toolkit/
├── src/ade/
│   ├── cli.py              # CLI entry points (init, doctor)
│   ├── detect.py            # Project stack auto-detection
│   ├── config.py            # Pydantic config models
│   └── templates/           # Jinja2 templates for generated files
├── tests/                   # Test suite (25 tests)
├── docs/
│   ├── ade-architecture-design.md   # Full architecture specification
│   └── ade-research-findings.md     # Market research and analysis
└── pyproject.toml
```

## Roadmap

- [x] **v0.1** — Core CLI: `ade init`, `ade doctor`, project detection, config generation
- [x] **v0.2** — CrewAI runner: sandboxed agent tools, phase dispatch, progress reporting
- [x] **v0.3** — End-to-end SDLC: task lifecycle, worktree management, circuit breakers
- [x] **v1.0** — Production-ready: state safety, crash recovery, config migration, structured logging
- [ ] **v1.1** — Model tooling: `ade models benchmark`, `ade models check`, `ade models create`

## License

MIT
