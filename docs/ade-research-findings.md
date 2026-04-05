# ADE — Research Findings

## Agentic Development Environment: Industry Landscape & Technology Assessment

**Date**: 2026-04-05  
**Purpose**: Deep research supporting the ADE architecture design  

---

## 1. Agentic SDLC Frameworks — Market Landscape (2026)

### Leading Tools

| Tool | Type | Stars/Adoption | Key Strength |
|------|------|----------------|-------------|
| **Claude Code** | CLI Agent | 22K+ GitHub stars, 111K+ npm | Deep reasoning, Ollama support (Jan 2026) |
| **OpenHands** | Open-source Agent | $18.8M Series A (Nov 2025) | MIT-licensed, multi-LLM, autonomous |
| **Cursor** | IDE Agent | $2B+ ARR, #1 in LogRocket rankings | Acquired by Cognition AI (~$250M) |
| **Codex CLI** | Terminal Agent | 65K+ GitHub stars | OpenAI's answer to Claude Code, Rust-based |
| **Aider** | Terminal Agent | Best OSS terminal agent | Git-native, excellent Ollama support |
| **Continue.dev** | IDE Extension | VS Code + JetBrains | Agent mode, model-agnostic |

### Industry Shift: Reactive → Proactive

Traditional AI assistants react to requests. Agentic tools now:
- Receive a goal description
- Autonomously plan, execute across files, run tests, fix failures
- Commit, create PRs, document changes
- Human provides direction and approval, not step-by-step instructions

---

## 2. Local LLM Performance Benchmarks (April 2026)

### Code Generation Rankings

| Model | HumanEval | LiveCodeBench v6 | Context | VRAM (Q4) |
|-------|-----------|-------------------|---------|-----------|
| **Qwen 2.5 Coder 32B** | 88.4% | — | 128K | ~20 GB |
| **Gemma 4 31B** | — | 80.0% | 256K | ~18 GB |
| **DeepSeek Coder V2** | 81.1% | — | 128K | ~15 GB |
| **Codestral 25.01** | 81.1% | — | 256K | ~14 GB |
| **Qwen 2.5 Coder 14B** | >88% | — | 128K | ~10 GB |
| **DeepSeek R1 0528 8B** | — | — | 128K | ~6 GB |

### Agentic Capability Rankings

For **agentic tasks** (tool calling, multi-step reasoning, instruction following):

1. **Gemma 4 31B** — Purpose-built for agents, native function calling, 256K context
2. **Qwen 3.5 35B-A3B** — MoE architecture, strong tool use, only 3B active params
3. **Qwen 2.5 Coder 32B** — Best raw coding, good instruction following
4. **DeepSeek R1** — Strong reasoning but slower (chain-of-thought)

### Code Review Specialist Models

| Model | Strength | Best For |
|-------|----------|---------|
| **DeepSeek v3.1** | Concise, informative review comments | General code review |
| **DeepSeek-R1** | Deep reasoning, chain-of-thought | Security analysis, complex bugs |
| **Qwen 3.5** | Balanced programming + reasoning | Multi-language review |

---

## 3. Gemma 4 Technical Assessment

### Release Details (April 2, 2026)

- **Sizes**: E2B, E4B, 26B MoE, 31B Dense
- **Modality**: Text + Image input, Text output
- **Context Windows**: 128K (small) / 256K (medium+)
- **Ollama Support**: Day-one, all sizes available
- **Native Function Calling**: Yes — critical for CrewAI agent integration

### 31B Dense Model Benchmarks

| Benchmark | Score |
|-----------|-------|
| MMLU Pro | 85.2% |
| LiveCodeBench v6 | 80.0% |
| MATH | Strong |
| Agentic tasks | Purpose-built |

### Hardware Requirements (31B Dense)

- **FP16**: 62 GB (doesn't fit single consumer GPU)
- **Q8**: ~31 GB (tight fit on RTX 5090 32GB)
- **Q4_K_M**: ~18 GB (recommended — good quality, fits with room)
- **Q4_K_S**: ~16 GB (slightly lower quality, more headroom)

### Risk Assessment

- **Maturity**: Released 3 days ago — expect rough edges
- **Mitigation**: Qwen 2.5 Coder 32B as tested fallback
- **Advantage**: Native agentic capabilities may outweigh raw benchmark scores

---

## 4. Multi-Agent Framework Comparison

### Framework Decision Matrix

| Criteria | CrewAI | LangGraph | AutoGen/MS Agent | OpenAI Swarm |
|----------|--------|-----------|-------------------|-------------|
| **Ollama Support** | Native | Via wrapper | Via LiteLLM | Via wrapper |
| **Role-Based Agents** | Excellent | Good | Good | Basic |
| **Tool Integration** | Built-in | Built-in | Built-in | Basic |
| **State Management** | Basic | Advanced | Advanced | None |
| **Learning Curve** | Low | Medium | High | Low |
| **Production Readiness** | Good | Excellent | GA Q1 2026 | Experimental |
| **Best For** | Ship in <2 weeks | Complex workflows | Enterprise/Azure | Prototyping |

### Why CrewAI for ADE

1. **Native Ollama support** — no wrapper code needed
2. **Role-based agent design** — maps directly to SDLC phases
3. **Simple mental model** — Agent + Task + Tool + Crew
4. **Fast iteration** — get a working pipeline in days, not weeks
5. **A2A protocol support** — future-proof for agent interoperability

### LiteLLM as Optional Enhancement

- Unified OpenAI-compatible API across 100+ providers
- Retry/fallback logic across model deployments
- Cost-based routing between local (Ollama) and cloud (Claude API)
- **Not required for v1** — CrewAI's native Ollama support is sufficient
- Consider adding for v2 if model routing complexity increases

---

## 5. Quality Assurance Tool Assessment

### SAST Tools (2026 Rankings)

| Rank | Tool | Type | Strength |
|------|------|------|----------|
| 1 | DryRun Security | AI-native SAST | Leading AI analysis |
| 2 | **Snyk** | SAST + SCA + Secrets | Comprehensive, already in user's VS Code |
| 3 | **Semgrep** | Programmable SAST | Lightweight, community rules, scriptable |
| 4 | GitHub CodeQL | GitHub-native SAST | Deep analysis, GitHub integration |
| 5 | SonarQube | Quality + Security | Broadest scope (bugs, smells, security) |

### Recommended Stack for ADE

| Tool | Purpose | Why |
|------|---------|-----|
| **Semgrep** | Security scanning | Lightweight, scriptable, multi-language, free community rules |
| **Ruff** | Python linting | 10-100x faster than flake8, replaces isort/black/flake8 |
| **ESLint** | JS/TS linting | Industry standard, extensive rule ecosystem |
| **Prettier** | Code formatting | Multi-language formatter, opinionated |

### Why Not SonarQube?

- Heavier setup (requires server)
- Better suited for CI/CD pipelines than local dev agents
- Semgrep covers security findings sufficiently for local use
- Can be added in CI/CD as a complement (future consideration)

### Agentic Code Review Statistics (2026)

- 79% of teams now use agentic review tools
- 45% improvement in review speed
- 38.7% of AI review comments lead to actual fixes
- PR-native enforcement is becoming mandatory with increased agent throughput

---

## 6. Hardware Optimization for Dual-Model Setup

### RTX 5090 Memory Budget (32GB GDDR7)

```
Scenario: Concurrent Loading (Recommended)
┌────────────────────────────────────┐
│ Gemma 4 31B (Q4_K_M):     18.0 GB │
│ Qwen 2.5 Coder 14B (Q4):  10.0 GB │
│ KV Cache + Overhead:        4.0 GB │
│ ─────────────────────────────────  │
│ Total:                     32.0 GB │ ← Tight but feasible
└────────────────────────────────────┘

Scenario: Hot-Swap (If concurrent is unstable)
┌────────────────────────────────────┐
│ Active Model:              18.0 GB │
│ KV Cache (large context):  10.0 GB │
│ Headroom:                   4.0 GB │
│ ─────────────────────────────────  │
│ Total:                     32.0 GB │ ← More room per model
└────────────────────────────────────┘
```

### Performance Expectations

| Metric | Gemma 4 31B (Q4) | Qwen 2.5 14B (Q4) |
|--------|-------------------|---------------------|
| Tokens/sec (generation) | ~35-50 t/s | ~60-80 t/s |
| Context load time | ~2-5s | ~1-3s |
| Memory (inference) | 18 GB | 10 GB |
| Recommended context | 128K | 64K |

### AMD 9950X3D Advantage

The 144MB 3D V-Cache is valuable for:
- KV-cache operations during inference
- CrewAI orchestration overhead
- Parallel test execution
- Static analysis tool execution

CPU handles all non-GPU workloads without contention.

---

## 7. Security Considerations for Agentic Development

### OWASP Top 10 for Agentic Applications (2026)

This is the first industry standard for agentic AI security:

1. **Prompt Injection** — Agents executing malicious instructions from code comments
2. **Broken Access Control** — Agents accessing files/systems beyond their scope
3. **Data Exfiltration** — Code or secrets leaking through model prompts
4. **Unsafe Code Execution** — Agents running arbitrary commands
5. **Excessive Permissions** — Agents with broader access than needed

### Mitigation Strategy for ADE

1. **Command allowlist** — Only pre-approved commands can be executed
2. **File write restrictions** — Only files listed in the plan can be modified
3. **No network access** — Agents cannot curl, wget, or access external services
4. **No credential access** — .env, .ssh, credentials files are blocked
5. **Branch isolation** — Agents work only on feature branches, never main
6. **Audit logging** — Every agent action is logged with full context
7. **Circuit breaker** — Max iteration limits prevent runaway execution

### Industry Context

- 48% of cybersecurity professionals identify agentic AI as #1 attack vector (2026)
- E2B sandbox sessions grew from 40K/month to 15M/month in one year
- ~50% of Fortune 500 now running agent workloads
- Sandboxing and access control are mandatory, not optional

---

## 8. Mature AI-Augmented SDLC Patterns

### Industry Maturity Levels (2026)

| Level | Description | % of Teams |
|-------|-------------|-----------|
| 1 — Ad hoc | Using ChatGPT/Copilot occasionally | 30% |
| 2 — Experimental | Testing coding agents on side projects | 40% |
| 3 — Intentional | Agents integrated into daily workflow | 25% |
| 4 — Systematic | Full agentic SDLC with guardrails | 4% |
| 5 — Autonomous | Agents handle most coding autonomously | 1% |

ADE targets **Level 4** — systematic agentic SDLC with human oversight at key checkpoints.

### Canonical 5-Phase Pattern

Industry consensus has converged on this flow:

1. **Plan**: AI extracts use cases, dependencies, risks from requirements
2. **Implement**: Autonomous multi-file coding with continuous testing
3. **Review**: AI-driven static analysis + deep reasoning review
4. **Test**: Agentic test generation with impact analysis
5. **Document**: Auto-generated docs, changelogs, PR descriptions

ADE adds Phase 1.5 (Design Check) as an innovation for catching architectural drift early.

### Efficiency Benchmarks

- Teams with 12+ months agentic experience: 10-30% improvement in specific tasks
- Top 5% optimized teams: 50% faster incident response
- Agentic code review: 45% faster than manual review

---

## Sources

### Agentic SDLC & Frameworks
- OpenHands Official — openhands.dev
- 15 Best Claude Code Alternatives (2026) — taskade.com
- SDLC for Agentic AI Engineering (March 2026) — medium.com/@brettluelling
- Agentic Coding Tools Setup Guide — ikangai.com
- AI-Led SDLC with Azure and GitHub — Microsoft Tech Community
- Sonar: AI Agents in SDLC — sonarsource.com

### Local LLM & Ollama
- Gemma 4 Announcement — blog.google
- Gemma 4 on Ollama — ollama.com/library/gemma4
- Top 5 Open-Source Coding LLMs Ranked 2026 — index.dev
- Best Local LLM Models 2026 — sitepoint.com
- Optimizing Local LLM Context for Agentic Coding — tkamucheka.github.io
- Ollama 2026 Guide — textify.ai

### Multi-Agent Frameworks
- LangGraph vs CrewAI vs AutoGen — o-mega.ai
- CrewAI vs LangGraph vs AutoGen — datacamp.com
- Multi-Agent Frameworks for Enterprise 2026 — adopt.ai
- Open-Source AI Agent Framework Comparison — langfuse.com

### Quality Assurance
- Top AI SAST Tools 2026 — dryrun.security
- Semgrep vs SonarQube 2026 — dev.to
- State of AI Code Review 2026 — dev.to
- Semgrep Security Platform — semgrep.dev

### Security
- Practical Security Guidance for Sandboxing — NVIDIA Developer Blog
- Code Execution Risks in Agentic AI 2026 — apiiro.com
- Securing the Agentic Development Lifecycle — cycode.com
- OWASP Top 10 for Agentic Applications

### Hardware
- GPU Memory for LLMs — medium.com
- Running Multiple LLMs GPU Memory Management — dasroot.net
- Splitting LLMs Across Multiple GPUs — digitalocean.com

---

## 9. Orchestration Architecture — Deep Research (v2 Findings)

### Claude Code as Orchestrator

Claude Code is a **TypeScript-based agentic system** with a QueryEngine that orchestrates planning and execution. It includes ~40 discrete tools, a permission-gated tool system, and multi-strategy context management.

**Key capabilities for orchestration**:
- **Subagent spawning**: Each subagent gets its own context window, tool allowlist, and isolation
- **Git worktree support**: Native `--worktree` flag — each subagent gets its own isolated worktree
- **Hooks system**: PreToolUse, PostToolUse, SessionStart, SessionEnd callbacks
- **Session persistence**: Capture session_id and resume with full context
- **Custom commands**: `.claude/commands/*.md` for repeatable workflows
- **CLAUDE.md**: Project-level memory and workflow instructions

**Why NOT a custom Python CLI**: Claude Code already provides the agent loop, error handling, context management, and tool execution that a custom CLI would need to reimplement.

**Limitation**: No cross-session state management — each invocation is independent. Mitigated by file-based state in `.ade/tasks/`.

### Claude Agent SDK

The Claude Code SDK was renamed to **Claude Agent SDK** — the production API behind Claude Code. It gives programmatic access to subagents, tools, hooks, and session management in Python/TypeScript. **However**, it requires API billing (separate from Max Pro subscription), making it unsuitable for the cost model in v1.

**Future consideration**: When API costs are acceptable, migrating from Claude Code CLI to Agent SDK would provide tighter programmatic control.

### Agent Teams (Experimental)

Claude Code's agent teams feature enables multiple Claude Code instances with shared task lists and inter-agent messaging. **Status**: Experimental, disabled by default, with known limitations (no session resumption, slow shutdown, one team per session). **Not recommended for v1** — wait for GA.

### Git Worktrees for Agent Isolation

Git worktrees have become **foundational infrastructure for parallel AI agent development** (2025-2026):
- Each agent gets its own working directory on its own branch, preventing file conflicts
- Companies like incident.io routinely run 4-5 parallel Claude agents via worktrees
- Claude Code supports `--worktree` natively (2026)
- Each subagent automatically gets an isolated worktree, temporary branch, and repo copy
- Worktrees share the same `.git` directory — efficient disk usage

**Best practices**:
- Use worktrees (not branches or clones) for per-task isolation
- Sequential git operations (avoid parallel git writes to prevent silent corruption)
- 5-10 second creation/cleanup overhead (acceptable for phase transitions)

### Scanning Orchestration — Pre-commit Framework

**Pre-commit** is the standard for orchestrating multiple scanning tools:
- Reads `.pre-commit-config.yaml`, auto-installs hooks in isolated environments
- Parallelizes hook execution
- Supports auto-fix with commit integration
- Language-agnostic, works with Semgrep, Ruff, ESLint, Prettier, detect-secrets

**MegaLinter** is the unified alternative (50 languages, Python-based, parallel execution) — recommended for v2 if pre-commit becomes insufficient.

**Biome** is emerging as a unified ESLint + Prettier replacement for JS/TS — monitor for v2.

### Production Agent Architecture Patterns

**OpenHands**: Python SDK, event-sourced state, sandboxed execution, 2026 focus on multi-agent orchestration
**Devin AI**: Compound AI system (planner + coder + critic), dynamic re-planning, parallel instance spawning
**Temporal.io**: Used by OpenAI Codex and Replit Agent for durable execution, retry semantics, state persistence

**Common patterns**:
- Orchestrator decides workflow state, agents decide tactical actions
- Structured intent output (LLM → structured format → orchestrator validates)
- Explicit state/transition definitions (not freestyle LLM)
- Checkpoint-based recovery at phase boundaries

### Sources (v2 Research)

- Claude Code overview — code.claude.com/docs/en/overview
- Agent SDK overview — platform.claude.com/docs/en/agent-sdk/overview
- Orchestrate teams of Claude Code sessions — code.claude.com/docs/en/agent-teams
- Create custom subagents — code.claude.com/docs/en/sub-agents
- Inside Claude Code Architecture Deep Dive — zainhas.github.io
- The Code Agent Orchestra — addyosmani.com/blog/code-agent-orchestra
- Using Git Worktrees for Multi-Feature Development with AI Agents — nrmitchi.com
- How Git Worktrees Changed My AI Agent Workflow — nx.dev
- Shipping faster with Claude Code and Git Worktrees — incident.io/blog
- MegaLinter — megalinter.io
- Pre-commit framework — pre-commit.com
- Biome: The ESLint and Prettier Killer — dev.to
- OpenHands SDK — arxiv.org/html/2511.03690v1
- AI Agent Architecture: Build Systems That Work in 2026 — redis.io
- Agentic AI Workflows: Why Orchestration with Temporal is Key — intuitionlabs.ai
