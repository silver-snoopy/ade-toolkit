# ADE Knowledge-Layer Generation Study

Date: 2026-06-26

Scope: Should ADE's pipeline be responsible for generating and maintaining the
*knowledge layer* / grounding documents that its own agents read — e.g.
`ARCHITECTURE.md`, the per-harness instruction files (`copilot-instructions.md`
/ `CLAUDE.md` / `AGENTS.md`), language/stack detection, and a grounding document
of the codebase's *actually-used* practices and conventions?

This file complements the dev-pipeline studies in `docs/`. It is written as a
conservative market synthesis: separate adversarially-verified findings from
lower-confidence claims, map the field onto ADE's existing design, and give a
recommendation with explicit alternatives. The competitor evidence comes from a
deep-research run (104 agents, 22 sources fetched, 109 claims extracted, 25
adversarially verified — 23 confirmed, 2 refuted). The ADE-side analysis comes
from local source review (`src/ade/detect.py`, `src/ade/templates/bootstrap/`,
`src/ade/templates/AGENTS.md.j2`, the hook layer).

## Executive conclusion

Yes — ADE should own a knowledge layer, but a **bounded** one. The defensible
position from the surveyed field is:

> Persist only the expensive, judgment-laden distillations (architecture
> rationale, actually-used conventions), generate them AI-assisted with a human
> review gate, derive the cheap/volatile context (file structure, current state)
> per-task instead of persisting it, and back the whole thing with a
> deterministic drift check. Do **not** fully automate it — the field
> explicitly refutes removing the human author.

ADE already implements the cheaper half of this (stack detection, per-request
scouts) and already owns the one piece most competitors lack (a deterministic
hook layer, the natural home for drift detection). The genuine gap is a
**brownfield cold-start**: on day one against an existing repo, ADE's agents have
stack commands but no distilled architectural model or convention grounding.

## What the field actually does (verified)

The market splits into two strategies, and the strongest players hedge across
both: **persistent maintained docs** versus **per-request derived context**.

| Tool | Strategy | Generation | Persisted | Human in loop |
| --- | --- | --- | --- | --- |
| GitHub Copilot (`copilot-instructions.md`) | Persistent | AI drafts after repo inventory, then human reviews; layered scoped instruction files; recommended ~5-section structure | Yes | **Yes — explicitly recommended** |
| Cursor (`.mdc` rules) | Persistent | Version-controlled rule files; four application modes (Always / Auto-attached / Agent-requested / Manual); auto-generation affordances beyond manual `/create-rule` | Yes | Partial |
| Devin / Cognition (DeepWiki) | Persistent | **Auto-indexes the codebase and auto-generates a grounding wiki at onboarding**, used to ground the agent | Yes | Minimal (closest to full-auto) |
| Aider (repo-map) | **Derived per-request** | tree-sitter parses source into a concise structural map, token-budgeted, sent with each request | **No** | n/a |
| Aider (conventions) | Persistent | **Manually authored** — no auto-derivation | Yes | Fully manual |
| Cody (Sourcegraph) | Derived per-request | keyword / BM25 + retrieval context | No | n/a |

Windsurf, Continue, Tabnine, Qodo, and Augment produced no claims that survived
adversarial verification — treat them as unconfirmed here, not as absent
capability.

### Findings the verifiers confirmed

- **Consensus generation pattern = AI-assisted draft + human review.** GitHub
  explicitly recommends using Copilot *itself* to draft the custom-instructions
  file, then a human edits. This is the field's center of gravity.
- **Staleness is the dominant failure mode**, and outdated grounding docs cause
  *silent* failures: the agent confidently follows wrong context. This is partly
  automatable via a session-start Git-vs-doc drift check. *(Caveat: this rests
  largely on a single arXiv preprint, n=1 — directionally credible, not
  conclusive.)*
- **Aider's repo-map is auto-derived from the actual code, token-budgeted, and
  sent per request — never persisted.** A clean example of the derived strategy.
- **A good agent instruction file is concise and structured** (~5–6 sections);
  lessons drawn from 2500+ repositories.
- **Devin/DeepWiki auto-generates its wiki at onboarding and uses it to ground
  the agent** — the one surveyed tool near full-auto persistent generation.

### Findings the verifiers refuted

- **Refuted (1–2 votes): "the knowledge documents can be fully AI-generated, with
  the human reduced to designing structure."** The field does *not* support
  removing the human author from the loop.
- **Refuted (0–3 votes): "Cursor rule creation is manual-only."** Cursor has
  auto-generation affordances beyond the manual command — so "persistent docs
  must be hand-written" is false.

## Where ADE sits today

ADE already implements part of this, and its existing ownership model aligns
well with the verified best practice:

- **Stack/language detection** — `detect.py` maps marker files to languages and
  build/lint/format/test commands, seeding `.ade/ade-stack.md` as a
  **seeded-once, user-editable** artifact. This is exactly the right model.
- **`CONTEXT.md`** is a *domain glossary*, deliberately **not pre-filled**,
  accumulated lazily via `grill-with-docs` during the Research phase. This is an
  Aider-conventions-style "manual / incremental" philosophy.
- **R2.1 scouts** (`current-state` + `available-surface`) are essentially
  **per-request repo-mapping** — the Aider/Cody derived strategy, already inside
  the pipeline.

**The gap the idea targets is real and specific:** ADE has **no `ARCHITECTURE.md`
and no auto-derived "actually-used practices" grounding doc.** The
lazy-accumulation philosophy is excellent for greenfield-incremental work but
leaves a **cold-start hole on brownfield repos** — on day one the agents have
stack commands but no distilled architectural model or convention grounding.
Competitors (Devin DeepWiki, Copilot inventory-draft) specifically solve
onboarding; ADE does not.

## Recommendation: bounded hybrid

### 1. Persist only what is expensive to re-derive

Split the knowledge layer by cost:

- **Derive per-task, do not persist:** file structure, current state, available
  surface — already covered by scouts. Zero staleness, no maintenance. Do not
  persist what a scout re-derives cheaply.
- **Persist (seeded-once, human-reviewed):** the judgment-laden distillations —
  `ARCHITECTURE.md` (the *why*, module boundaries, data flow) and a
  **practices/conventions grounding doc** derived from the *actual code* (lint
  configs, observed patterns), not from language defaults.

### 2. Resolve the "bootstrapper only scaffolds" tension

ADE's invariant is *"the bootstrapper only scaffolds — it doesn't run agents,
execute code, or manage state."* Distilling an architecture doc requires reading
and reasoning over the whole codebase — that is an **agent job, not a Python-CLI
job**. The clean resolution:

> `ade init` (Python) scaffolds an **empty seed + the generating skill + the
> drift hook**. The **harness agent** performs the actual derivation when the
> skill runs. The Python side never reads the codebase to distill it.

This preserves the invariant and matches the field's "AI drafts, human reviews"
consensus. Concretely: a new **`ade-onboard` / `ade-ground` skill** (a one-time
Phase 0.5), run once per repo, dispatches scouts to draft `ARCHITECTURE.md` plus
a practices doc, then surfaces them for the same **seeded-once,
never-overwritten, user-owned** treatment as `CONTEXT.md` / `ade-stack.md`.

### 3. Lean into the hook layer (ADE's structural advantage)

Staleness is the field's #1 risk, and **ADE already ships a deterministic hook
layer** — most competitors do not. Add a **session-start (or pre-commit) drift
check**: compare the grounding doc's hash/mtime against architecture-relevant
files changed in Git, and **warn** (not gate) when a doc has gone stale beneath
moved code. Given the existing `_hooklib` infrastructure this is cheap, and it is
the single highest-leverage differentiator available.

### 4. Keep the human gate

Do not fully automate — the field explicitly refutes it. ADE's existing "seeded
once, never overwritten" pattern *is* the human gate; reuse it.

## Alternatives

| Option | Pro | Con | Verdict |
| --- | --- | --- | --- |
| **A. Persist nothing new** — extend R2.1 scouts to cover architecture/conventions per-task (pure Aider/Cody model) | Zero staleness; nothing to maintain; minimal change | No cross-session memory; pays distillation cost every task; loses human-curated "why"; does not fix brownfield cold-start | Good fallback, misses onboarding value |
| **B. Full persistent KB** — auto-generate a DeepWiki-style index | Rich onboarding; matches Devin | Heavy; large staleness surface; ADE is a scaffolder, not a runtime, and cannot continuously re-index; violates minimalism | Over-reach for ADE |
| **C. Bounded hybrid (recommended)** — persist expensive distillations (seeded-once + reviewed), derive cheap context via scouts, add drift hook | Matches verified consensus; fixes cold-start; exploits the hook advantage; preserves invariants | One new skill + one hook to build and maintain | **Recommended** |

**One sharp caution:** resist deriving "conventions" from *language defaults*
(e.g. "Python → use ruff"). The field's value is grounding in **actually-used**
practices — read the repo's lint configs and observed patterns, or ADE will
generate confidently-wrong guidance, which is exactly the silent-failure mode the
research flagged.

## Suggested next step

The cleanest first slice: an **`ade-onboard` skill** that drafts
`ARCHITECTURE.md` plus a practices doc from scout output (human-reviewed,
seeded-once), plus a **grounding-drift warn-hook**. It is additive, respects
every existing ADE invariant, and closes the brownfield onboarding gap that
competitors specifically target.

## Sources

Primary / vendor documentation:

- GitHub Copilot — adding custom instructions: <https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot>
- GitHub blog — writing a great AGENTS.md (lessons from 2500+ repos): <https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/>
- GitHub blog — 5 tips for better custom instructions: <https://github.blog/ai-and-ml/github-copilot/5-tips-for-writing-better-custom-instructions-for-copilot/>
- Cursor — rules documentation: <https://cursor.com/docs/rules>
- Aider — repo map: <https://aider.chat/docs/repomap.html> and <https://aider.chat/2023/10/22/repomap.html>
- Aider — conventions: <https://aider.chat/docs/usage/conventions.html>
- Sourcegraph — how Cody understands your codebase: <https://sourcegraph.com/blog/how-cody-understands-your-codebase>
- Devin / Cognition — DeepWiki: <https://docs.devin.ai/work-with-devin/deepwiki>

Contrarian / skeptical (staleness, drift, maintenance burden):

- arXiv preprint (staleness as primary failure mode; drift hook): <https://arxiv.org/html/2602.20478v1>
- cursorrules vs copilot-instructions benchmark 2026: <https://rpdi.us/blog/cursorrules-vs-copilot-instructions-md-benchmark-2026/>
- Continuous context: <https://datahub.com/blog/continuous-context/>

Practitioner / implementation:

- HumanLayer — writing a good CLAUDE.md: <https://www.humanlayer.dev/blog/writing-a-good-claude-md>
- Augment — how to build agents.md: <https://www.augmentcode.com/guides/how-to-build-agents-md>
- Amp — context engineering: <https://github.com/ampcode/amp-examples-and-guides/blob/main/guides/context-management/Context%20Engineering%20-%20Amp.md>
- Building an AI init command: <https://kau.sh/blog/build-ai-init-command/>

## Caveats

- The staleness finding leans heavily on one arXiv preprint (n=1). It is
  directionally consistent with practitioner reports but should not be treated as
  settled empirical fact.
- Windsurf, Continue, Tabnine, Qodo, and Augment had no claims survive
  verification in this run — "no surviving claim" means unconfirmed coverage, not
  evidence of absence.
- Two claims were adversarially refuted and excluded from the recommendation:
  fully-autonomous (human-free) generation, and Cursor being manual-only.

---

# Part II — Cross-Harness Grounding & Determinism (Extension, 2026-06-26)

Date: 2026-06-26

Motivation: this part is driven by ADE's brownfield north-star — a **one-shot
project seeder** that removes the tedious manual work of grounding coding agents
on an *existing* repo, producing the knowledge layer / technical-instruction
context once and grounding **Claude Code + Copilot + Codex (+ Gemini, Cursor)
identically**. The question Part II answers: *which artifacts should a single
seed run emit, and how do they wire together, so behavior is stable and
close-to-deterministic across harnesses — realistically?*

Evidence base: a second deep-research run (104 agents, 21 sources, 96 claims
extracted, 25 adversarially verified — 23 confirmed, 2 refuted), plus local
review of ADE's harness adapter layer (`src/ade/harnesses/`, `AGENTS.md.j2`,
`memory_pointer.md.j2`).

## The core reframe: two layers, because the LLM step is irreducibly stochastic

"Deterministic code generation" is not literally achievable, and the research is
blunt about it. The realistic target is a **two-layer** system:

- **Layer 1 — reduce output *variance*** via a single shared grounding the agents
  consume (the instruction files). This makes behavior *consistent*, not
  *identical*.
- **Layer 2 — enforce deterministic *acceptance*** via hooks / CI / linters /
  formatters / tests, because no prompt can make generation reproducible.

Verified support for why Layer 2 is mandatory:

- **LLM codegen is severely non-deterministic by default.** Across
  CodeContests / APPS / HumanEval, **75.76% / 51.00% / 47.56%** of problems had
  *zero* identical test output among repeated requests under identical prompts
  (peer-reviewed, ACM TOSEM).
- **`temperature=0` does NOT guarantee determinism** — it only reduces variance
  (batched-GPU floating-point non-associativity, MoE routing). So grounding files
  reduce variance but determinism must come from downstream gates.
- **Instruction files are advisory, with no runtime enforcement.** Claude Code is
  documented violating explicit, read-and-acknowledged `CLAUDE.md` rules when
  built-in system prompts take precedence (plan-mode's prompt literally says "This
  supersedes any other instructions"). The lesson: move enforcement out of the
  prompt and into deterministic gates.
- **Reliable AI artifacts require a mandatory multi-stage acceptance gate** —
  security (Bandit/Semgrep), syntax (AST/mypy/ruff), execution (sandboxed tests),
  accuracy (golden thresholds) — *not* better prompting alone.

**ADE implication:** ADE already owns Layer 2 (the deterministic hook layer) —
the piece most competitors lack. Part II is therefore mostly about getting
Layer 1 right *across harnesses from one seed run*, while explicitly positioning
the hook layer as the determinism guarantee. The grounding files are the
variance-reducer; the hooks are the enforcer.

## The canonical file: `AGENTS.md` is now the cross-tool standard

- `AGENTS.md` ("a README for agents") is an **open, cross-tool format**,
  released by OpenAI (Aug 2025) and transferred to the **Linux Foundation's
  Agentic AI Foundation**; it is natively read by **Codex, Copilot's coding
  agent, Cursor, Gemini CLI** and ~28 other tools (adopter counts are the
  standard's own, treat as promotional; the named load-bearing tools are
  independently confirmed).
- It **complements, does not replace** each harness's richer native format —
  tools keep their own files alongside it.

**ADE implication:** ADE's canonical harness-neutral `AGENTS.md` is exactly the
right spine and already matches the de-facto standard. No change needed to the
*concept* — only to *coverage* (Part II §monorepo) and *content* (Part I's
`ARCHITECTURE.md` + practices doc).

## Per-harness consumption matrix (the load-bearing facts)

How each target in ADE's set actually *consumes* a single canonical
`AGENTS.md`, and whether a bridge is needed:

| Harness | Reads canonical `AGENTS.md`? | Bridge required | ADE status today |
| --- | --- | --- | --- |
| **Codex** | **Yes, natively** (nested, nearest-wins; concatenates root→cwd) | None | ✓ `memory_file = AGENTS.md`, read natively |
| **Copilot** (coding agent) | **Yes, natively** — *plus* root `CLAUDE.md` / `GEMINI.md`, *plus* `.github/copilot-instructions.md` + `.github/instructions/**`; all coexist | None for the coding agent | ✓ emits root `AGENTS.md` + a thin `copilot-instructions.md` pointer (belt-and-suspenders, fine) |
| **Claude Code** | **No** — reads **only `CLAUDE.md`** | **`@AGENTS.md` import** at top of `CLAUDE.md` (officially documented transclusion; expanded at launch; cannot drift; Windows-safe without admin — preferred over symlink) | ✓ `supports_at_import=True` already emits `@AGENTS.md` — **this is the documented best practice, exactly right** |
| **Gemini CLI** | **Only via config** — reads `AGENTS.md` *only* if `context.fileName` in `.gemini/settings.json` names it; otherwise reads `GEMINI.md` | Either set `context.fileName`, or keep a `GEMINI.md` pointer | ⚠ uses a plain-text `GEMINI.md` pointer (`supports_at_import=False`); see recommendation 4 |
| **Cursor** (if targeted) | Via `.mdc` rules / native `AGENTS.md` | Glob-scoped `.mdc` for path rules | n/a (not an ADE target) |

Caveat the research flagged: Copilot's **coding/cloud agent** reads
`AGENTS.md` + `CLAUDE.md` + `GEMINI.md`; some surfaces (Chat, CLI) support only
singular `AGENTS.md`, and `CLAUDE.md` / `GEMINI.md` must sit at **repo root**
(no nested-path scoping). So the only fully path-scopable canonical file is
`AGENTS.md` itself.

## The real brownfield gap: path-scoping in monorepos

Three **incompatible** path-scoping models exist, and a brownfield monorepo seed
must satisfy all the harnesses at once:

| Model | Mechanism | Used by |
| --- | --- | --- |
| **Directory-proximity (nearest-wins)** | nested `AGENTS.md` per package; agent reads the nearest and concatenates the chain root→cwd | Codex, Copilot native `AGENTS.md` |
| **Glob frontmatter** | `.github/instructions/NAME.instructions.md` with `applyTo: "**/*.ts,**/*.tsx"` | Copilot |
| **Glob-scoped rules** | `.mdc` rule files with glob globs | Cursor |

These do not interoperate (proximity ≠ glob; off-path sibling `AGENTS.md` files
are not loaded). **A hand-maintained repo cannot keep all three in sync — but a
generator can.** This is precisely where ADE is uniquely positioned: a brownfield
seed run can derive path-scoped guidance **once** and emit it in all three
styles. No surveyed competitor does this; it is the strongest available
differentiator and directly serves the "remove manual work" goal.

## Enterprise governance patterns (verified)

- **Protect the instruction files as agent configuration.** GitHub's Well
  Architected guidance: files like `AGENTS.md`, `mcp.json`,
  `copilot-instructions.md` "define what agents can do. Changes to these files
  need human review," enforced via **CODEOWNERS + branch rulesets requiring
  independent review** (GitHub's per-file "required reviewer rule" went GA
  2026-02-17).
- **Org-vs-repo layering:** org-level instructions only for **narrow,
  non-negotiable standards** (security/compliance, <1000 words, no repo-specific
  logic); repo-level via a **central library of starters that teams copy and
  adapt**. Pushing everything to the org level "wastes tokens and produces
  generic results."

**ADE implication:** the governance pattern *is* ADE's "AI drafts → human
reviews" gate, expressed in version control. A brownfield seed can scaffold a
**CODEOWNERS entry for the grounding files** so the minimum-friction review
checkpoint is also the governance control — one diff review satisfies both.

## What a one-shot brownfield seed run should emit (the deliverable)

Per harness, from a single derivation pass:

| Artifact | Purpose | Harnesses served |
| --- | --- | --- |
| `AGENTS.md` (root, canonical) | the single source of truth: stack, build/test, conventions, ARCHITECTURE pointer | Codex, Copilot (native), Gemini (via config) |
| `ARCHITECTURE.md` (root) | distilled module boundaries + data flow + the *why* (Part I) | referenced by `AGENTS.md` |
| practices/conventions doc | actually-used conventions derived from lint configs + observed patterns (Part I) | referenced by `AGENTS.md` |
| `CLAUDE.md` (root) | thin file whose first line is `@AGENTS.md` | Claude Code |
| `GEMINI.md` *or* `.gemini/settings.json` `context.fileName` | point Gemini at the canonical file | Gemini CLI |
| `.github/copilot-instructions.md` | thin pointer (coding agent already reads `AGENTS.md`; this covers Chat/CLI surfaces) | Copilot |
| nested `AGENTS.md` + `.github/instructions/*.instructions.md` + `.mdc` (monorepo only) | path-scoped per-package guidance in all three scoping styles, generated from one source | all |
| `CODEOWNERS` entry for the above | makes the review gate a governance control | n/a (process) |
| deterministic hooks (existing) | Layer 2 acceptance enforcement | all |

The human checkpoint is a **single diff-review pass** over this set — which is
both the field's required review gate and the minimum-friction UX the north-star
demands.

## Recommendations for ADE (ranked)

1. **Keep the spine — it is already best practice.** Canonical `AGENTS.md` + the
   `@AGENTS.md` Claude bridge are exactly the documented single-source pattern.
   Do not refactor it; validate and lock it with a test.
2. **Add `ARCHITECTURE.md` + a practices doc to the seed** (Part I) and reference
   both from `AGENTS.md`, so Copilot/Codex pick them up natively and Claude via
   the import.
3. **Generate path-scoped guidance for monorepos in all three styles** (nested
   `AGENTS.md`, Copilot `.instructions.md` `applyTo`, Cursor `.mdc`) from one
   derivation. This is the differentiator and the hardest thing to do by hand.
4. **Fix/verify Gemini single-sourcing:** either emit
   `.gemini/settings.json` with `context.fileName` including `AGENTS.md` (true
   single-source, drop the duplicate pointer) or keep the `GEMINI.md` pointer
   knowingly. Re-check whether `supports_at_import=False` is still accurate for
   current Gemini CLI.
5. **Scaffold governance:** seed a `CODEOWNERS` entry for the grounding files and
   document the single review pass as the minimum-friction human gate.
6. **Position the hook layer explicitly as Layer 2** ("deterministic acceptance")
   in ADE's own docs — it is the answer to "how can generation be
   close-to-deterministic," and it is ADE's structural advantage.

## Open questions (unresolved by the research)

- Does a single canonical `AGENTS.md` actually *reduce cross-harness output
  variance* on the same task, or only improve single-harness efficiency? The one
  efficiency study tested **Codex only**; no study measures behavioral
  consistency across Copilot + Claude + Codex on identical grounding. *(Two
  cross-harness-generalization claims were adversarially refuted, 0-3.)*
- Observed drift rate / detection latency of multi-file sync patterns vs the
  no-second-copy `@AGENTS.md` import in real monorepos.
- The minimal deterministic gate set that reliably catches the rule classes most
  often ignored under system-prompt override (parallel-agent dispatch,
  file-location rules, author-separation) — expressed once, emitted per harness
  like ADE's hooks.

## Part II sources

Primary / vendor:

- agents.md (the standard): <https://agents.md/>
- GitHub Copilot — custom instructions (repo-wide + `applyTo` path-scoped + AGENTS.md/CLAUDE.md/GEMINI.md): <https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot>
- GitHub changelog — Copilot coding agent supports AGENTS.md: <https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/>
- Anthropic — Claude Code memory & `@AGENTS.md` import: <https://code.claude.com/docs/en/memory>
- OpenAI Codex — AGENTS.md (nested, nearest-wins): <https://developers.openai.com/codex/guides/agents-md>
- GitHub Well Architected governance (CODEOWNERS + rulesets, org-vs-repo): <https://github.com/orgs/community/discussions/193359>

Determinism (peer-reviewed + preprint):

- Non-determinism of LLM code generation (ACM TOSEM): <https://arxiv.org/pdf/2308.02828>
- Mandatory multi-stage acceptance gate / one-time invocation (preprint): <https://arxiv.org/html/2604.05150v1>
- AGENTS.md efficiency on Codex (preprint; Codex-only): <https://arxiv.org/abs/2601.20404>

Practitioner:

- Cross-tool portability of AGENTS.md / CLAUDE.md: <https://codex.danielvaughan.com/2026/05/27/agent-instruction-files-agents-md-claude-md-cross-tool-portability-codex-cli/>
- AGENTS.md in monorepos: <https://dev.to/datadog-frontend-dev/steering-ai-agents-in-monorepos-with-agentsmd-13g0>
- Why Claude Code ignores your CLAUDE.md: <https://github.com/anthropics/claude-code/issues/27032>
- Symlink AGENTS.md → CLAUDE.md (and why import is preferred): <https://www.ssw.com.au/rules/symlink-agents-to-claude>

## Part II caveats

- **Fast-moving area (mid-2026).** Harness instruction-file support evolves
  surface-by-surface (Copilot Chat/CLI vs coding agent differ; Gemini CLI reads
  `AGENTS.md` only via explicit config). Re-verify before implementing.
- **Determinism/efficiency evidence is thin in places.** `2308.02828` is strong
  and peer-reviewed; `2604.05150` (100% reproducibility) is a single v1 preprint
  on a narrow benchmark; `2601.20404` (AGENTS.md efficiency) tested **Codex
  only** with a non-rigorous quality check — do **not** generalize its numbers to
  Claude/multi-harness.
- **Refuted and excluded:** "AGENTS.md gains are efficiency-only, not quality"
  (0-3) and "the efficiency effect was measured across both Codex and Claude"
  (0-3).
- The Claude-Code rule-violation evidence is from GitHub issues (observed
  behavior + reporter root-cause), not documented design intent — but the
  underlying "instruction files are advisory, not enforced" point is robustly
  corroborated.

---

# Part III — Repo Topologies: Monorepo & Polyrepo (Extension, 2026-06-26)

Date: 2026-06-26

Motivation: a brownfield seeder must work in two structurally different worlds —
**monorepos** (one repo, many packages: the knowledge layer collocates by
*directory proximity*) and **polyrepos** (many separate repos: no shared tree, so
the layer must be *distributed and tiered*). This part covers how the
agent-hardening files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
`copilot-instructions.md` + `.instructions.md`, Cursor `.mdc`, hook/settings
configs, `mcp.json`) collocate, layer, merge, and stay in sync in each.

Evidence base: two further deep-research runs — monorepo (108 agents, 25/25
claims confirmed) and polyrepo (110 agents, 24/25 confirmed) — both anchored
overwhelmingly in primary vendor docs (Anthropic, GitHub, VS Code/Microsoft, Nx,
OpenAI Codex, Cursor, Gemini CLI).

## The universal mechanic: additive merge, not override (verified both topologies)

The single fact that governs everything below, confirmed in both passes:
**instruction/context files *concatenate*; settings/rules *override*.** They are
two different families with two different merge models.

| File family | Merge model | Conflict resolution |
| --- | --- | --- |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `copilot-instructions.md`, `*.instructions.md` | **Additive concatenation** (broadest → closest; closest read last) | By **model attention** (later/closer text weighted more) — *not* a hard override |
| Claude `settings.json`, Cursor rules | **Override chain** (Managed/Team highest) | Higher scope wins per key |
| Claude **permission** rules | **Merge across scopes** | `deny` cannot be overridden by any `allow` |

The practical consequence: you can *layer guidance* freely (nothing is dropped,
so a root file + a package file both apply), but you cannot rely on a closer file
to *hard-override* a farther one — only to out-weight it. Determinism still has to
come from the settings/hook/CI layer, not from instruction-file precedence.

## A. Monorepo (one repo, many packages) — collocation by proximity

- **Claude Code walks UP at launch and lazy-loads subdirectories.** Launching at
  repo root loads the **root `CLAUDE.md` only**; subdirectory files load *on
  demand* when Claude reads files there. Launching inside `packages/api/` loads
  that file **plus every ancestor**. The on-demand subdir load is the documented
  token-saving mechanism for "work that stays in one package."
- **Recommended inheritance = two levels.** A **root** file holds cross-cutting
  rules (standards, commit conventions, layout); a **thin per-package** file adds
  only that area's stack-specific conventions. Shared rules are inherited once,
  never duplicated — the single-source-of-truth pattern *within* a monorepo.
- **Copilot path-scoping:** `.github/instructions/*.instructions.md` with an
  `applyTo:` glob targets exact paths and stacks **cumulatively** on top of the
  repo-wide `copilot-instructions.md` (files lacking `applyTo` are ignored).
- **VS Code nested `AGENTS.md` is experimental** (`chat.useNestedAgentsMdFiles`):
  it injects subfolder `AGENTS.md` *paths* into context and lets the agent
  *choose* — not a hard nearest-wins resolution.

### ⚠ The critical asymmetry (the most ADE-relevant finding in this study)

**Instruction files inherit up the tree; hooks / settings / MCP do NOT.**
Claude Code's `.claude/settings.json` (hooks, permissions, worktree config) loads
**only from the directory Claude is launched in** — it does not traverse parents;
MCP servers and permissions are **session-global**. The official load table:
Skills ✅ nested, `CLAUDE.md` ✅ on-demand subdirs, **Settings ❌ root-only, Hooks
❌ root-only, MCP ❌ session-global**. Hierarchical merge is only a *proposed*
feature (open issues #12962 / #37344), not shipped. Project MCP config is a single
repo-root `.mcp.json`, not per-package.

**Why this matters for ADE specifically:** ADE's entire determinism story (Part II
"Layer 2") rests on the **deterministic hook layer**. In a monorepo, if a
developer launches the agent from the repo root while working in a sub-package,
**that package's ADE hooks do not fire** — the acceptance gate silently does not
run. This is a real correctness gap, not a styling nit. Documented workarounds:
emit **self-contained `.claude/settings.json` in every package**, **always launch
from the package directory**, or rely on **global user settings**. ADE, as a
generator, can do the first automatically.

### Monorepo tooling awareness

- **Nx is the proof-of-model for ADE:** `npx nx configure-ai-agents` generates
  per-tool config (Claude/Cursor/Copilot/Gemini/Codex/OpenCode) **from one
  source** — exactly ADE's emit-from-one-derivation pattern — and the Nx **MCP
  server** exposes the project graph (`nx_workspace`, `nx_project_details`) so
  agents discover workspace boundaries *dynamically* instead of from baked-in file
  layout.
- **Turborepo / Bazel / pnpm-yarn workspaces:** no verified agent-facing
  project-graph/MCP equivalent surfaced — dynamic workspace discovery appears
  Nx-specific today (open question).

## B. Polyrepo (many separate repos) — collocation by tier

No shared tree exists, so collocation becomes **layering across repo boundaries**:
push durable conventions to a home/org tier, keep only repo-specifics per repo.

**Per-harness tiers and precedence (all primary-sourced, 3-0):**

| Harness | Home/global tier | Org/enterprise tier | Per-repo tier | Precedence family |
| --- | --- | --- | --- | --- |
| **Claude Code** | `~/.claude/CLAUDE.md`, `~/.claude/settings.json` | **Managed policy** `CLAUDE.md` + `managed-settings.json` (MDM/GPO/Ansible; *cannot be overridden*) | `./CLAUDE.md`, `.claude/settings.json` | `CLAUDE.md` **additive**; settings **override** (Managed > CLI > Local > Project > User) |
| **Codex** | `~/.codex/AGENTS.md`, `~/.codex/config.toml` | — | `AGENTS.md` chain, `.codex/config.toml` (trusted only) | `AGENTS.md` **additive** (global → root → cwd, closest last) |
| **Copilot** | personal (web) | **Org custom instructions** (GA 2026-04-02) — but **prioritized *last*** | `copilot-instructions.md` + `.instructions.md` | additive; priority Personal > Repo > **Org** |
| **Cursor** | User Rules (in-app, *not* a versioned file) | **Team Rules** (dashboard; enforceable, *cannot be disabled*) | `.cursor/rules/*.mdc` | **override** (Team > Project > User) |
| **Gemini CLI** | `~/.gemini/GEMINI.md` | *(no org tier found)* | `GEMINI.md` | additive concatenation |

Key polyrepo facts:

- **Strongest cross-repo single-source levers:** Claude **managed-policy**
  `CLAUDE.md`/settings (unoverridable, OS-path deployed), Cursor **Team Rules**
  (enforceable). Copilot's org tier exists but is **weak — prioritized last**, so
  org-level Copilot grounding must stay narrow and non-conflicting to matter.
- **Codex and Gemini global files are filesystem-path-based, *not* git-aware** —
  they only cross repo boundaries when repos nest under a shared parent dir
  (e.g. `~/dev/`). The additive model also means **every global file is
  concatenated on every prompt → token cost**, so keep global tiers narrow.
- **ADE is itself a pull-style distribution mechanism.** Because ADE owns and
  regenerates the **per-repo** tier on every `init`, re-running it across N repos
  *is* distribution (pull if developer-invoked, push if CI-driven). The org/global
  tiers sit *above* ADE's scope — that is where narrow, durable conventions belong.

### Distribution & fleet-sync mechanisms (LOWER confidence — see caveat)

These were named in fetched sources but did **not** survive into the verified
top-claim set, so treat as directional, not confirmed: a **central
starter-instruction repo** teams copy-and-adapt; **git submodule/subtree** of
shared instruction fragments; packaging instructions as an **npm/pip/OCI
dependency**; the GitHub **`.github` default community-health repo**; **template
repositories**; and fleet-update tooling (**`multi-gitter`**, **`safe-settings`**,
**`actions-template-sync`**, **Renovate**) to bump a pinned generator version
across many repos. The trade-off axis is always **push vs pull** and **drift
control**: a generator + pinned version + a CI drift-check (diff the generated
`AGENTS.md` against the canonical) is the pattern most aligned with how ADE
already works.

## Combined recommendations for ADE (ranked)

1. **Fix the monorepo hook asymmetry — highest priority.** It silently disables
   ADE's Layer-2 determinism for sub-package work. Emit **self-contained
   `.claude/settings.json` (hooks/permissions) per package**, and/or document the
   launch-from-package-root requirement, and/or provide root-level hooks that
   detect the touched package. Track issues #12962 / #37344 — if hierarchical
   merge ships, revisit.
2. **Emit the two-level monorepo layout** (one root `AGENTS.md` + thin nested
   per-package files; keep nested files thin to exploit lazy subdir loading and
   control token bloat). ADE's generator nature makes this nearly free, and Nx's
   `configure-ai-agents` proves the model.
3. **Generate path-scoping in all three styles in sync** (nested `AGENTS.md` +
   Copilot `applyTo` `.instructions.md` + Cursor `.mdc`) from one derivation —
   carried from Part II; the monorepo is where this pays off most.
4. **Position ADE-re-run as the polyrepo pull-distribution mechanism**, and add a
   **CI drift-check** (diff generated `AGENTS.md`/pointers against a pinned
   canonical version) so N repos cannot silently diverge; pair with
   `multi-gitter`/Renovate-style fleet bumps of the pinned ADE version.
5. **Optionally emit org-tier templates** (a managed-policy `CLAUDE.md` and a
   narrow Copilot org-instruction starter) for durable cross-repo conventions that
   live *above* ADE's per-repo tier — explicitly kept narrow to avoid the
   always-concatenated token tax.

## Open questions (Part III)

- Cursor `.mdc`, native Codex `AGENTS.md`, and Gemini `GEMINI.md` **nested merge
  semantics** were under-sourced vs Claude/Copilot/VS Code — verify before relying
  on them.
- If Claude Code ships **hierarchical settings/hooks discovery** (#12962/#37344),
  the central monorepo finding **inverts** — re-verify.
- Do **Turborepo/Bazel/pnpm** expose any agent-facing project-graph/MCP equivalent
  to Nx, or is dynamic workspace discovery Nx-only today?
- The **polyrepo distribution/sync mechanisms** (submodules, template repos,
  `safe-settings`, `multi-gitter`, Renovate, `.github` default repo) need a
  dedicated verification pass — they were fetched but not adversarially confirmed.

## Part III sources

Monorepo (primary):

- Claude Code — large codebases (nested CLAUDE.md, settings non-inheritance): <https://code.claude.com/docs/en/large-codebases>
- Claude Code — memory: <https://code.claude.com/docs/en/memory>
- Claude Code — settings precedence: <https://code.claude.com/docs/en/settings>
- Claude Code — MCP scopes: <https://code.claude.com/docs/en/mcp>
- Claude Code issues — hierarchical settings proposals: <https://github.com/anthropics/claude-code/issues/12962>, <https://github.com/anthropics/claude-code/issues/37344>
- VS Code — custom instructions (nested AGENTS.md, applyTo): <https://code.visualstudio.com/docs/agent-customization/custom-instructions>
- GitHub — path-scoped instruction files: <https://github.blog/changelog/2025-09-03-copilot-code-review-path-scoped-custom-instruction-file-support/>
- Nx — AI agent skills + single-source generation: <https://nx.dev/blog/nx-ai-agent-skills>, <https://github.com/nrwl/nx-ai-agents-config>
- Nx — MCP project graph: <https://nx.dev/docs/reference/nx-mcp>

Polyrepo (primary):

- Claude Code — memory / settings / permissions (managed tier): <https://code.claude.com/docs/en/memory>, <https://code.claude.com/docs/en/settings>, <https://code.claude.com/docs/en/permissions>
- Codex — AGENTS.md chain + config reference: <https://developers.openai.com/codex/guides/agents-md>, <https://developers.openai.com/codex/config-reference>
- Copilot — customizing chat responses (tiers) + org instructions GA: <https://docs.github.com/copilot/concepts/about-customizing-github-copilot-chat-responses>, <https://github.blog/changelog/2026-04-02-copilot-organization-custom-instructions-are-generally-available/>
- Cursor — rules (Team/Project/User): <https://cursor.com/docs/rules>
- Gemini CLI — GEMINI.md hierarchy: <https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md>

Polyrepo fleet-sync (lower confidence, not adversarially confirmed):

- `safe-settings`: <https://github.com/github/safe-settings> · `multi-gitter`: <https://github.com/lindell/multi-gitter> · `actions-template-sync`: <https://github.com/AndreasAugustin/actions-template-sync> · GitHub default community-health repo: <https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file>

## Part III caveats

- **Fast-moving (2025–2026), feature-gated.** VS Code nested `AGENTS.md` and
  `AGENTS.md` auto-detection are experimental settings; Copilot org instructions
  only reached GA 2026-04-02; Cursor Team Rules and Claude `managed-settings.d/`
  are recent. Re-verify before building.
- **The monorepo hook-asymmetry finding could invert** if Claude ships
  hierarchical settings (#12962/#37344) — it is the load-bearing recommendation,
  so track those issues.
- **Cursor / Codex / Gemini nested-merge semantics are under-sourced** relative to
  Claude/Copilot/VS Code; the polyrepo **distribution/sync mechanisms** were
  fetched but not adversarially verified (no surviving top-claim) — both flagged
  as lower confidence above.
- **Vendor framing:** Nx's "every tool gets the same capabilities" is marketing —
  read as *same generated config surface*, not runtime parity (Codex still can't
  dispatch subagents).
- **Scope vs tree precedence are orthogonal.** Claude's 5-scope settings
  precedence and Copilot's Personal>Repo>Org ordering are *scope*-based; the
  directory-tree concatenation is a separate axis — do not conflate them.
