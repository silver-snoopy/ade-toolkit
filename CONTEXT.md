# CONTEXT — ADE domain glossary

The shared, canonical language of the ADE toolkit. Definitions only — no implementation
detail. Update when a term is coined, sharpened, or changes meaning.

## Pipeline

- **Phase** — one of the ten… now **nine** numbered stages (0–9) of the ADE SDLC:
  0 Intent, 1 Research, 2 Plan, 3 Design-check, 4 Implement, 5 Quality-gate, 6 Review,
  7 Docs, 8 Ship, 9 Retro. Live verification was removed in G5; the suite is the
  acceptance mechanism.
- **Orchestrator** — the main-session Claude (Opus) that owns context and the write path
  and dispatches subagents. It never writes application code itself.

## Routing (G4)

- **Tier** — the routing classification assigned to a task, governing which phases run.
  Exactly three: **trivial**, **standard**, **architecture**.
  - **trivial** — a tiny, self-contained change (e.g. a copy/comment/config one-liner or a
    small isolated fix) that runs a cut-down path: lightweight research, no design-check,
    no retro, single review pass — but **always** keeps author-separated TDD, the
    deterministic quality gate, and the merge gate.
  - **standard** — the full nine-phase flow. The default.
  - **architecture** — standard plus extra rigor for high-blast-radius work: at least one
    ADR and an adversarial Plan Soundness Review before code.
- **Routing** — the act of assigning a tier. It is the closing sub-step of **Phase 0
  (Intent)**, not a separate phase. (NB: distinct from "a change to the architecture doc"
  — the *architecture tier* is a routing classification.)
- **Blast radius** — the breadth of impact/risk of a change; the property routing
  estimates. Larger blast radius → higher tier.
- **Forced-escalation** — a deterministic rule that raises a task's tier regardless of its
  estimated size, because the change touches a sensitive category (security/auth/secrets/
  crypto, schema/migrations, public-API). Forced-escalation sets a **floor**; it can never
  be overridden downward.
- **Floor** — the minimum tier a forced-escalation rule imposes (e.g. an auth change has a
  floor of `standard`; a migration has a floor of `architecture`).
- **Escalation path** — a file path/glob whose modification triggers forced-escalation.
  A baseline set is compiled into the enforcement hook and cannot be removed by config;
  `.claude/ade-routing.json` may only extend it.
- **Plan Soundness Review** — the architecture-tier adversarial review of the *plan*
  (not the code) by a fresh-context reviewer that tries to refute it against the spec.
  Distinct from the **PLAN GATE**, which is a structural completeness check applied to all
  tiers.

## Compound loop (G3)

- **Compound loop** — the cross-task feedback mechanism by which each completed task
  deposits durable, reloadable knowledge so the next task is cheaper: Phase 9 **codifies**
  learnings that Phase 1 reads back, and review findings accrete into a corpus that Phase 6
  reads back.
- **Codify** — the closing sub-step of **Phase 9 (Retrospective)**: turn the cycle's
  reflection into durable knowledge by writing a Learning and merging the task's review
  findings into the calibration corpus. (Parallel to G4's "Route" sub-step of Phase 0 — a
  sub-step, not a renamed phase.) Distinct from the **Retro** proper, which looks back and
  records per-task metrics (`retro.json`).
- **Learning** — a durable, per-task knowledge artifact at `docs/learnings/{date}_{slug}.md`
  capturing a *thing we discovered* about how the system/tools/domain behave (including
  failed approaches) and **why it matters** — the transferable mechanism, not an anecdote.
  Distinct from an **ADR** (a decision we *committed to*) and a **spec** (the WHAT/plan):
  *if you chose it, it's an ADR; if you found it out, it's a Learning.*
  _Avoid_: solution, retro note.
- **Calibration corpus** — the single accreting, version-controlled doc at
  `docs/review-calibration.md` listing recurring **finding-classes**; read **fresh** by
  Phase 6 review agents every run so the project's recurring issues are checked proactively.
  The corpus *is* the review tuning (passive read-back; review prompts are never rewritten).
- **Finding-class** — one recurring category of review finding in the calibration corpus,
  carrying a severity (assigned from the finding's *badness*), a frequency (how many tasks
  it recurred in), a greppable signal, and an example. **Frequency orders the corpus; it
  never promotes severity** — recurrence drives prominence, not escalation.
- **Review-findings signal** — the per-task count of Phase 6 review findings (plus post-PR
  bot comments when a merged PR with bot reviews exists), surfaced at Retro as a health
  number. Its only durable effect is incrementing a finding-class's frequency; it is **not**
  a gate (ADE has no post-PR loop to halt). _Avoid_: SLI.
- **Compounder** — the read-only subagent (sonnet) that distills a task's findings and
  learnings into the Learning body and the corpus merge; the orchestrator owns the final
  write. Runs only in the Codify sub-step (standard + architecture tiers; trivial skips it).
