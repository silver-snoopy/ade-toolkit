# ADE — Agentic Development Environment

## Architecture Design Specification v2

**Version**: 2.0  
**Date**: 2026-04-05  
**Status**: Draft  

---

## Context

Modern software development is increasingly augmented by AI agents, but most setups lack a structured SDLC flow. ADE bridges this gap by combining **Claude Code** (Max Pro subscription) as the orchestrator with **local LLMs** (Ollama on RTX 5090) for high-throughput coding — using **CrewAI** for the local agent network.

ADE is a **portable toolkit**: a thin `ade init` scaffolder generates all configuration files needed for any project. After initialization, **Claude Code itself is the orchestrator** — no custom CLI or Python wrapper needed.

### Design Principles

1. **Claude Code is the orchestrator** — battle-tested agent loop, not a custom reimplementation
2. **Local LLMs for coding throughput** — CrewAI + Ollama for speed, privacy, zero marginal cost
3. **Deterministic scanning** — pre-commit framework, not LLM-based analysis
4. **Git worktrees for isolation** — each task gets its own worktree, preventing conflicts
5. **Portable** — `ade init` works on any brownfield or greenfield project
6. **Zero extra API cost** — all Claude usage via Max Pro subscription

### Goals

- Autonomous 6-phase SDLC with human checkpoints at plan approval and PR review
- Portable across any project (Python, TypeScript, Go, multi-language)
- Industry-standard quality gates (Semgrep, Ruff, ESLint, Prettier)
- Circuit breakers and observability for safe autonomous operation

### Non-Goals

- Replacing human architectural judgment for novel systems
- Production deployment automation (CI/CD pipeline management)
- Cloud-hosted agent infrastructure
- Building a custom orchestration engine (Claude Code already is one)

---

## Hardware Baseline

| Component | Specification | Role |
|-----------|--------------|------|
| GPU | NVIDIA RTX 5090 (32GB GDDR7) | Ollama model inference |
| CPU | AMD 9950X3D (16C/32T, 144MB cache) | CrewAI orchestration, QA tools, test execution, build processes |
| RAM | 64GB DDR5 | Model loading overflow, parallel tool execution |

The 3D V-Cache on the 9950X3D benefits CPU-bound tasks: CrewAI orchestration, parallel test execution, static analysis tools, and build processes. The 32GB VRAM handles model inference on GPU.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                ADE — Agentic Development Environment                │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │         Claude Code (Max Pro Subscription)                    │  │
│  │         ══════════════════════════════                        │  │
│  │         THE ORCHESTRATOR                                      │  │
│  │                                                               │  │
│  │  Inputs:                                                      │  │
│  │  • CLAUDE.md → ADE workflow phases, standards, constraints    │  │
│  │  • .claude/commands/ → /ade-plan, /ade-code, /ade-review      │  │
│  │  • .claude/settings.json → hooks (PostEdit, PreCommit)        │  │
│  │                                                               │  │
│  │  Capabilities:                                                │  │
│  │  • Plans & reviews with Claude Opus reasoning                 │  │
│  │  • Spawns subagents with isolated context + tool allowlists   │  │
│  │  • Creates git worktrees for task isolation                   │  │
│  │  • Runs shell commands (test suites, builds, CrewAI)          │  │
│  │  • Session persistence for multi-phase workflows              │  │
│  └──────────┬──────────────────────────────┬────────────────────┘  │
│             │ subprocess dispatch           │ hooks trigger          │
│             ▼                              ▼                        │
│  ┌───────────────────────┐    ┌──────────────────────────────────┐ │
│  │  CrewAI + Ollama      │    │  Pre-commit Framework            │ │
│  │  (Local LLM Agents)   │    │  (Deterministic Scanning)        │ │
│  │                       │    │                                   │ │
│  │  • Coder Agent        │    │  • Semgrep (SAST)                │ │
│  │    (Gemma 4 31B)      │    │  • Ruff (Python lint+format)     │ │
│  │  • Test Agent         │    │  • ESLint (JS/TS lint)           │ │
│  │    (Qwen 2.5 14B)    │    │  • Prettier (formatting)         │ │
│  │  • Fixer Agent        │    │  • detect-secrets (secret scan)  │ │
│  │    (Gemma 4 31B)      │    │                                   │ │
│  │                       │    │  Triggered by:                    │ │
│  │  Each in own          │    │  • Pre-commit git hooks           │ │
│  │  git worktree         │    │  • Claude Code hooks              │ │
│  └───────────────────────┘    │  • `pre-commit run --all-files`   │ │
│                               └──────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Ollama Runtime                              │  │
│  │                    (RTX 5090 — 32GB VRAM)                     │  │
│  │                                                                │  │
│  │  Hot-Swap Mode (DEFAULT):                                      │  │
│  │  • One model loaded at a time for full context window          │  │
│  │  • Gemma 4 31B (Q4_K_M) ~18 GB + KV cache up to ~12 GB      │  │
│  │  • Swap to Qwen 2.5 Coder 14B for test generation phase      │  │
│  │  • 5-10 second swap latency (acceptable for phase transitions) │  │
│  │                                                                │  │
│  │  Concurrent Mode (EXPERIMENTAL, opt-in via config):            │  │
│  │  • Both models loaded: ~28 GB model weights                   │  │
│  │  • Only ~4 GB for KV cache — context severely limited (~8K)   │  │
│  │  • Only for small tasks with short context needs               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## SDLC Flow — The 6 Phases

### Overview

```
Phase 1:   PLAN           → Claude Opus (Claude Code)
Phase 1.5: DESIGN CHECK   → Local LLM stubs + Claude Opus validation
Phase 2:   CODE           → CrewAI + Ollama (local, in git worktree)
Phase 3:   QUALITY GATE   → Pre-commit + local LLM test generation
Phase 4:   REVIEW         → Claude Opus deep review
Phase 5:   FINALIZE       → Claude Opus docs + human PR review
```

**Human Checkpoints** (mandatory):
- After Phase 1: approve the plan
- After Phase 5: review the PR and decide to merge

**Circuit Breaker**: Max 3 iterations of Code→Review loop. After that → HUMAN_ESCALATION.

---

### Phase 1: PLAN (Claude Opus via Claude Code)

**Actor**: Claude Code (Max Pro subscription)  
**Input**: Human task description + codebase context  
**Output**: `.ade/tasks/<task-id>/plan.md`  

**How it works**: Claude Code reads the codebase, analyzes the task, and produces a structured implementation plan. The ADE workflow instructions in CLAUDE.md guide Claude to follow this format:

```markdown
# Implementation Plan: <task-title>

## Summary
<1-2 sentence description>

## Files to Modify
- `src/auth/handler.py` — Add JWT validation middleware
- `src/auth/tokens.py` — New file: token generation and refresh logic

## Implementation Steps
1. Create `src/auth/tokens.py` with `generate_token()` and `refresh_token()`
2. Add `validate_jwt()` middleware to `src/auth/handler.py`
3. Wire middleware into route definitions in `src/app.py`

## Acceptance Criteria
- [ ] All existing tests pass
- [ ] New tests cover happy path and 3 error cases
- [ ] Semgrep scan passes with no new findings

## Dependencies Required
- PyJWT (already in requirements.txt)

## Estimated Complexity
- Files: 3 modified, 1 new
- Suitable for: single CrewAI coding cycle (no decomposition needed)
```

**For large tasks**: Claude Opus decomposes into sub-tasks, each scoped to fit within model context. Sub-tasks run Phases 1.5-3 independently, then a unified Phase 4 review.

**Human checkpoint**: User reviews and approves the plan before proceeding.

---

### Phase 1.5: DESIGN CHECK (Local LLM + Claude Validation)

**Actor**: CrewAI Architect Agent (Gemma 4 31B) → Claude Code validation  
**Input**: `plan.md`  
**Output**: Stub files with function signatures, class structures, type definitions  

**Process**:
1. Claude Code dispatches: `python -m ade.crew run --phase stubs --task-id <id>`
2. Architect Agent reads plan, generates skeleton code
3. Claude Code reads stubs, validates alignment with the plan
4. If misaligned → feedback to Architect Agent (max 2 iterations)
5. If aligned → proceed to Phase 2

**Why this phase exists**: A 30-second stub check prevents 10-minute rewrites by catching architectural drift before full implementation.

---

### Phase 2: CODE (CrewAI + Ollama, in Git Worktree)

**Actor**: CrewAI Coder Agent (Gemma 4 31B, local)  
**Input**: `plan.md` + approved stubs  
**Output**: Working code on feature branch in isolated worktree  

**Process**:
1. Claude Code creates git worktree: `git worktree add .ade/worktrees/<task-id> -b ade/<task-id>`
2. Claude Code dispatches CrewAI in the worktree directory
3. Coder Agent implements each step from the plan sequentially
4. After each file change: runs test command, self-corrects failures (max 3 per file)
5. Commits completed work with conventional commit messages

**Git Worktree Isolation**:
```
my-project/                      # Main working directory (untouched)
├── .ade/
│   └── worktrees/
│       └── task-abc123/         # Isolated worktree for this task
│           ├── src/             # Full repo checkout on ade/abc123 branch
│           ├── tests/
│           └── ...
```

Each task gets a completely isolated copy of the repository. The main working directory is never modified by agents.

**Concurrent tasks**: Multiple ADE tasks can have active worktrees simultaneously. However, in hot-swap mode, only one task can use the GPU at a time. Concurrent tasks must serialize through Ollama — one codes while others wait. For true parallelism, use Claude Code's native `--worktree` flag to run separate Claude Code sessions in parallel (each session handles its own SDLC cycle).

**Agent Tools** (sandboxed):
- `read_file`, `write_file`, `edit_file` — file operations within worktree only
- `execute_command` — restricted to allowlisted commands (test runners, build tools, git)
- `search_code` — grep across codebase
- `git_commit` — commit to feature branch only

---

### Phase 3: QUALITY GATE (Pre-commit + Local LLM Tests)

**Actors**: Pre-commit framework (deterministic) + Test Agent (Qwen 2.5 Coder 14B)  

Steps 3a and 3b run **in parallel** (both CPU-bound). Step 3c runs **sequentially after** model hot-swap:

#### 3a. Static Analysis (Pre-commit Framework — Deterministic)

```bash
cd .ade/worktrees/<task-id>
pre-commit run --all-files
```

Configured tools:

| Tool | Scope | Purpose |
|------|-------|---------|
| **Semgrep** | All languages | SAST — security vulnerabilities, code anti-patterns |
| **Ruff** | Python files | Linting + formatting (replaces flake8/isort/black) |
| **ESLint** | JS/TS files | Linting + code quality |
| **Prettier** | JS/TS/CSS/HTML/MD | Code formatting consistency |
| **detect-secrets** | All files | Prevent secret/credential commits |

#### 3b. Test Execution

Runs the project's configured test command in the worktree:
```bash
pytest --tb=short -q    # or jest --ci, go test ./..., etc.
```

#### 3c. Test Gap Analysis (LLM — Qwen 2.5 Coder 14B)

- Ollama hot-swaps to Qwen 2.5 Coder 14B
- Test Agent analyzes the diff, identifies untested code paths
- Generates additional tests for uncovered scenarios
- Runs the new tests to verify they pass

#### 3d. QA Report

Results compiled to `.ade/tasks/<task-id>/qa-report.json`:
```json
{
  "task_id": "abc123",
  "gate_status": "PASS|WARN|FAIL",
  "semgrep": { "findings": 0 },
  "ruff": { "errors": 0, "warnings": 2 },
  "eslint": { "errors": 0 },
  "prettier": { "files_reformatted": 3 },
  "tests": { "passed": 42, "failed": 0, "coverage": "87%" },
  "generated_tests": { "new_tests": 3, "all_passing": true },
  "blocking_issues": []
}
```

**Gate Logic**:
- **PASS**: Zero errors, all tests pass → proceed to Phase 4
- **WARN**: Minor warnings → auto-fix and re-check
- **FAIL**: Errors found → Fixer Agent resolves (max 3 iterations)

---

### Phase 4: REVIEW (Claude Opus via Claude Code)

**Actor**: Claude Code (Max Pro subscription)  
**Input**: Git diff + QA report + original plan  
**Output**: `.ade/tasks/<task-id>/review-feedback.md`  

Claude Code reviews the complete diff against the plan:
- **Plan alignment**: Does the code implement what was planned?
- **Logic correctness**: Bugs, race conditions, edge cases?
- **Security**: Injection, auth bypass, secrets exposure?
- **Architecture**: Does it follow project patterns?

**Review Outcomes**:
- **APPROVED** → proceed to Phase 5
- **MINOR_FIXES** → Fixer Agent in worktree → re-run Phase 3 → back to Phase 4
- **MAJOR_ISSUES** → HUMAN_ESCALATION with detailed explanation

**Circuit Breaker**: After 3 Code→Review cycles → HUMAN_ESCALATION regardless.

**Context Management**: For large diffs, Claude Code should spawn a subagent for Phase 4 review (each subagent gets its own context window). The custom commands `/ade-code` and `/ade-review` as separate commands are natural context boundaries — running phases as separate commands prevents context overflow in long sessions.

---

### Phase 5: FINALIZE (Claude Opus via Claude Code)

**Actor**: Claude Code (Max Pro subscription)  
**Input**: Approved code + review feedback  
**Output**: Documentation, PR, polished commits  

**Process**:
1. Squash commits on feature branch for clean history
2. Generate/update documentation for changed APIs
3. Update CHANGELOG.md
4. Create PR description with summary, test results, QA report
5. **Human checkpoint**: User reviews final PR → merge decision

After merge, cleanup: `git worktree remove .ade/worktrees/<task-id>`

---

## State Machine

```
                      INITIATED
                          │ user provides task
                          ▼
                      PLANNING
                          │ human approves plan
                          ▼
                    DESIGN_CHECK ◄──┐
                          │        │ stubs rejected (max 2x)
                          │────────┘
                          │ stubs approved
                          ▼
                      CODING (in worktree)
                          │ code complete
                          ▼
                    QUALITY_GATE ◄──────────┐
                          │                 │ fixes needed (max 3x)
                          │ gate passed     │
                          ▼                 │
                      REVIEWING ────────────┘
                          │
                ┌─────────┼──────────────┐
                │         │              │
             approved   minor         major issues /
                │       fixes →       max iterations
                ▼       Fixer Agent        │
            FINALIZING                     ▼
                │                  HUMAN_ESCALATION
                │                     │         │
                ▼                  resolved   abandoned
          AWAITING_MERGE              │         │
                │                     ▼         ▼
                │ human merges    COMPLETED   FAILED
                ▼
            COMPLETED

Terminal states: COMPLETED, FAILED
Any state + user abort → FAILED
```

---

## Portable Toolkit — `ade init`

### What `ade init` Generates

```bash
pip install ade-toolkit        # Install once, globally
cd my-project
ade init                       # Auto-detect stack, generate all configs
```

**Auto-detection**:
- Scans for `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, etc.
- Detects existing linter configs (`.eslintrc`, `ruff.toml`, `.prettierrc`)
- Detects test commands from project config
- Merges with existing CLAUDE.md (appends ADE section, doesn't overwrite)

### Generated File Structure

```
my-project/
├── CLAUDE.md                      # Updated with ADE workflow section
├── .claude/
│   ├── commands/
│   │   ├── ade-plan.md            # /ade-plan — run Phase 1 only
│   │   ├── ade-code.md            # /ade-code — run Phases 1.5-3
│   │   ├── ade-review.md          # /ade-review — run Phase 4
│   │   ├── ade-full.md            # /ade-full — complete SDLC cycle
│   │   └── ade-status.md          # /ade-status — check task status
│   └── settings.json              # Hooks configuration
├── .pre-commit-config.yaml        # Scanning tools (Semgrep, Ruff, ESLint, Prettier)
├── .ade/
│   ├── config.yaml                # ADE-specific settings
│   ├── crew/                      # CrewAI agent definitions
│   │   ├── architect.yaml
│   │   ├── coder.yaml
│   │   ├── tester.yaml
│   │   └── fixer.yaml
│   ├── modelfiles/                # Ollama model configs
│   │   ├── Modelfile.gemma4-ade
│   │   └── Modelfile.qwen-test-ade
│   ├── worktrees/                 # Git worktrees (gitignored)
│   ├── tasks/                     # Task state (gitignored)
│   └── .gitignore                 # Ignores worktrees/ and tasks/
└── ... (existing project files)
```

### CLAUDE.md — ADE Workflow Section

`ade init` appends this to your project's CLAUDE.md:

```markdown
## ADE — Agentic Development Environment

### Workflow

When asked to implement a feature or fix a bug using the ADE workflow
(triggered by /ade-full or when the user says "use ADE"):

1. **PLAN**: Analyze the codebase and create a structured plan in
   `.ade/tasks/<task-id>/plan.md`. Ask the user to approve before proceeding.

2. **DESIGN CHECK**: Dispatch CrewAI architect agent to generate code stubs:
   `python -m ade.crew run --phase stubs --task-id <id>`
   Review the stubs for plan alignment. Re-dispatch if needed (max 2x).

3. **CODE**: Create git worktree, dispatch CrewAI coder agent:
   `git worktree add .ade/worktrees/<id> -b ade/<id>`
   `python -m ade.crew run --phase code --task-id <id> --worktree .ade/worktrees/<id>`

4. **QUALITY GATE**: Run scanning and tests in the worktree:
   `cd .ade/worktrees/<id> && pre-commit run --all-files`
   `cd .ade/worktrees/<id> && <test_command>`
   If failures, dispatch fixer agent (max 3x).

5. **REVIEW**: Review the diff (`git diff main...ade/<id>`) against the plan.
   Check for: logic errors, security issues, plan alignment, code quality.
   If issues: dispatch fixer agent and re-run QA gate (max 3 total cycles).

6. **FINALIZE**: Squash commits, generate docs, create PR description.
   Present to user for merge decision. Clean up worktree after merge.

### Circuit Breaker
After 3 code→review cycles, escalate to the user with a summary of what's
failing. Do NOT keep retrying silently.

### Models
- Planning, review, finalization: Claude Opus (this session)
- Coding, fixing: Ollama Gemma 4 31B (via CrewAI)
- Test generation: Ollama Qwen 2.5 Coder 14B (via CrewAI)
```

### Custom Commands

**`.claude/commands/ade-full.md`** (triggered by `/ade-full`):
```markdown
Run the complete ADE SDLC cycle for the following task: $ARGUMENTS

Follow the ADE workflow defined in CLAUDE.md:
1. Create a plan and ask for approval
2. Run design check with local agents
3. Dispatch coding to CrewAI in a git worktree
4. Run quality gate (pre-commit + tests)
5. Deep review the diff
6. Finalize with docs and PR

Track progress in .ade/tasks/ and report status at each phase transition.
```

**`.claude/commands/ade-plan.md`** (triggered by `/ade-plan`):
```markdown
Create an ADE implementation plan for: $ARGUMENTS

Analyze the codebase and produce a structured plan in
.ade/tasks/<task-id>/plan.md following the format in CLAUDE.md.
Include: files to modify, implementation steps, acceptance criteria.
Ask me to approve the plan before any further action.
```

### Configuration (`.ade/config.yaml`)

```yaml
version: "2.0"

project:
  name: auto-detected
  languages: auto-detect           # or: [python, typescript, go]
  test_commands:
    python: pytest --tb=short -q
    typescript: npx jest --ci
  build_command: null               # Optional

models:
  primary:
    name: gemma4:31b
    provider: ollama
    context_window: 131072          # 128K tokens
    temperature: 0.1
  test_generator:
    name: qwen2.5-coder:14b
    provider: ollama
    context_window: 65536
    temperature: 0.2
  fallback:
    name: qwen2.5-coder:32b
    provider: ollama
  mode: hot-swap                    # hot-swap (default) or concurrent (experimental)

orchestration:
  max_phase_iterations: 3           # Per phase circuit breaker
  max_total_iterations: 9           # Total across all phases
  human_checkpoints:
    - after_plan                    # Always: review the plan
    - after_final_review            # Always: review the PR

worktree:
  base_dir: .ade/worktrees
  cleanup_after_merge: true
  branch_prefix: ade/

scanning:
  pre_commit: true                  # Use .pre-commit-config.yaml
  semgrep: { enabled: true }
  ruff: { enabled: auto }          # Auto-enable if Python detected
  eslint: { enabled: auto }        # Auto-enable if JS/TS detected
  prettier: { enabled: auto, write: true }
  detect_secrets: { enabled: true }

fallback_triggers:
  consecutive_tool_failures: 3      # Switch to fallback model after 3 failed tool calls
  qa_fix_failures: 3                # Switch after 3 failed QA fix attempts
  empty_responses: 2                # Switch after 2 empty/gibberish responses

logging:
  level: info
  format: structured
  retention_days: 30
```

### CLI Commands

**MVP (v1.0)**:
```bash
ade init                           # Initialize ADE in current project
ade init --language python,ts      # Override auto-detection
ade doctor                         # Verify all dependencies (Ollama, Claude Code, pre-commit)
```

**Post-MVP (v1.1+)**:
```bash
ade update                         # Update configs to latest ADE template
ade models check                   # Verify Ollama models are available
ade models benchmark               # Quick inference speed test
ade models create                  # Create custom Ollama Modelfiles
```

Note: `ade` is a **scaffolding CLI**, not an orchestrator. After `ade init`, Claude Code handles all orchestration. The `ade` tool's job is finished once config files are generated.

After `ade init`, you use Claude Code directly:
```bash
claude                             # Start Claude Code
> /ade-full Add JWT authentication  # Run complete SDLC cycle
> /ade-plan Refactor user service   # Plan only
> /ade-status                       # Check current task status
```

---

## CrewAI Agent Definitions

### Architect Agent

```yaml
role: Software Architect
goal: >
  Generate accurate code skeletons and type stubs that faithfully represent
  the implementation plan's architecture, file structure, and interfaces.
backstory: >
  You are a senior software architect who translates high-level plans into
  concrete code structures. You focus on interfaces, type signatures, and
  module boundaries — not implementation details.
model: ollama/gemma4:31b
tools: [read_file, write_file, list_directory, search_code]
max_iterations: 5
```

### Coder Agent

```yaml
role: Senior Software Developer
goal: >
  Implement the approved design by writing clean, correct, well-tested code
  that follows the project's existing patterns and conventions.
backstory: >
  You are an experienced developer who writes production-quality code. You
  follow the implementation plan precisely, respect existing code patterns,
  and ensure all tests pass after each change.
model: ollama/gemma4:31b
tools: [read_file, write_file, edit_file, execute_command, search_code, git_commit, list_directory]
max_iterations: 15
```

### Test Agent

```yaml
role: QA Engineer
goal: >
  Ensure comprehensive test coverage by generating tests for uncovered code
  paths, edge cases, and error scenarios identified in the implementation diff.
backstory: >
  You are a thorough QA engineer who writes tests that catch real bugs. You
  analyze code changes, identify what's not covered, and write focused tests
  that verify both happy paths and failure modes.
model: ollama/qwen2.5-coder:14b
tools: [read_file, write_file, execute_command, search_code]
max_iterations: 10
```

### Fixer Agent

```yaml
role: Bug Fixer
goal: >
  Fix specific issues identified by the QA gate or code review, making
  minimal targeted changes that resolve the finding without introducing
  new problems.
backstory: >
  You are a careful developer who fixes bugs with surgical precision.
  You read the error report, understand the root cause, and apply the
  minimal fix needed. You never make unrelated changes.
model: ollama/gemma4:31b
tools: [read_file, write_file, edit_file, execute_command, search_code, git_commit]
max_iterations: 10
```

---

## Ollama Configuration

### Environment Variables

```bash
# Recommended Ollama settings for ADE
export OLLAMA_KEEP_ALIVE="5m"          # Unload after 5 min idle (hot-swap friendly)
export OLLAMA_MAX_LOADED_MODELS="1"    # Hot-swap: one model at a time
export OLLAMA_NUM_PARALLEL="1"         # One request at a time
export OLLAMA_FLASH_ATTENTION="1"      # Memory-efficient attention
```

### Custom Modelfiles

```
# .ade/modelfiles/Modelfile.gemma4-ade
FROM gemma4:31b
PARAMETER num_ctx 131072              # 128K context
PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1

# .ade/modelfiles/Modelfile.qwen-test-ade
FROM qwen2.5-coder:14b
PARAMETER num_ctx 65536               # 64K context
PARAMETER temperature 0.2
PARAMETER top_p 0.9

# .ade/modelfiles/Modelfile.qwen-fallback-ade
FROM qwen2.5-coder:32b
PARAMETER num_ctx 32768               # 32K context (limited by VRAM with 20GB model)
PARAMETER temperature 0.1
PARAMETER top_p 0.9
```

```bash
ollama create gemma4-ade -f .ade/modelfiles/Modelfile.gemma4-ade
ollama create qwen-test-ade -f .ade/modelfiles/Modelfile.qwen-test-ade
```

### VRAM Budget (RTX 5090, 32GB)

```
Hot-Swap Mode (DEFAULT):
┌────────────────────────────────────┐
│ Active Model:              18.0 GB │ (Gemma 4 31B Q4_K_M)
│ KV Cache (128K context):  ~10.0 GB │
│ CUDA Overhead:             ~1.0 GB │
│ Headroom:                   3.0 GB │
│ Total:                     32.0 GB │
└────────────────────────────────────┘
Swap time: ~5-10 seconds between models

Concurrent Mode (EXPERIMENTAL):
┌────────────────────────────────────┐
│ Gemma 4 31B weights:       18.0 GB │
│ Qwen 2.5 14B weights:     10.0 GB │
│ KV Cache (both models):    ~3.0 GB │ ← severely limited
│ CUDA Overhead:              ~1.0 GB │
│ Total:                     32.0 GB │
└────────────────────────────────────┘
WARNING: Context limited to ~8K tokens per model in concurrent mode
```

### Fallback Model Triggers

The fallback model (Qwen 2.5 Coder 32B) activates when:
1. Primary model fails 3 consecutive tool calls (broken JSON, malformed output)
2. Fixer Agent cannot resolve QA findings in 3 iterations
3. 2+ empty/truncated/gibberish responses
4. Explicit user override via config

---

## Model Selection Rationale

### Primary Coder: Gemma 4 31B

- **Released**: April 2, 2026 — day-one Ollama support
- **LiveCodeBench v6**: 80.0%
- **Context**: 256K tokens (configured at 128K for VRAM headroom)
- **Native function calling**: Purpose-built for agentic workflows with CrewAI
- **VRAM**: ~18GB at Q4_K_M quantization
- **Risk**: Released 3 days ago. Automatic fallback catches obvious failures (broken tool calls, gibberish). Subtle incorrectness is caught by Phase 4 (Claude Opus review) — this is a key strength of the "different model for review" pattern. If Gemma 4 proves unreliable in practice, temporarily route coding through Qwen 2.5 Coder 32B via config override.

### Test Generator: Qwen 2.5 Coder 14B

- **Family benchmark**: Qwen 2.5 Coder 32B scores 88.4% HumanEval — 14B is strong for its size
- **Specialization**: Excels at test structure, assertions, code patterns
- **VRAM**: ~10GB at Q4_K_M — loads quickly in hot-swap mode

### Fallback: Qwen 2.5 Coder 32B

- **When**: Gemma 4 31B underperforms (see trigger conditions above)
- **VRAM**: ~20GB at Q4_K_M — leaves ~11GB for KV cache
- **Context**: 32K tokens (reduced from 128K — the VRAM tradeoff of a larger model)
- **Implication**: When fallback triggers on a large-context task, the plan should be decomposed into smaller sub-tasks that fit within 32K context. The CLAUDE.md instructions guide Claude Code to re-plan with smaller scope.
- **Purpose**: Battle-tested insurance for model quality, with scope adjustment for context

### Cloud: Claude Opus (via Claude Code, Max Pro)

- **Phases**: Plan (1), Design Check (1.5 validation), Review (4), Finalize (5)
- **Cost**: $0 additional — covered by Max Pro subscription ($250/month)
- **Why**: Superior reasoning for architecture, nuanced review, security analysis

---

## Security Model

### Agent Sandboxing

```yaml
allowed_commands:
  - pytest, jest, npm test, go test    # Test runners
  - ruff, eslint, prettier, semgrep    # Linters/scanners
  - pre-commit                         # Hook framework
  - git add, commit, diff, status, log # Version control
  - npm run build, make, cargo build   # Build tools

blocked_commands:
  - rm -rf, rm -r                      # Destructive file ops
  - curl, wget, ssh, scp               # Network access
  - docker, sudo                       # Privileged ops
  - pip install, npm install            # Dependency changes (require human approval)

blocked_file_patterns:
  - "*.env*"                           # Environment files
  - "*credentials*"                    # Credential files
  - "*.ssh/*"                          # SSH keys
```

### Sandboxing Enforcement

The allowlists above are **enforced** via a custom `SafeShellTool` wrapper in the CrewAI agent definitions. CrewAI's built-in `execute_command` tool does not enforce allowlists — the ADE `ade.crew` module provides a hardened replacement:

```python
# ade/crew/tools/safe_shell.py (pseudocode)
class SafeShellTool(BaseTool):
    def _run(self, command: str) -> str:
        # Validate against allowlist before execution
        if not is_allowed(command, config.allowed_commands):
            return f"BLOCKED: '{command}' is not in the allowed command list"
        if matches_blocked_pattern(command, config.blocked_patterns):
            return f"BLOCKED: '{command}' matches a blocked pattern"
        # Execute in worktree directory only
        return subprocess.run(command, cwd=worktree_path, timeout=300)
```

Similarly, `SafeFileWriteTool` enforces the tiered file permission model. Agents never use raw `execute_command` — only the safe wrappers.

### File Access Rules (Layered Permissions)

- **Tier 1 — Free write**: Files listed in `plan.md` "Files to Modify"
- **Tier 2 — Auto-allowed**: `__init__.py`, test files (Test Agent), formatting changes (Prettier/Ruff)
- **Tier 3 — Logged**: Same-directory siblings of Tier 1 files (flagged for review)
- **Tier 4 — Blocked**: All other files
- **Delete**: Never — agents cannot delete files

### Git Safety

- Agents work in isolated worktrees on `ade/<task-id>` branches only
- No force push, no push to main/master
- Worktree cleanup only after successful merge
- Main working directory is never modified by agents

### Dependency Changes

If a task requires new dependencies, the plan (Phase 1) must list them explicitly. Claude Code prompts the human to install them before Phase 2 begins. Agents never install dependencies directly.

---

## CrewAI Subprocess Lifecycle Management

When Claude Code dispatches CrewAI (`python -m ade.crew run ...`), the subprocess can run for 10+ minutes. Robustness requires monitoring:

### Timeout & Exit Codes

```yaml
# .ade/config.yaml
orchestration:
  max_phase_duration_minutes: 30    # Kill subprocess after 30 min
```

CrewAI runner exits with specific codes:
- **0**: Success — all tasks completed
- **1**: Failure — agent encountered unrecoverable error
- **2**: Partial — some work completed, written to worktree, but agent hit max iterations
- **3**: Timeout — killed by timer, partial work may exist

Claude Code reads the exit code and reacts:
- Exit 0 → proceed to next phase
- Exit 1 → read error log, attempt fix or escalate
- Exit 2 → read partial output, decide to retry or escalate
- Exit 3 → escalate to human (likely model or GPU issue)

### Progress Reporting

The CrewAI runner writes incremental progress to `.ade/tasks/<id>/progress.log`:
```
[14:15:02] phase=code agent=coder step=1/4 file=src/auth/tokens.py status=writing
[14:17:30] phase=code agent=coder step=1/4 file=src/auth/tokens.py status=complete
[14:17:35] phase=code agent=coder step=2/4 file=src/auth/handler.py status=writing
```

Claude Code can check progress via: `tail -5 .ade/tasks/<id>/progress.log`

### Ollama Failure Handling

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Ollama not running | Connection refused | CrewAI runner exits with code 1 + clear error message |
| Model OOM | CUDA out of memory error | Runner attempts hot-swap to smaller context, retry once |
| Model hanging | No output for 120 seconds | Runner kills inference, retries with fresh context |
| GPU driver crash | Subprocess crash | Exit code 1, Claude Code escalates to human |

---

## Error Recovery & Resume

### Crash Recovery

Each phase boundary writes state to `.ade/tasks/<id>/state.json`. If Claude Code session ends:
1. Start new session: `claude`
2. `/ade-status` shows last completed phase
3. Resume from next phase manually or with `/ade-code --task-id <id>`

### Phase Idempotency

| Phase | Safe to Re-run? | Notes |
|-------|-----------------|-------|
| Plan | Yes | Regenerates plan.md |
| Design Check | Yes | Regenerates stubs |
| Code | With caution | Reset worktree branch first |
| Quality Gate | Yes | Deterministic tools |
| Review | Yes | Stateless Claude evaluation |
| Finalize | Yes | Regenerates docs |

### Git Worktree Safety

If ADE crashes mid-coding:
- Worktree preserves all committed code on the feature branch
- Uncommitted changes may be lost (acceptable — agent commits frequently)
- `git worktree list` shows active worktrees
- `git worktree remove .ade/worktrees/<id>` for cleanup

---

## Observability

### State Management — Who Writes What

- **Claude Code** writes `state.json` at phase boundaries (instructed by CLAUDE.md to run `echo '...' > .ade/tasks/<id>/state.json` or use a helper script)
- **CrewAI runner** writes `progress.log` during execution and updates `state.json` at completion
- **Pre-commit** output is captured by Claude Code and written to `qa-report.json`
- **Recovery**: If `state.json` is missing/corrupt, fallback to checking: which artifacts exist (plan.md? stubs? qa-report.json?) + `git log` on the worktree branch

### Task State (`.ade/tasks/<id>/state.json`)

```json
{
  "task_id": "abc123",
  "description": "Add JWT authentication",
  "status": "quality_gate",
  "current_phase": 3,
  "iterations": {
    "design_check": 1,
    "code_review": 0,
    "qa_fix": 0
  },
  "timestamps": {
    "created": "2026-04-05T14:00:00Z",
    "plan_approved": "2026-04-05T14:05:00Z",
    "coding_started": "2026-04-05T14:08:00Z"
  },
  "worktree": ".ade/worktrees/abc123",
  "branch": "ade/abc123",
  "models_used": ["gemma4:31b", "qwen2.5-coder:14b"],
  "files_modified": ["src/auth/tokens.py", "src/auth/handler.py"]
}
```

### Agent Logs

CrewAI agent actions are logged to `.ade/tasks/<id>/logs/`:
```json
{
  "timestamp": "2026-04-05T14:15:00Z",
  "agent": "coder",
  "action": "write_file",
  "params": { "path": "src/auth/tokens.py" },
  "result": "success",
  "model": "gemma4:31b",
  "tokens": { "input": 2048, "output": 512 }
}
```

---

## Pre-commit Configuration

### Generated `.pre-commit-config.yaml`

```yaml
repos:
  # Security scanning
  - repo: https://github.com/returntocorp/semgrep
    rev: v1.x.x
    hooks:
      - id: semgrep
        args: ['--config', 'p/default']  # Pinned ruleset for reproducibility
        # Use '--config auto' for latest rules (requires network)

  # Python linting + formatting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.x.x
    hooks:
      - id: ruff
        args: ['--fix']
      - id: ruff-format

  # JavaScript/TypeScript formatting
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.x.x
    hooks:
      - id: prettier
        types_or: [javascript, typescript, css, html, markdown, json, yaml]

  # ESLint (if JS/TS project)
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.x.x
    hooks:
      - id: eslint
        types: [javascript, typescript]

  # Secret detection
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.x.x
    hooks:
      - id: detect-secrets
```

`ade init` auto-detects which hooks to include based on project languages.

---

## Technology Stack Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestrator** | Claude Code (Max Pro) | Planning, review, finalization, dispatch |
| **Agent Framework** | CrewAI | Local multi-agent coding, testing, fixing |
| **LLM Runtime** | Ollama | Local model serving on RTX 5090 |
| **Primary Model** | Gemma 4 31B | Code generation, architecture, fixing |
| **Secondary Model** | Qwen 2.5 Coder 14B | Test generation |
| **Fallback Model** | Qwen 2.5 Coder 32B | Backup if primary underperforms |
| **SAST** | Semgrep (via pre-commit) | Security scanning |
| **Python Lint** | Ruff (via pre-commit) | Python linting + formatting |
| **JS/TS Lint** | ESLint (via pre-commit) | JavaScript/TypeScript linting |
| **Formatter** | Prettier (via pre-commit) | Multi-language formatting |
| **Secrets** | detect-secrets (via pre-commit) | Secret detection |
| **Scanning** | Pre-commit framework | Deterministic tool orchestration |
| **Isolation** | Git worktrees | Per-task repository isolation |
| **Project Setup** | `ade init` (Python CLI) | Config scaffolding and auto-detection |
| **Workflow** | CLAUDE.md + custom commands | SDLC phase definitions |

---

## Installation & Setup

### One-Time Setup

```bash
# 1. Install ADE toolkit (thin scaffolder)
pip install ade-toolkit

# 2. Install Ollama models
ollama pull gemma4:31b             # Primary coder (~18GB Q4)
ollama pull qwen2.5-coder:14b     # Test generator (~10GB Q4)
ollama pull qwen2.5-coder:32b     # Fallback model (~20GB Q4)

# 3. Claude Code CLI (part of Max Pro subscription)
npm install -g @anthropic-ai/claude-code

# 4. Pre-commit framework
pip install pre-commit

# 5. Scanning tools
pip install ruff semgrep
npm install -g eslint prettier

# 6. Verify everything
ade doctor
```

### Per-Project Setup

```bash
cd my-project
ade init                           # Generate all configs
pre-commit install                 # Activate git hooks
ade models create                  # Create custom Ollama Modelfiles

# Start using ADE
claude                             # Launch Claude Code
> /ade-full Add user authentication with JWT tokens
```

---

## Verification Plan

### Setup Verification

1. `ade doctor` — checks all dependencies (Ollama, Claude Code, pre-commit, scanning tools)
2. `ade models check` — verifies required Ollama models respond
3. `ade models benchmark` — quick inference test (expected: >30 tok/s for Gemma 4)

### Integration Test

1. Create test project with simple Python module
2. `ade init` → verify config generated correctly
3. `claude` → `/ade-full "Add a greet() function that returns 'Hello, World!'"`
4. Verify all 6 phases execute end-to-end
5. Verify git worktree created and cleaned up after merge

### Stress Test

1. Medium-complexity task: "Add REST API endpoint with validation and error handling"
2. Verify circuit breaker triggers after 3 failed iterations
3. Verify human escalation works
4. Verify crash recovery: kill session mid-pipeline, resume in new session

---

## Versioning & Migration

The `.ade/config.yaml` includes a `version` field. When `ade init --upgrade` detects an older version:
1. Migrates config to current schema
2. Backs up old config
3. Non-destructive: new fields get defaults, removed fields archived

---

## Future Considerations (Out of Scope for v1)

- **Claude Agent SDK migration**: When API costs become acceptable, migrate from Claude Code CLI to Agent SDK for tighter programmatic control
- **MCP Integration**: Connect agents to external tools via Model Context Protocol
- **Agent Teams**: Leverage Claude Code's experimental agent teams when they reach GA
- **MegaLinter**: Replace individual pre-commit hooks with unified MegaLinter for broader coverage
- **Web Dashboard**: Browser-based monitoring instead of CLI-only
- **CI/CD Integration**: Trigger ADE phases from GitHub Actions
- **Biome**: Replace ESLint + Prettier with Biome when it matures further
