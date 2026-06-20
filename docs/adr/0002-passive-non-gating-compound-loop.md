# ADR 0002 — The compound loop is passive, prose-driven, and non-gating

**Status:** Accepted
**Date:** 2026-06-20
**Context tier:** system-wide (ADE pipeline)

## Context

G3 adds the compound loop: Phase 9 **codifies** a task's knowledge into durable artifacts
(`docs/learnings/` + `docs/review-calibration.md`) that later tasks read back (Phase 1 reads
learnings; Phase 6 reads the calibration corpus). We had to decide *how forceful* this
machinery is. Two reference points pulled toward more force:

- **LeRisque** gates on its review signal: an SLI (`> 10` post-PR review comments) **halts**
  new PRs entering the pipeline and triggers human recalibration. Its Judge then computes
  PASS/FAIL from corpus severities.
- **G4 (this toolkit's own prior gap)** added a deterministic **enforcement hook**
  (`check-escalation-paths`) precisely because routing has a security property that must be
  non-evadable. A reader who just saw G4 will expect G3 to follow suit.

ADE specifics pull the other way: it is a **scaffolder** for arbitrary target projects, the
compound artifacts are version-controlled docs (not security boundaries), and ADE has **no
post-PR CI loop it could halt** — Phase 9 runs in the same session that opened the PR,
before any bot has reviewed it.

## Decision

The compound loop is **passive, prose-driven, and non-gating**:

1. **Passive calibration, not prompt-rewriting.** Phase 6 review agents read
   `docs/review-calibration.md` *fresh every run* and prioritize the project's recurring
   finding-classes. The corpus *is* the tuning. The retro never edits the shipped review
   skill/agent prompt text.

2. **The review-findings signal is a health metric, not a gate.** It is surfaced at Retro
   and its only durable effect is incrementing a finding-class's frequency. There is no
   `> N → halt`; ADE has nothing to halt. (Deliberate divergence from LeRisque's SLI.)

3. **Frequency orders the corpus; it never promotes severity.** Severity is assigned from a
   finding's badness; recurrence drives prominence (top-of-list), not escalation — so the
   loop can never silently harden the merge gate.

4. **No enforcement hook.** Unlike G4, G3 ships no deterministic hook. The artifacts are
   ordinary docs with no security property to guarantee; correctness of the loop is the
   orchestrator's and the `compounder` subagent's job, recorded in skills (prose), like
   routing's size-judgment half.

## Consequences

- The loop is cheap, reversible, and safe: a wrong or empty corpus degrades to today's
  behavior (an empty corpus is a no-op), and nothing it does can block a merge.
- ADE gains a genuine compound loop without importing LeRisque's CI-scale machinery
  (halt/recalibrate), which has no analogue in a session-scoped scaffolder.
- The asymmetry with G4 is intentional and recorded here: **G4 hooks because it guards a
  security boundary; G3 does not because it guards nothing — it accrues knowledge.**

## Alternatives considered

- **Gating signal (LeRisque's `>10 → halt`):** rejected — ADE has no post-PR pipeline to
  halt; the signal would point at nothing.
- **Active prompt-rewriting (retro edits the review prompt):** rejected — brittle, risks
  corrupting the shipped review prompt, hard to review/revert; passive read-back achieves
  the same tuning safely.
- **Auto-promoting severity by frequency:** rejected — conflates "how often" with "how bad"
  and would silently harden the merge gate with no human in the loop.
- **An enforcement hook (G4 parallel):** rejected — there is no security property to
  enforce; a hook would be ceremony without a guarantee.
