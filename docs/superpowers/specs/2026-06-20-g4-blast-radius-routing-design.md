# Design — G4: Blast-radius routing

**Date:** 2026-06-20
**Status:** Approved (design); pending implementation plan
**Scope:** ADE toolkit (`src/ade/`) — closes gap G4 from `docs/ade-sdlc-gap-analysis.html` (Recommendations move #3).
**Depends on:** G1/G2 (deterministic hook layer) and G5 (9-phase pipeline, stack-neutral phases) — both shipped.

## 1. Context & motivation

The gap analysis flagged that ADE runs its full heavyweight flow for every change: the S/M/L scope estimate is *informational only* and "a one-line doc fix shouldn't pay for stub-design + live verification." Eight of ten surveyed systems classify change size/risk and **mask which phases run**. G4 adds that routing.

Two evidence sources shaped this design:

- **LeRisque** (`PetroczyP/LeRisque`, read directly): a deterministic Stage-0 router with `trivial`/`standard`/`architecture` tiers. `trivial` (only `*.md`/`*.txt`/single-line config) skips to the final gate; `architecture` (touches ADR paths / models / route adds / `>10` files) runs the full flow **+ a mandatory plan-review gate** (Stage 1.5). Routing is deterministic file-glob + diff-size, with no LLM classifier and no user-override gate; security escalation happens post-PR, not at routing.

- **Deep research** (`docs/superpowers/` synthesis, 2026-06-20; 27 sources, 25/25 claims verified). Key findings:
  - The top tier should add **more than** a single plan-review gate. Highest leverage: **(a) mandatory ADRs** — "context and change understanding is *the* key determinant of review effectiveness" (Bacchelli & Bird, ICSE 2013) — and **(b) an adversarial plan/design-review *before* code**, since post-code review reliably catches only small local bugs and misses the design/security risk that defines high blast radius. **Expanded reviewer count is low marginal value** (the ~2-reviewer optimum holds); mandatory docs are weakly supported.
  - **Classifier = hybrid**: deterministic path/glob rules for routing + forced-escalation (auditable, non-evadable), with size/severity judgment layered on. LLM-only classification is "non-deterministic and evadable" — it must not be the sole basis for security (Martin Fowler/Sietsma; Anthropic hooks guidance).
  - **Forced-escalation = category-based, deterministic, at classification time, overriding size** — security/auth/secrets/crypto, public-API, schema/SQL-migration changes (Meta RADAR hard-excludes these from auto-approval; GitHub rulesets force path-based reviewers). Plus defense-in-depth: enforce again later via a deterministic gate, because LLM detection is evadable.
  - **Human-in-the-loop**: auto-proceed low-risk; surface high-tier / forced-escalated changes for human confirm/override (Meta RADAR keeps a human override loop even on auto-approve).

ADE-specific wrinkle the research surfaces: ADE's router runs at **Phase 0, before any code exists**, so it classifies from the intent's *declared* affected areas + type, not a real diff. That makes a later deterministic re-check (a Ship-time hook on the actual diff) the load-bearing guarantee.

## 2. Goals / non-goals

**Goals**
- A Router step after Phase 0 assigns one of three tiers — `trivial` / `standard` / `architecture` — and masks which phases run.
- `standard` is exactly today's full 0–9 flow (no behavior change for it).
- `trivial` is a moderate fast-path that preserves ADE's safety invariants (author-separated TDD + the deterministic quality gate + the merge gate) while cutting ceremony.
- `architecture` adds, on evidence, **≥1 mandatory ADR** and an **adversarial plan-review gate** before code.
- Forced-escalation is deterministic and category-based: security/auth/secrets/crypto/data-loss force a floor of `standard`; schema/migrations/public-API/ADR-or-contract changes / large blast radius force `architecture`. A `trivial` route is impossible for any escalation-matching change.
- A new deterministic hook (`check-escalation-paths`) enforces the floor against the *actual* diff at Ship time — the non-evadable backbone — wired into both claude and copilot hook substrates.
- Routing config (`.claude/ade-routing.json`) is seeded, user-editable, and is the single source of truth read by both the orchestrator (Phase 0) and the hook (Ship).
- Tier + rationale are announced; `architecture` and any forced-escalation require explicit human confirmation; the user can override up freely.
- All affected tests updated; suite stays green; the G5 stale-reference guard still passes.

**Non-goals (deferred / out of scope)**
- No ML/LLM diff-risk scorer (Meta DRS/RADAR are production-CI scale, inappropriate for a scaffolder). Size judgment is the orchestrator's, bounded by deterministic floors.
- No expanded review fan for `architecture` (research: low marginal value; 2-reviewer optimum holds).
- No per-tier model-tier changes.
- G3 (compound loop) remains a separate cycle.
- No new "live verification" — removed in G5 by operator directive; nothing here reintroduces it.

## 3. Design

### 3.1 The Router (post-Phase-0 step)

New detail skill `skills/phases/route.md.j2` (un-numbered, referenced from `ade-full`, like the former `qa-verify-bug`). It runs after Phase 0 captures intent and before Phase 1. The orchestrator:

1. Reads `.claude/ade-routing.json` (escalation globs + size thresholds).
2. Computes the tier:
   - **Forced-escalation first (deterministic rules):** if any declared `Affected Area` (or the intent text) matches an `escalation_globs.architecture` entry → tier `architecture`; else if it matches `escalation_globs.standard` → floor `standard`.
   - **Size judgment (orchestrator, only within the non-forced band):** a change with no escalation match and a small, self-contained scope (≈ Phase-0 size `S` and a single area, e.g. a docs/comment/copy/config one-liner) → `trivial`; otherwise `standard`.
3. Writes the decision + a one-line rationale to `.ade/tasks/<task-id>/routing.md` and updates `status.md` (`Routed: <tier>`).
4. **Announces** the tier + rationale.
5. **Gate:** `architecture` or any forced-escalation → require explicit human confirmation before proceeding. `trivial`/`standard` → auto-proceed (announced); the user may still interject to re-tier. Override **up** is always allowed; override **down out of a forced floor** is refused (and would be blocked by the Ship hook regardless).

The Router is prose-driven (orchestrator applies the JSON rules); the only *code* in G4 is the enforcing hook (§3.4) and the cli/seed wiring. This matches the research split: deterministic rules + enforcing hook for escalation; orchestrator judgment for size.

### 3.2 Per-tier phase map

`standard` = the current 0–9 flow, unchanged. The other two differ as:

| Phase | trivial | architecture (delta vs standard) |
|---|---|---|
| 0 Intent | ✓ | ✓ |
| Router | ✓ | ✓ (+ confirmation gate) |
| 1 Research | lightweight **inline scout** only — no R3 grill, no R5 CoVe | full R1–R5 |
| ◆ ready-for-dev gate | folded into the Router announce/confirm | ✓ |
| 2 Plan | short **inline** plan (no Plan agent) | full + **★ plan-review gate** |
| 3 Design-check (stubs) | **skipped** | ✓ |
| 4 Implement (author-sep TDD) | ✓ (non-negotiable) | ✓ |
| 5 Quality gate (hooks+tests) | ✓ (non-negotiable hard gate) | ✓ |
| 6 Review | single quick review pass (not the 3-lens fan) | full fan |
| 7 Docs | only if a doc trigger fires | **required** (non-conditional) |
| 8 Ship + ◆ merge gate | ✓ (non-negotiable) | ✓ |
| 9 Retro | **skipped** | ✓ |

`★ plan-review gate` (architecture only): after Phase 2, before any code, dispatch a fresh-context `plan-reviewer` subagent that **never saw the planning reasoning**; it tries to refute the plan against the spec (hallucinated paths, weak/missing acceptance criteria, scope creep, missing edge cases, missing ADR for a hard-to-reverse decision). Bounded: max 2 fix iterations → escalate to user. Architecture tier also forces **≥1 ADR** in R4 (`grill-with-docs`): the orchestrator instructs grill to produce at least one ADR capturing the decision + trade-offs (overriding the usual "sparingly" 3-criteria gate).

TDD (Phase 4) and the deterministic quality gate (Phase 5) and the merge gate are **non-negotiable in every tier** — trivial cuts ceremony, never the safety invariants.

### 3.3 Routing config — `.claude/ade-routing.json`

Template `templates/ade-routing.json.j2` renders to `.claude/ade-routing.json` (seed-if-missing, user-owned). Machine-readable (JSON, not markdown) precisely because a deterministic hook parses it. Shape:

```json
{
  "escalation_globs": {
    "architecture": [
      "**/migrations/**", "**/*.sql", "**/schema.*",
      "**/openapi.*", "**/*.proto", "**/routes/**", "**/api/**",
      "docs/adr/**", "**/models/**"
    ],
    "standard": [
      "**/auth/**", "**/*secret*", "**/*crypto*", "**/security/**",
      "**/.env*", "**/credentials*"
    ]
  },
  "size_thresholds": { "architecture_file_count": 10 },
  "keywords": {
    "architecture": ["schema", "migration", "public api", "breaking change", "data model"],
    "standard": ["auth", "authentication", "authorization", "secret", "credential", "crypto", "security", "permission", "data loss"]
  }
}
```

- **Orchestrator (Phase 0)** uses `keywords` + `escalation_globs` against the *declared* affected areas (no diff exists yet) and `size_thresholds.architecture_file_count` against the plan's anticipated file count.
- **Hook (Ship)** uses `escalation_globs` against the *actual* staged file paths.
- Defaults are conservative and stack-neutral; the user edits the file for their repo. `detect.py` does **not** populate it (no reliable cross-stack inference); defaults + user edits suffice.

### 3.4 The deterministic re-check hook — `check-escalation-paths.py`

New hook `templates/hooks/check-escalation-paths.py.j2` (+ shared `_hooklib` helpers), rendered to `.claude/hooks/`. Behavior:

- Reads the staged/changed file list and `.claude/ade-routing.json`, plus the current tier from `.ade/tasks/<task-id>/routing.md` (the routing artifact written by the Router).
- If any changed path matches `escalation_globs.architecture` and tier < `architecture`, **block**; if any matches `escalation_globs.standard` and tier == `trivial`, **block**. Message names the offending path(s) and the required floor.
- If no `routing.md` is found (routing not run — e.g. a manual commit outside ADE), the hook is a **no-op** (it only enforces ADE-routed work; it must not break normal commits).
- Wired like the G1/G2 hooks: `claude_settings.json.j2` adds a PreToolUse(Bash) entry; `pre-commit-config.yaml.j2` adds a `repo: local` entry. Emitted to `.claude/hooks/` always (so it exists inside worktrees); wiring is mode-specific. `cli.py` `_render_hooks` adds it to the rendered set; `doctor` adds it to the required-paths checklist.

This is the non-evadable guarantee: even if the Phase-0 orchestrator mis-routes (LLM judgment, no diff), a `trivial`/`standard` change that actually touches a migration or auth path is blocked at commit time.

### 3.5 The `plan-reviewer` agent (architecture tier)

New `templates/agents/plan-reviewer.md.j2` (`model: sonnet`, tools `[Read, Grep, Glob]` — read-only, no Write/Edit/Bash). Fresh-context, never receives the planning reasoning; receives the spec + the plan file. Returns a structured verdict (REJECT codes for hallucinated paths, weak/missing acceptance criteria, scope creep, missing edge cases, missing-ADR-for-hard-to-reverse) + APPROVE. Used only in the architecture tier's `★ plan-review gate`. Mirrors LeRisque's plan-reviewer intent, scaled to ADE's conventions.

### 3.6 Phase-skill & composite ripple

- `ade-full.md.j2`: insert the **Router** step + ready-confirm between Phase 0 and Phase 1; annotate each phase heading with its masking rule (e.g. "Phase 3 — DESIGN CHECK *(skipped for `trivial`)*"); add the architecture `★ plan-review gate` after Phase 2; add the forced-escalation rules + the tier-confirmation gate; add the new hook to the orchestrator's awareness. Add a `Routing` circuit-breaker line if needed (plan-review max 2 iterations).
- `00-intent.md.j2`: add a short note that the intent's `Affected Areas` + `Type` + `Scope` feed the Router, so they should name security/auth/schema/API impact explicitly when present (improves Phase-0 escalation accuracy).
- `ade-code.md.j2` / `ade-review.md.j2`: honor tier masking (code skills note design-check is skipped for trivial; review skill notes the quick-pass-vs-fan choice and the architecture plan-review gate).
- `claude_md_section.md.j2`: document the three tiers + the Router + `.claude/ade-routing.json` pointer + the new hook in the Circuit Breaker / hook list.

### 3.7 CLI & detection

- `cli.py` `init`: seed `.claude/ade-routing.json` (seed-if-missing, created/kept print line); `_render_hooks` renders `check-escalation-paths.py`; `_emit_claude_hooks` / copilot config wire it; `doctor` `required_paths` gains the hook + (as a bootstrap/WARN) the routing config.
- `detect.py`: no change required (config defaults are stack-neutral; user edits for their repo).

### 3.8 Documentation

`docs/ade-architecture-design.md`:
- New "## Blast-radius routing (G4)" section: the three tiers, the per-tier phase map, the hybrid classifier (deterministic forced-escalation + orchestrator size judgment), the Ship-time hook, the human gate.
- Pipeline description: note the Router step after Phase 0 and the architecture plan-review gate.
- Deterministic hook layer section: add `check-escalation-paths.py`.
- Subagent catalog: add the `plan-reviewer` row (architecture tier).
- Circuit-breaker table: add the plan-review loop (max 2).
- Note the S/M/L scope estimate now *feeds* the Router (no longer purely informational).

## 4. Files touched (summary)

**New:** `skills/phases/route.md.j2`, `agents/plan-reviewer.md.j2`, `hooks/check-escalation-paths.py.j2`, `ade-routing.json.j2`.
**Edited:** `cli.py`, `claude_settings.json.j2`, `pre-commit-config.yaml.j2`, `skills/ade-full.md.j2`, `skills/ade-code.md.j2`, `skills/ade-review.md.j2`, `skills/phases/00-intent.md.j2`, `claude_md_section.md.j2`, `docs/ade-architecture-design.md`. (`detect.py`: no change.)

## 5. Tests

**Add:**
- `test_init_seeds_ade_routing_file` — `.claude/ade-routing.json` exists, is valid JSON, has `escalation_globs`/`keywords`; seed-if-missing preserves an edited file.
- `test_init_generates_plan_reviewer_agent` — exists, `model: sonnet`, read-only tools, "plan"/"refute"/"acceptance criteria" present, fresh-context wording, no `@vitals`/stack hardcoding.
- `test_init_generates_escalation_hook` — `.claude/hooks/check-escalation-paths.py` rendered; wired in `.claude/settings.json` (claude mode) and `.pre-commit-config.yaml` (copilot mode).
- `test_escalation_hook_blocks_unrouted_migration` / `test_escalation_hook_allows_when_floor_met` / `test_escalation_hook_noop_without_routing` — unit tests for the hook logic (block when diff touches an architecture glob below floor; allow when tier meets floor; no-op when no `routing.md`). In `tests/test_hooks.py`.
- `test_ade_full_describes_router_and_tiers` — `ade-full.md` contains the Router step, all three tier names, the per-phase masking annotations, the architecture plan-review gate, and the forced-escalation rules.
- `test_doctor_checks_escalation_hook` — removing the hook makes `doctor` FAIL.

**Update:**
- `test_init_claude_mode_emits_settings_and_hooks` — assert `check-escalation-paths.py` is wired alongside the G1/G2 hooks.
- `test_init_copilot_mode_emits_precommit_config` — assert the escalation hook entry present.
- Hook-count / settings-merge idempotency tests — account for the third hook.

**Guard:** the G5 `test_no_stale_stack_references` still passes (the new templates must carry no `@vitals`/`backend-coder`/etc.; `routing.json` is `.json` not `.md` so it is outside that test's `.md` glob — fine, but keep its example paths stack-neutral).

## 6. Edge cases

- **No diff at Phase 0:** the Router classifies from declared affected areas; the Ship hook is the deterministic backstop on the real diff. Documented as the intended two-layer design.
- **Mis-route downward:** a `trivial`/`standard` change that actually edits a migration/auth path is blocked by the hook at commit; the orchestrator must re-route up.
- **Manual commit outside ADE (no `routing.md`):** hook is a no-op — it must never break non-ADE commits.
- **Empty/edited `ade-routing.json`:** seed-if-missing preserves user edits; if the file is malformed JSON, the hook fails safe (treats as "no escalation globs" → does not block; logs a warning) so a bad config never hard-bricks commits. The orchestrator likewise falls back to "everything ≥ standard" if it cannot parse the config (conservative).
- **`architecture` triggered but user disagrees:** user may override **up** but not below a forced floor; down-override out of a floor is refused with the reason.
- **trivial change that grows mid-flight:** if Phase 4 file changes exceed the size threshold or touch an escalation glob, the existing scope-drift rule + the Ship hook catch it; the orchestrator re-routes.

## 7. Rollout / compatibility

- Existing ADE projects re-running `ade init` get `.claude/ade-routing.json`, the `plan-reviewer` agent, and the new hook (wired idempotently into existing settings). The pipeline gains a Router step and tier masking — a deliberate, additive workflow change; `standard` behaves exactly as before, so existing tasks are unaffected unless explicitly routed `trivial`/`architecture`.
- Effort is **Medium** (the gap analysis estimated "Low" for a minimal router; the research-backed additions — ADR + plan-review gate + the deterministic Ship hook + config — raise it to Medium, accepted deliberately for the robustness they buy).

## 8. Open questions

None blocking. Future enhancements (deferred): an ML/LLM diff-risk score to refine size judgment; auto-population of `escalation_globs` from `detect.py` stack knowledge; per-tier model-tier selection.
