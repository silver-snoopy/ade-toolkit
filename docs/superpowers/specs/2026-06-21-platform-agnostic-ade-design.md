# Design: Platform-agnostic ADE (skills-first, cross-harness)

**Date:** 2026-06-21
**Status:** accepted (grilled & refined 2026-06-21) — implementation plan pending. See ADR-0003.
**Type:** feature / architecture
**Supersedes the cross-harness "absent (by design)" gap** flagged in `docs/ade-sdlc-gap-analysis-2026-06.html`.

## Goal

Make ADE **platform-agnostic** — a first-class experience on **Claude Code, OpenAI Codex CLI, Google Gemini CLI, and GitHub Copilot** — without diluting the rigor ADE leads on (iterative-retrieval research, Chain-of-Verification with a spec-blind verifier, hook-enforced author-separated TDD, blast-radius routing, the compound loop).

Three sub-goals from the request, resolved by research:

1. **Multi-environment** — all four harnesses are first-class targets.
2. **Distribution** — keep it "no big deal"; `uvx` for zero-install (the npx-equivalent for a Python tool) + each tool's native skill loader (`gh skill`, …). **Not** a Node rewrite in V1 (a Node migration is a deliberate later decision).
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

### Deterministic gates: native PreToolUse hooks on all four (verified)

Skills are model-invoked and ignorable, so ADE's hard gates (G1 author-separation, G2 stub/leftover, G4 escalation floor) live in the deterministic hook layer. **All four harnesses ship native lifecycle hooks** with a near-identical taxonomy and the **same JSON-over-stdin contract** Claude uses:

| Harness | PreToolUse deny? | Wiring |
|---|---|---|
| Claude Code | ✅ | `.claude/settings.json` |
| Gemini CLI | ✅ (PreToolUse can block) | `.gemini/settings.json` ([docs](https://geminicli.com/docs/hooks/)) |
| GitHub Copilot | ✅ (`preToolUse` deny/modify) | `.github/hooks/*.json` ([docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks)) |
| OpenAI Codex | ✅ (blocking hooks reject calls) | `hooks.json` / `[hooks]` in `config.toml` ([docs](https://developers.openai.com/codex/hooks)) |

Because ADE's three hook scripts already share a JSON-stdin `_hooklib`, the **same scripts wire into all four** harnesses' native hook systems — `_hooklib` gains a thin per-harness envelope parser (event field names differ; Copilot uses camelCase). This gives **proactive PreToolUse deny, in-session, on every target** — stronger than commit-time gating. **`git pre-commit` is demoted to an optional belt-and-suspenders fallback** (non-ADE commits / CI). This upgrades G2 from Claude-only/partial to a **cross-harness, leader-class** deterministic layer.

### No personas (evidence-based)

The persona research is decisive: role/persona assignment **does not reliably improve objective-task quality and often degrades it** (degraded reasoning on 7/12 datasets, [arXiv:2408.08631](https://arxiv.org/abs/2408.08631); no significant objective gain, [arXiv:2311.10054](https://arxiv.org/abs/2311.10054)). Critically:

- The writer/reviewer benefit ADE relies on comes from **context isolation, not persona** ([Cross-Context Review arXiv:2603.12123](https://arxiv.org/pdf/2603.12123); [CoVe arXiv:2309.11495](https://arxiv.org/abs/2309.11495); Anthropic and Cognition attribute subagent value to separation-of-concerns with zero persona attribution).
- LLM-as-judge is highly sensitive to **authority/framing cues** ([arXiv:2604.16790](https://arxiv.org/html/2604.16790v1)) — so adding "you are a senior X" to ADE's blind verifier would *inject* the very bias its design eliminates. Personas are a regression for ADE specifically.

**Decision: keep function-named, capability-organized skills. No personas** beyond optional human-legibility labels. The blind verifier stays unlabeled.

## Design

### Organizing model — skills-first, function-named, no command layer

ADE's pipeline is authored as **one Agent Skill per phase** (SKILL.md, function-named): `ade-intent`, `ade-research`, `ade-plan`, `ade-design-check`, `ade-implement`, `ade-quality-gate`, `ade-review`, `ade-docs`, `ade-ship`, `ade-retro` — plus the end-to-end **driver skill** (`ade-pipeline`, the former `ade-full`) that sequences Phases 0→9, with frontmatter marking it **user-invoked** so the strict ordering never depends on probabilistic auto-activation.

A **phase skill carries the procedure** (steps, exit criteria) and **dispatches worker subagents** for the isolation-critical steps (e.g. `ade-implement` dispatches `test-writer` then `implementer`; `ade-research` dispatches scouts + spec-verifier). There is **no sub-phase skill splitting** — sub-sequences (TDD red→green, research R1–R5) are procedure inside the phase skill, not separate skills. This keeps a small surface (~10 phase skills + driver + ~6 workers, matching the phases in `CONTEXT.md`) and lean descriptions for Codex's 8 KB discovery budget. (Exact skill set is refinable later.)

**The separate slash-command layer is retired.** Claude Code has merged custom commands into skills (`.claude/commands/*.md` and `.claude/skills/<name>/SKILL.md` both produce `/<name>`; invocation-control frontmatter decides who triggers it — verified at [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)), and the other three harnesses are skill-native. So ADE authors **only Agent Skills** — there is no `.claude/commands/` tree to emit or maintain. A skill meant to be explicitly invoked sets its frontmatter accordingly; the harness surfaces it as `/<name>` wherever slash invocation exists.

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
    ├── hooks/            # 3 deterministic hooks + _hooklib (+ per-harness JSON-envelope parser)
    ├── AGENTS.md.j2      # canonical instruction superset
    └── ...               # routing/stack config, memory pointers
```

The harness layer is **thin**: the SKILL.md *content* is identical everywhere; adapters only handle **placement** (which dir) and **small deltas** (Codex TOML subagent format + 8 KB-aware lean descriptions; per-harness memory-file name). This is much smaller than a full per-harness content compiler — the skills layer absorbs most of the portability work.

### Emitted layout (per `ade init --agent <targets>`)

`--agent` accepts a comma-separated list (`claude,gemini,codex,copilot`) or `all`, and **defaults to `claude`** for backward compatibility. Each selected target gets the emission below.

- **Skills (portable core):** canonical SKILL.md folders (`ade-research/`, `ade-implement/`, …) → `.agents/skills/` (Gemini + Copilot) and `.claude/skills/` (Claude); Codex skills location as verified at build time. Content identical; one authoring source.
- **Worker subagents (thin adapter):** the handful of context-isolated workers (scout, test-writer, implementer, spec-verifier, reviewers, compounder) → per-harness subagent files (`.md`/`.agent.md`/`.toml`). Skills dispatch these where the harness supports it.
- **Instructions:** ADE's workflow instructions authored **once as `AGENTS.md`** (repo root). Codex reads it natively; Claude/Gemini/Copilot get a **thin ADE-managed delimited block** in their memory file (`CLAUDE.md` / `GEMINI.md` / `.github/copilot-instructions.md`) that imports it (`@AGENTS.md` where supported, else a one-line "ADE workflow: see `./AGENTS.md`"). ADE only ever manages its own block; the user's own content is untouched.
- **Deterministic gates:** ADE **renders the hook scripts** (`block-mixed-commit`, `check-leftover-stub`, `check-escalation-paths` + `_hooklib`) from its templates **into each selected harness's own tree**, and wires them as that harness's **native PreToolUse hooks** (`.claude/settings.json`, `.gemini/settings.json`, Codex `hooks.json`/`[hooks]`, `.github/hooks/`). **No shared `.ade/` copy** — each harness is self-contained, and the scripts are ADE-owned (regenerated on every `init`, never user-edited), so per-harness duplication carries no drift risk. `_hooklib` parses each harness's JSON envelope. `git pre-commit` is an **optional fallback** for non-ADE commits / CI.
- **Config (user-owned):** routing + stack config are seed-if-missing and *edited by the user*, so they are **not** duplicated per-harness (that would diverge). Single copy in **`.ade/`** (the ADE-specific home; committed — only `.ade/tasks/` + `.ade/worktrees/` are gitignored). Per-harness hook copies read `.ade/ade-routing.json` by relative path; the escalation hook already fail-safes to `≥ standard` when the config is missing/unparseable. **Split rule:** `.ade/` holds ADE's own content (user-owned config + ephemeral state); each harness dir holds *that harness's* generated artifacts (skills, worker defs, hooks). Hooks are ADE-owned and emitted per-harness; config is user-owned and lives once in `.ade/`.

### Compound knowledge — repo-versioned, harness-neutral

The compound loop's durable outputs — **Learnings** (`docs/learnings/`) and the **Calibration corpus** (`docs/review-calibration.md`) — stay **version-controlled in `docs/`**, harness-neutral. Every harness's skills read and write the *same* committed files, which is what makes the compound loop work when one repo is driven from different tools or machines. This matches the field norm — compound-engineering (`docs/solutions/` + `CONCEPTS.md`), LeRisque (`docs/review-calibration.md`), gsd (`.planning/`), case (retrospective + `working-memory.json`) all keep compounded knowledge committed in the repo, never in a tool-specific dir. Specs and ADRs likewise remain in `docs/`. **Rule:** durable project knowledge → `docs/` (versioned, reviewable); ADE config + ephemeral state → `.ade/`; generated artifacts → per-harness dirs.

### Codex degraded tier (explicit)

Codex gets SKILL.md skills + TOML worker subagents + native Codex **hooks** (`hooks.json`/`[hooks]`) + `AGENTS.md`, **plus** a generated note that ADE's autonomous orchestration requires the user to grant delegation, or runs phases **sequentially** (single context), until `openai/codex#18513` lands. Honest, shipped, with a clear upgrade path. The degradation is *orchestration only*: author-separation and the blind verifier lose their isolation guarantee and become in-context conventions — but Codex's **native PreToolUse hooks still deterministically enforce** G1/G2/G4 (and `git pre-commit` remains as fallback), so the hard gates hold even when isolation doesn't.

### Distribution

- Keep the **Python core** for V1 and `pip install ade-toolkit`.
- Primary UX: **`uvx ade-toolkit init …`** — the zero-install, one-liner equivalent of `npx` for a Python tool (Spec-Kit-style). This delivers the "ease of npx" without a rewrite.
- The generated skills are *also* independently installable via each tool's native loader (`gh skill install`, Gemini/Copilot loaders) for users who want just the skills; the full pipeline (skills + workers + hooks + config + `AGENTS.md`) comes from `ade init`.
- **A Node/npx migration is an explicit later decision**, deliberately deferred out of V1 (not foreclosed) — revisit if Node-ecosystem reach/discoverability becomes a priority.

### Eval in V1 — skill-quality gate only

V1 adds a **static-only skill-*quality* gate** (PluginEval-style, à la `wshobson/agents`): deterministic, free, offline checks — well-formed SKILL.md, required frontmatter, description lean enough for Codex's 8 KB budget, anti-patterns. Exposed via `ade eval` and runnable in CI. The **LLM-judge (semantic) layer moves to V2** (it needs API calls and is Claude-centric to run — shouldn't gate a cross-harness V1), and **cross-harness *behavioral* benchmarking** (does the pipeline ship good code on Gemini vs Codex) is also **V2** (requires running each tool live).

### Migration & versioning (v3.0.0)

The layout contract changes, so this ships as **v3.0.0**. An **`ade migrate`** command handles existing (v2) trees idempotently: moves user-owned config (`.claude/ade-routing.json`, `ade-stack.md`) → `.ade/`; regenerates skills in SKILL.md form; removes stale generated files (old command-style `skills/ade/*.md`, `.claude/commands/ade_*`); creates `AGENTS.md` and rewrites the `CLAUDE.md` ADE-block to a pointer. ADE-generated files are always safe to overwrite; the only state-preserving step is the **user-owned config move**. `ade init` on a detected v2 tree points the user to `ade migrate` rather than silently leaving cruft. The architecture shift is recorded in **ADR-0003** (skills-first, cross-harness, no-personas).

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
| Codex can't autonomously dispatch | Ship a documented **degraded/sequential tier**; native Codex **hooks** (+ pre-commit fallback) still enforce the hard gates; revisit on `#18513`. |
| SKILL.md auto-activation unreliable for a strict pipeline | Explicit **`ade-pipeline`** driver sequences phases; don't rely on description-matching for ordering. |
| Codex 8 KB discovery budget | Keep skill **descriptions lean**; the quality gate flags overruns. |
| Skills can't enforce gates | Enforcement lives in **native PreToolUse hooks on all four harnesses** (same scripts, per-harness wiring), not in skills; `git pre-commit` is the fallback. |
| Per-harness hook **envelope** differs (field names, camelCase) | One shared script set; `_hooklib` gains a thin per-harness JSON-envelope parser. Verify each harness's payload shape at build time. |
| `.agents/skills/` read-support varies by tool | Emit to `.agents/skills/` **and** the per-harness skills dir; verify Codex's location at build time. |

## Testing

- **Golden-file tests** per harness: canonical skill/worker → expected emitted layout.
- **Skill-quality static checks** run as tests (and shipped as `ade eval`).
- **`ade init --agent all`** integration test produces a valid tree for every harness.
- Existing 84 tests pin current Claude output so the refactor is regression-safe.

## Rollout

**v3.0.0 ships all four harnesses (Claude, Gemini, Copilot, Codex) in one release.** The steps below are the internal build order — each independently mergeable behind the v3.0.0 milestone — not separate releases.

1. **Adapter abstraction + skills-first refactor on Claude** — author the pipeline as SKILL.md phase skills that dispatch worker subagents; emit to `.claude/skills/` + `.agents/skills/`; per-harness hook-emission framework. *Regression-safe — existing tests pin Claude output.*
2. **Canonical `AGENTS.md` + thin per-harness memory pointers**; move user-owned config → `.ade/`; ship **`ade migrate`** (v2 → v3).
3. **Gemini, Copilot, and Codex adapters** — worker-def emission (`.md` / `.agent.md` / `.toml`), skills placement, and native hook wiring per harness; Codex degraded/sequential tier.
4. **Skill-quality eval gate** (`ade eval`).
5. **Distribution**: `uvx` UX + docs; verify each harness's skills/hook locations against current vendor docs at build time.

## Open questions (resolve during planning/implementation)

- Does Codex CLI read `.agents/skills/`, or must skills go in a Codex-specific dir? (Verify against current Codex docs at build time.)
- Exact per-harness hook JSON-envelope field names (esp. Copilot camelCase) for `_hooklib`'s parser — verify each payload shape at build time.
- V2: persona-flavored *review lenses* on generator agents only (never the blind verifier) — measure whether they widen issue coverage without reintroducing authority bias.
- V2: behavioral cross-harness eval harness.

## References

- Portability research run `wf_506e3f60-b75`; persona research run `wf_d444ff6c-1bc`; field study `docs/ade-sdlc-gap-analysis-2026-06.html`.
- Agent Skills standard — agentskills.io; Claude/Gemini/Copilot/Codex skills docs.
- Cross-harness compiler prior art — `wshobson/agents` (Python; PluginEval).
- Persona efficacy — arXiv:2408.08631, 2311.10054, 2506.20020; Cross-Context Review arXiv:2603.12123; CoVe arXiv:2309.11495; self-correction arXiv:2310.01798; LLM-judge bias arXiv:2604.16790.
- Codex autonomy gap — `openai/codex#18513`.
