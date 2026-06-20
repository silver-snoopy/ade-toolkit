# Design — G3: The compound loop

**Date:** 2026-06-20
**Status:** Draft
**Scope:** ADE toolkit (`src/ade/`) — closes gap G3 from `docs/ade-sdlc-gap-analysis.html` (Recommendations move #6).
**Depends on:** G1 (author-separated TDD), G2 (deterministic hook layer), G5 (9-phase pipeline, stack-neutral phases), G4 (blast-radius routing) — all shipped.
**Companion docs:** glossary terms in `CONTEXT.md` (Compound loop section); the passive/non-gating decision in `docs/adr/0002-passive-non-gating-compound-loop.md`.

> **Terminology (hardened during grill — see `CONTEXT.md`):** the durable per-task artifact is a **Learning** in `docs/learnings/` (not "solution"). Phase 9 stays **Retrospective**; its closing sub-step is **Codify** (parallel to G4's "Route" sub-step). The per-task findings metric is the **review-findings signal** (not "SLI" — there is no gate). The overall mechanism is the **compound loop**.

## 1. Context & motivation

The gap analysis flagged that ADE's Phase 9 retro **does not compound**: it emits an ephemeral, per-task `.ade/tasks/<id>/retro.json` that dead-ends. The two artifacts ADE *does* persist across tasks — `CONTEXT.md` (terminology) and ADRs (decisions) — are genuinely strong, "better than most" of the surveyed field. What's missing is the third substrate the field has converged on: a durable **solutions/learnings** sink that the next task's Research phase reads back, plus a **feedback metric** that tunes the review gate so the pipeline self-improves.

> Study §12 ("The compound step — does the task improve the next one?") and Gap G3 (§G3): *"ADE's retro doesn't compound. The CONTEXT.md + ADR machinery is the right substrate; it needs a durable solutions/learnings sink and a feedback metric (à la LeRisque's SLI → calibration) so the pipeline self-improves."* Recommendations move #6: *"Promote Phase 9 to a compound step: durable solutions/learnings doc + a review-findings SLI that tunes Phase 6 prompts."* — 8/10 surveyed systems have a compound/learn loop; ADE's retro is one of the two that don't.

Two evidence sources shaped this design:

- **LeRisque** (`PetroczyP/LeRisque`, read directly). Two reusable mechanisms:
  - A **calibration corpus** (`.claude/agents/judge/calibration-corpus.md`) — severity-ordered finding-classes distilled from 329 post-PR review-thread comments across 6 PRs into a ~20-class taxonomy. Each class carries `What it is / Signal (greppable) / Severity / Frequency / Verbatim examples (PR link)`. The Judge reads it **fresh at every invocation** (not cached) and walks the classes in order against the diff. Recalibration is gated by an **SLI** (count of inline review comments at PR open; target `< 10`, breach at `> 10`): on breach, file a regression issue, halt new PRs, append findings to the corpus, recalibrate. An **off-corpus escape hatch** lets the Judge surface novel patterns (`# OFF-CORPUS:`) without blocking, feeding the next recalibration.
  - A **durable learnings sink** (`po-capture-learning` → `RnD/Vault/learnings/<date>_<slug>.md`) with a mechanism-focused template whose load-bearing section is **"Why this matters"** — *"the part that compounds — without it you have an anecdote; with it, a principle that transfers."* Read back before brainstorming the next problem.

- **compound-engineering** (`EveryInc/compound-engineering-plugin`): `ce-compound` writes per-task `docs/solutions/` and seeds a `CONCEPTS.md` digest. The biggest *conceptual* idea in the corpus — "each completed task deposits durable, reloadable knowledge so the next task is cheaper."

**ADE-specific shape.** ADE is a *scaffolder* for arbitrary projects, not a single dogfooded repo. Three consequences drive the design:
1. The compound artifacts live in the **target** project (joining `CONTEXT.md`/ADRs/specs), seeded empty by `ade init` — ADE cannot ship a pre-populated, project-specific corpus.
2. The signal source must be **always available offline**: ADE cannot assume CodeRabbit/Copilot bots exist on every target repo, so the baseline review-findings signal is **Phase 6's own review findings** (already counted in `retro.json`), with post-PR bot comments as an *optional* augmentation.
3. ADE has **no post-PR CI loop to halt**, so the review-findings signal is a **health signal, not a gate**: the compounding itself is the response to a high finding-count, not a pipeline halt. (We deliberately do not adopt LeRisque's gating SLI — hence the term "review-findings signal," not "SLI.")

This was verified empirically before settling the design: `ade init --project-dir .` in a fresh git repo seeds `CONTEXT.md` and `docs/{adr,specs}/` at the **target project root** (via `bootstrap_targets` + `_render_and_write_if_missing` in `cli.py`), and the rendered phase skills reference those paths relative to project root — Phase 1 research already reads `CONTEXT.md` + `docs/adr/*` back this way. The two new artifacts reuse that proven seeding-and-read-back machinery exactly.

## 2. Goals / non-goals

**Goals**
- A durable **learnings sink**: a mechanism-focused **Learning** at `docs/learnings/{YYYY-MM-DD}_{slug}.md`, written at the **Codify** sub-step of Phase 9 (standard + architecture tiers) **only when the task yielded a genuinely transferable insight**, seeded with a README + template by `ade init`.
- Phase 1 Research (R2.1 scouts) reads `docs/learnings/` back, alongside the existing `CONTEXT.md` + `docs/adr/*` — making the next task cheaper.
- A durable **calibration corpus** at `docs/review-calibration.md`: a single accreting list of recurring finding-classes ordered by frequency, seeded empty by `ade init`.
- Phase 6 review agents (every tier, incl. trivial) read the corpus **fresh every run** and prioritize the project's top recurring finding-classes (passive tuning — the corpus *is* the tuning; no prompt-rewriting).
- The **corpus merge runs unconditionally** at Codify (every standard/architecture task folds its findings in; zero findings = no-op), independent of whether a Learning is written.
- A **review-findings signal**: the per-task Phase 6 finding count (+ best-effort post-PR bot comments on *prior* merged PRs, see §3.3) surfaced as a health number at Retro. Its only durable effect is incrementing a finding-class's `Frequency`; **frequency orders the corpus, it never promotes severity**, and it is **not a gate**.
- A dedicated **`compounder` subagent** (sonnet, read-only analysis) distills the task's findings/learnings into the Learning body + the corpus-merge instructions; the orchestrator owns the final write.
- Phase 6 **persists its Review Output** to `.ade/tasks/<task-id>/review.md` so the `compounder` has real file-path inputs.
- `retro.json` is **retained** as a per-task metrics source the compounder reads; Codify is layered on top, not a replacement.
- Trivial tier stays as G4 defined it: Phase 9 (and thus Codify) **skipped** — trivial *reads* the corpus at Phase 6 but does not contribute (it benefits from accumulated knowledge without paying the Codify cost).
- All affected tests updated; suite stays green; the G5 stale-reference guard (`test_no_stale_stack_references`) still passes.

**Non-goals (deferred / out of scope)**
- **No enforcement hook.** The loop is prose-driven (skills), like routing — the artifacts are just version-controlled docs; there is no security property to enforce deterministically.
- **No active prompt rewriting.** Review tuning is passive read-back only; the retro never edits the shipped review skill/agent prompt text.
- **No pipeline halt / regression-issue automation.** ADE has no post-PR CI loop; the review-findings signal is surfaced as a health number, not a gate (deliberate divergence from LeRisque's `> 10 → halt`). See ADR 0002.
- **No automatic severity promotion.** Frequency orders the corpus; severity is assigned from a finding's badness and never bumped by recurrence (avoids silently hardening the merge gate). See ADR 0002.
- **No `CONCEPTS.md` rolling digest.** Per-task Learning files + grep is the read-back mechanism (chosen over compound-engineering's digest to avoid a second per-task artifact). May be revisited later.
- **No cross-project corpus.** Each installed project compounds independently; ADE ships empty seeds.
- **No new model-tier changes** beyond adding the sonnet `compounder`.

## 3. Design

### 3.1 The learnings sink — `docs/learnings/`

A mechanism-focused **Learning** per task (when one exists), `docs/learnings/{YYYY-MM-DD}_{slug}.md` (mirrors the `docs/specs/{date}_{slug}.spec.md` convention — per-task, dated, slugged, greppable, no merge contention). A Learning records a *thing we discovered* (including a failed approach), not a *decision we committed to* (that is an ADR). Written **only when the task yielded a genuinely transferable insight** — if nothing rises above routine, the `compounder` writes none and says so at Retro (quality over volume keeps the Phase-1 read-back valuable). Template sections (load-bearing one bolded):

```
# <one-line problem statement>

## Context
2–3 sentences: what was the task, what were we trying to do.

## What we tried
- Approach X — expected Y, found Z

## What we learned
The concrete finding. Specifics — names, paths, numbers.

## Why this matters
The underlying mechanism — the part that compounds. A principle that transfers
to the next task, not an anecdote.

## Gotchas
Sharp edges someone applying this should know.

## Related
- Spec: docs/specs/<...>
- ADRs: docs/adr/<...>
- Glossary terms touched: <CONTEXT.md terms>
```

Seeded by `ade init` as `docs/learnings/README.md` (explains the sink + embeds this template), exactly like `docs/specs/README.md`.

### 3.2 The calibration corpus — `docs/review-calibration.md`

A single accreting, version-controlled doc ordered by frequency, seeded empty (header + format + a "read this fresh at the start of every review" note). Each finding-class:

```
### <class name>
- Severity: blocker | fix-before-merge | nice-to-have
- Frequency: N tasks
- Signal: <greppable description of what to look for>
- Example: <task slug / file#anchor / short quote>
```

**Read-back (passive tuning):** Phase 6 review agents read this file fresh at the start of every review and prioritize the highest-frequency / highest-severity classes for *this* project. An empty corpus is a no-op (behaves exactly as today) — no first-task bootstrapping value is lost.

**Merge rule (in the `compounder`):** match an incoming finding to an existing class by `Signal` → increment `Frequency` + append the new example; else add a new class. `Severity` is assigned from the finding's *badness* and is **never** changed by recurrence. `Frequency` drives **ordering only** — the most-recurring classes float to the top so reviewers check them first. (No frequency→severity promotion; see ADR 0002.)

### 3.3 The review-findings signal

Phase 9 already records `review.{high,med,low}Findings` in `retro.json`. The **review-findings signal** is the per-task Phase 6 finding count, surfaced at Retro as a health number — e.g. *"6 findings this task; class 'silent-fallback' now seen in 3 tasks."* Its only durable effect is incrementing finding-class `Frequency` in the corpus. There is **no halt/gate** (ADE has no post-PR loop to halt; see ADR 0002) — the corpus accretion *is* the response.

**Post-PR bot comments — best-effort, over *prior* PRs.** Bot reviews (CodeRabbit/Copilot) arrive asynchronously *after* Codify has run for the originating task, so they are never available for *this* task. Instead, the `compounder` opportunistically checks **recently-merged prior PRs** (e.g. `gh pr view`) whose bots have since posted, and folds those finding-classes into the corpus on a *later* task's Codify. Absent `gh`/bots/PRs → findings-only, no failure. This keeps the augmentation honest about *when* it fires.

### 3.4 The `compounder` subagent

New `templates/agents/compounder.md.j2` (`model: sonnet`, tools `[Read, Grep, Glob]` — read-only; no Write/Edit/Bash, matching how `plan-reviewer` is scoped). Fresh context. Inputs (all **file paths**, per ADE convention): `.ade/tasks/<task-id>/review.md` (the persisted Phase 6 output, §3.5), `.ade/tasks/<task-id>/retro.json`, the spec, the diff, the current `docs/review-calibration.md`, and — when the orchestrator gathered them (§3.3) — a temp file of prior-PR bot comments. Returns structured output: (a) the **Learning body** per §3.1, *or an explicit "no transferable learning" verdict with a one-line reason*; and (b) the **corpus-merge instructions** per §3.2 (which classes to increment / which to add; never a severity change). The **orchestrator owns the final write** of both files and runs any `gh` calls (the compounder is read-only and never shells out), consistent with ADE's "orchestrator owns the write path; subagents analyze."

### 3.5 Phase-skill ripple

- `skills/phases/09-retro.md.j2` — keep the `retro.json` block (now framed as a compounder metrics input), then add the **Codify sub-step**: dispatch `compounder` → orchestrator (always) merges `docs/review-calibration.md`, (conditionally) writes `docs/learnings/{date}_{slug}.md`, surfaces the review-findings signal, and optionally runs the prior-PR `gh` check (§3.3). Explicitly **skipped for trivial** (per G4).
- `skills/phases/06-review.md.j2` — two edits: (1) instruct review agents to read `docs/review-calibration.md` fresh at the start of the review and prioritize the project's top recurring finding-classes (all tiers); (2) add a closing step to **persist the Review Output to `.ade/tasks/<task-id>/review.md`** (§3.5 input for Codify).
- `skills/phases/01-research.md.j2` — add `docs/learnings/*` to the R2.1 "Project inputs" list (line ~10) and instruct scouts to grep it for prior learnings on the task's area; orchestrator surfaces relevant ones.
- `skills/ade-ship.md.j2` — Phase 9 section gains the Codify sub-step (mirrors `09-retro`).
- `skills/ade-full.md.j2` — Phase 9 heading reflects Codify; annotate "skipped for trivial".
- `claude_md_section.md.j2` — document the two artifacts + the compound loop + the `compounder`.

### 3.6 CLI & detection

- `cli.py` `init`: add two `bootstrap_targets` entries — `bootstrap/learnings-README.md.j2` → `docs/learnings/README.md`, and `bootstrap/review-calibration.md.j2` → `docs/review-calibration.md` (both seed-if-missing, created/kept print line). Add `compounder.md` to the rendered agents set.
- `doctor`: `bootstrap_paths` gains `docs/learnings` + `docs/review-calibration.md`, reported if missing exactly like the existing `CONTEXT.md` / `docs/adr` / `docs/specs` bootstrap checks (they are seeded by `init`).
- `detect.py`: no change (artifacts are stack-neutral).

### 3.7 Documentation (repo)

`docs/ade-architecture-design.md`:
- New "## Compound loop (G3)" section: the two artifacts, the data flow (Phase 9 Codify writes → Phase 1 reads learnings / Phase 6 reads calibration), the review-findings signal as health-signal-not-gate, the `compounder`, the passive-tuning decision, the trivial-tier exclusion.
- Subagent catalog: add the `compounder` row (sonnet, read-only).
- Phase 9 description: note the Codify sub-step (was retro-only).
- Phase 1 / Phase 6 descriptions: note the read-back; Phase 6 also persists `review.md`.
- `CONTEXT.md` (Compound loop section) + **ADR 0002** (passive/non-gating compound loop) — both written during the grill.

## 4. Files touched (summary)

**New:** `agents/compounder.md.j2`, `bootstrap/learnings-README.md.j2`, `bootstrap/review-calibration.md.j2`. Plus repo docs already written during grill: `CONTEXT.md` (Compound loop section), `docs/adr/0002-passive-non-gating-compound-loop.md`.
**Edited:** `cli.py`, `skills/phases/09-retro.md.j2`, `skills/phases/01-research.md.j2`, `skills/phases/06-review.md.j2`, `skills/ade-ship.md.j2`, `skills/ade-full.md.j2`, `claude_md_section.md.j2`, `docs/ade-architecture-design.md`. (`detect.py`: no change.)

## 5. Tests

**Add:**
- `test_init_seeds_learnings_dir` — `docs/learnings/README.md` exists, contains the template sections (incl. "Why this matters"); seed-if-missing preserves an edited file.
- `test_init_seeds_review_calibration` — `docs/review-calibration.md` exists with the finding-class format (`Severity`/`Frequency`/`Signal`); seed-if-missing preserves edits.
- `test_init_generates_compounder_agent` — exists, `model: sonnet`, read-only tools (no Write/Edit/Bash), mentions "learning"/"calibration"/"why it matters"; no `@vitals`/stack hardcoding.
- `test_retro_skill_describes_codify_step` — `09-retro.md` references `docs/learnings/`, `docs/review-calibration.md`, the `compounder`, the "Codify" sub-step, the conditional-Learning rule, and "skipped for trivial".
- `test_research_reads_learnings` — `01-research.md` lists `docs/learnings/` as an R2.1 scout input.
- `test_review_reads_calibration` — `06-review.md` references reading `docs/review-calibration.md` fresh.
- `test_review_persists_output` — `06-review.md` instructs persisting the Review Output to `.ade/tasks/<task-id>/review.md`.
- `test_doctor_checks_compound_artifacts` — removing the seeds makes `doctor` report them missing.

**Update:**
- Any init-counts / bootstrap-list tests that assert the seeded-file set or agent set — account for the two new seeds + the `compounder` agent.

**Guard:** `test_no_stale_stack_references` still passes (new `.md` templates carry no `@vitals`/`backend-coder`/`frontend-coder`/`Playwright`/`docker compose`/`localhost`/`NO EXEMPTIONS`/`07-verify`/`qa-verify`/`/10`).

## 6. Edge cases

- **Empty corpus / first tasks:** review reads an empty `docs/review-calibration.md` → no-op, behaves exactly as today. No bootstrapping value lost.
- **No prior learnings:** R2.1 grep of an empty `docs/learnings/` → no-op.
- **No transferable learning this task:** the `compounder` writes no Learning and notes "routine — no Learning" at Retro; the corpus merge still runs. Keeps `docs/learnings/` high-signal.
- **Trivial tier:** skips Phase 9 → no Learning, no corpus update; but Phase 6 still *reads* the corpus (consistent with G4).
- **No `gh` / no bots / no merged PR:** review-findings signal = Phase 6 findings only; no failure, no external dependency.
- **Parallel tasks:** per-task Learning files never collide; the single `review-calibration.md` is written by the orchestrator at Codify on the task's own branch and merged normally — same contention profile as `CONTEXT.md` today.
- **User edits/deletes an artifact:** seed-if-missing respects an existing file; a deleted artifact is reseeded empty on next `ade init`, never overwriting a present one (`_render_and_write_if_missing` semantics).
- **A finding doesn't fit any class:** the compounder adds a new class (ADE's corpus is per-project and unbounded, so novel patterns are added directly rather than parked).

## 7. Rollout / compatibility

- Existing ADE projects re-running `ade init` get `docs/learnings/README.md`, `docs/review-calibration.md`, and the `compounder` agent (seed-if-missing; existing files untouched). The pipeline gains a Phase-9 Codify sub-step, a Phase-6 `review.md` persist step, and two read-backs — additive; `standard` behavior is otherwise unchanged, and an empty corpus/learnings set is a no-op, so existing tasks are unaffected until learnings accrete.
- Effort is **Medium** (comparable to G4): three new templates, six skill/CLI edits, a subagent, and the test/doc ripple — no new hook, no runtime code.

## 8. Open questions

None blocking. Future enhancements (deferred): a `CONCEPTS.md`-style rolling digest over `docs/learnings/`; richer post-PR bot-signal ingestion; a cross-project corpus seed library; corpus pruning for stale finding-classes.
