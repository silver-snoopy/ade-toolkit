# Design: Platform-agnostic ADE (skills-first, cross-harness)

**Date:** 2026-06-21
**Status:** draft (awaiting review)
**Type:** feature / architecture
**Supersedes the cross-harness "absent (by design)" gap** flagged in `docs/ade-sdlc-gap-analysis-2026-06.html`.

## Goal

Make ADE **platform-agnostic** — a first-class experience on **Claude Code, OpenAI Codex CLI, Google Gemini CLI, and GitHub Copilot** — without diluting the rigor ADE leads on (iterative-retrieval research, Chain-of-Verification with a spec-blind verifier, hook-enforced author-separated TDD, blast-radius routing, the compound loop).

Three sub-goals from the request, resolved by research:

1. **Multi-environment** — all four harnesses are first-class targets.
2. **Distribution** — keep it "no big deal"; lean on the skills ecosystem's native loaders + a thin `uvx`/`npx`/`gh skill` path. **Not** a Node rewrite.
3. **Skills format** — adopt **SKILL.md (Agent Skills)** as the portable unit.

## What the research established

Two deep-research runs (cross-harness portability; personas) plus direct primary-source verification. Full findings: `wf_506e3f60-b75` (portability), `wf_d444ff6c-1bc` (personas).

### SKILL.md is real, native, and portable across all four targets

Verified from each vendor's own docs — Agent Skills (SKILL.md) is a first-party, natively-consumed format across **all four** targets and ~40 tools total ([agentskills.io](https://agentskills.io)):

| Harness | Skills support | Skills dir(s) it reads |
|---|---|---|
| Claude Code | native | `.claude/skills/` |
| Gemini CLI | native | `.gemini/skills/`, **`.agents/skills/`** (alias, higher precedence) |
| GitHub Copilot | native (since 2025-12) | `.github/skills/`, `.claude/skills/`, **`.agents/skills/`**; `gh skill` installer |
| OpenAI Codex | native | Codex skills (8 KB *discovery-list* budget; full SKILL.md loads on activation) |

The decisive convenience: a **converging shared location, `.agents/skills/`**, that multiple tools read directly — so distribution is largely "drop SKILL.md folders into one dir."

### Skills give portable *capabilities*, not portable *orchestration*

A SKILL.md is a progressive-disclosure instruction module loaded into the **current** agent's context. It is **not** a subagent/isolation mechanism. ADE's rigor (spec-verifier never sees the spec; test-writer ≠ implementer; parallel scouts) depends on **context isolation**, which comes from each harness's **native subagent** feature — full on Claude/Gemini/Copilot, **user-gated/degraded on Codex** (`openai/codex#18513` tracks autonomous mode). Skills *invoke* those subagents; they do not replace them.

### Deterministic gates are not skills

Skills are model-invoked and ignorable. ADE's hard gates (G1 author-separation, G2 stub/leftover, G4 escalation floor) must stay as **`git pre-commit`** (the existing 3 hooks + `_hooklib`), the only enforcement that works identically everywhere. Claude's PreToolUse wiring remains a native bonus on top.

### No personas (evidence-based)

The persona research is decisive: role/persona assignment **does not reliably improve objective-task quality and often degrades it** (degraded reasoning on 7/12 datasets, [arXiv:2408.08631](https://arxiv.org/abs/2408.08631); no significant objective gain, [arXiv:2311.10054](https://arxiv.org/abs/2311.10054)). Critically:

- The writer/reviewer benefit ADE relies on comes from **context isolation, not persona** ([Cross-Context Review arXiv:2603.12123](https://arxiv.org/pdf/2603.12123); [CoVe arXiv:2309.11495](https://arxiv.org/abs/2309.11495); Anthropic and Cognition attribute subagent value to separation-of-concerns with zero persona attribution).
- LLM-as-judge is highly sensitive to **authority/framing cues** ([arXiv:2604.16790](https://arxiv.org/html/2604.16790v1)) — so adding "you are a senior X" to ADE's blind verifier would *inject* the very bias its design eliminates. Personas are a regression for ADE specifically.

**Decision: keep function-named, capability-organized skills. No personas** beyond optional human-legibility labels. The blind verifier stays unlabeled.

## Design

### Organizing model — skills-first, function-named

ADE's pipeline and worker behaviors are authored as **SKILL.md Agent Skills**, named by function (e.g. `ade-research`, `ade-plan`, `ade-tdd-red`, `ade-tdd-green`, `ade-quality-gate`, `ade-review`, `ade-codify`). A top-level **`ade-pipeline`** skill/command sequences Phases 0→9 deterministically — the strict ordering is driven explicitly, **not** left to probabilistic auto-activation.

### Components

```
src/ade/
├── cli.py                # init/doctor/(eval); orchestrates emission per selected harness
├── detect.py             # stack detection (unchanged)
├── harnesses/            # NEW — thin per-harness emitter (placement + small deltas, NOT a content compiler)
│   ├── base.py           # HarnessTarget: skills_dir, agent_dir/ext, memory_file, hook_substrate
│   ├── claude.py  gemini.py  copilot.py  codex.py
└── templates/
    ├── skills/           # canonical SKILL.md sources (folder per skill: SKILL.md + refs/scripts)
    ├── agents/           # canonical worker definitions (tier + tools + body) for context-isolated workers
    ├── hooks/            # 3 deterministic hooks + _hooklib (unchanged)
    ├── AGENTS.md.j2      # canonical instruction superset
    └── ...               # routing/stack config, memory pointers
```

The harness layer is **thin**: the SKILL.md *content* is identical everywhere; adapters only handle **placement** (which dir) and **small deltas** (Codex TOML subagent format + 8 KB-aware lean descriptions; per-harness memory-file name). This is much smaller than a full per-harness content compiler — the skills layer absorbs most of the portability work.

### Emitted layout (per `ade init --agent <targets>`)

`--agent` accepts a comma-separated list (`claude,gemini,codex,copilot`) or `all`, and **defaults to `claude`** for backward compatibility. Each selected target gets the emission below.

- **Skills (portable core):** canonical SKILL.md folders → `.agents/skills/` (Gemini + Copilot) and `.claude/skills/ade/` (Claude); Codex skills location as verified at build time. Content identical; one authoring source.
- **Worker subagents (thin adapter):** the handful of context-isolated workers (scout, test-writer, implementer, spec-verifier, reviewers, compounder) → per-harness subagent files (`.md`/`.agent.md`/`.toml`). Skills dispatch these where the harness supports it.
- **Instructions:** canonical **`AGENTS.md`** + thin per-harness pointers (`CLAUDE.md` / `GEMINI.md` / `.github/copilot-instructions.md`) that include/reference it.
- **Deterministic gates:** `git pre-commit` (always) + `.claude/settings.json` PreToolUse (Claude only, bonus).
- **Shared config:** routing + stack config in a harness-neutral location both skills and hooks read.

### Codex degraded tier (explicit)

Codex gets SKILL.md skills + TOML worker subagents + `AGENTS.md`, **plus** a generated note that ADE's autonomous orchestration requires the user to grant delegation, or runs phases **sequentially** (single context), until `openai/codex#18513` lands. Honest, shipped, with a clear upgrade path. Author-separation and the blind verifier degrade to in-context conventions on Codex; the `git pre-commit` gate still enforces G1/G2/G4 there.

### Distribution

- Keep the **Python core** and `pip install ade-toolkit`.
- Promote **`uvx ade-toolkit init …`** for zero-install (Spec-Kit-style).
- Skills are also installable via each tool's native loader (`gh skill install`, Gemini/Copilot loaders) or a thin **`npx` copier** into `.agents/skills/`.
- **No Node rewrite** — `npx` is a convenience shim, not the runtime.

### Eval in V1 — skill-quality gate only

V1 adds a **PluginEval-style skill-*quality* gate** (à la `wshobson/agents` PluginEval): cheap static analysis (well-formed SKILL.md, required frontmatter, lean description for the 8 KB budget, anti-patterns) + optional LLM-judge. Exposed via `ade eval` and/or CI. **Cross-harness *behavioral* benchmarking** (does the pipeline ship good code on Gemini vs Codex) is **V2** — it requires running each tool live and is expensive.

## Non-goals (V1)

- Personas as an architecture (rejected on evidence) — at most optional legibility labels.
- A full per-harness *content* compiler (the skills layer makes it unnecessary).
- An external runtime orchestrator (MCP+tmux, CAO-style) — heavy runtime, different product.
- Guaranteed Codex autonomy (blocked upstream).
- Behavioral cross-harness eval (V2).
- Guaranteeing identical orchestration semantics on all four (Codex is explicitly degraded).

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Format churn (all four shipped subagents/skills in the last ~6 months) | Bet on the **open** standards (SKILL.md, AGENTS.md); keep the harness layer thin so deltas are cheap to track. |
| Codex can't autonomously dispatch | Ship a documented **degraded/sequential tier**; pre-commit still enforces the hard gates; revisit on `#18513`. |
| SKILL.md auto-activation unreliable for a strict pipeline | Explicit **`ade-pipeline`** driver sequences phases; don't rely on description-matching for ordering. |
| Codex 8 KB discovery budget | Keep skill **descriptions lean**; the quality gate flags overruns. |
| Skills can't enforce gates | **`git pre-commit`** retained as the universal hard layer. |
| `.agents/skills/` read-support varies by tool | Emit to `.agents/skills/` **and** the per-harness skills dir; verify Codex's location at build time. |

## Testing

- **Golden-file tests** per harness: canonical skill/worker → expected emitted layout.
- **Skill-quality static checks** run as tests (and shipped as `ade eval`).
- **`ade init --agent all`** integration test produces a valid tree for every harness.
- Existing 84 tests pin current Claude output so the refactor is regression-safe.

## Rollout (phased — each independently mergeable)

1. **Author the pipeline as SKILL.md skills** + emit to `.agents/skills/` and `.claude/skills/` (Claude/Gemini/Copilot get skills immediately). Keep current Claude workers. *Regression-safe.*
2. **Canonical `AGENTS.md` + per-harness memory pointers**; move shared config to a neutral location.
3. **Thin worker-subagent emitter** for Gemini + Copilot, then Codex (TOML, degraded tier).
4. **Skill-quality eval gate** (`ade eval`).
5. **Distribution polish**: `uvx` docs, optional `npx` copier, `gh skill` packaging.

## Open questions (resolve during planning/implementation)

- Does Codex CLI read `.agents/skills/`, or must skills go in a Codex-specific dir? (Verify against current Codex docs at build time.)
- Exact neutral location for shared routing/stack config + hooks so both skills and pre-commit read one copy.
- V2: persona-flavored *review lenses* on generator agents only (never the blind verifier) — measure whether they widen issue coverage without reintroducing authority bias.
- V2: behavioral cross-harness eval harness.

## References

- Portability research run `wf_506e3f60-b75`; persona research run `wf_d444ff6c-1bc`; field study `docs/ade-sdlc-gap-analysis-2026-06.html`.
- Agent Skills standard — agentskills.io; Claude/Gemini/Copilot/Codex skills docs.
- Cross-harness compiler prior art — `wshobson/agents` (Python; PluginEval).
- Persona efficacy — arXiv:2408.08631, 2311.10054, 2506.20020; Cross-Context Review arXiv:2603.12123; CoVe arXiv:2309.11495; self-correction arXiv:2310.01798; LLM-judge bias arXiv:2604.16790.
- Codex autonomy gap — `openai/codex#18513`.
