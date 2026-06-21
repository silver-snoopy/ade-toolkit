# 0003 — Platform-agnostic, skills-first ADE

**Status:** accepted (2026-06-21)

To make ADE first-class on Claude Code, Codex CLI, Gemini CLI, and GitHub Copilot, we author the pipeline as **Agent Skills (SKILL.md)** — the open, cross-tool standard natively consumed by all four — with a **thin per-harness layer** for the things that genuinely differ. We chose this over a heavyweight per-harness content compiler because the skills standard absorbs most of the portability work, and over a Node/npx rewrite because it buys nothing a Python tool run via `uvx` doesn't already give.

## Decision

- **Two layers.** Portable **Agent Skills** carry behavior (one skill per phase, dispatching workers; a user-invoked `ade-pipeline` driver sequences 0→9). A **thin per-harness worker-subagent layer** (`.md`/`.agent.md`/`.toml`) provides the *context isolation* ADE's rigor depends on (blind verifier, author-separated TDD), since SKILL.md has no model/tools/isolation fields.
- **Retire the slash-command layer** — Claude Code merged custom commands into skills, and the other three are skill-native; ADE authors only skills.
- **Deterministic gates = native PreToolUse hooks on all four** (same scripts, per-harness wiring via `_hooklib`); `git pre-commit` is a fallback.
- **No personas** — the rigor comes from context isolation, not role identity; persona/authority framing is net-neutral-to-harmful on objective tasks and would bias the blind verifier.
- **Layout:** durable knowledge (specs, ADRs, learnings, calibration) in `docs/`; ADE config + ephemeral state in `.ade/`; generated artifacts in per-harness dirs; instructions authored once as `AGENTS.md` with thin per-harness memory pointers.
- **Distribution:** keep Python; `uvx ade-toolkit` for the npx-style zero-install. Ships as **v3.0.0** (breaking layout) with an **`ade migrate`** path; all four harnesses in that one release.

## Considered options (rejected)

- **Per-harness content compiler** (translate everything per harness) — heavier than needed; the skills standard already ports the behavior.
- **Node/npx rewrite** — discards a working Python codebase + tests for a distribution channel `uvx` already matches; `npx` is not the universal standard the field uses.
- **External runtime orchestrator** (MCP + tmux, CAO-style) — escapes per-harness subagent limits but adds a heavy long-running runtime, breaking ADE's zero-runtime file-scaffolding philosophy. A different product.
- **Personas / role-based agents** — the field's persona fashion (BMAD/gstack); rejected on evidence (no objective-quality gain; bias risk to the verifier).
- **`git pre-commit` as the only enforcement** — superseded once all four harnesses were confirmed to ship native PreToolUse hooks.

## Consequences

- **Codex is a degraded tier**: its subagent dispatch is user-gated (no autonomous orchestration), so author-separation/blind-verification degrade to in-context conventions there — but native Codex hooks still enforce the hard gates. Revisit when `openai/codex#18513` lands.
- We **bet on the open standards** (SKILL.md, AGENTS.md). Adoption is broad but young (all four shipped skills/hooks in the last ~6 months); the thin adapter layer keeps churn cheap, and each harness's skill/hook locations are verified against vendor docs at build time.
- v3.0.0 is a **breaking change**; `ade migrate` handles existing v2 trees (the only state-preserving step is moving user-owned config to `.ade/`).
- Full design: `docs/superpowers/specs/2026-06-21-platform-agnostic-ade-design.md`.
