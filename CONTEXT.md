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
