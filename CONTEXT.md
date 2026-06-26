# CONTEXT — ADE domain glossary

The shared, canonical language of the ADE toolkit. Definitions only — no implementation
detail. Update when a term is coined, sharpened, or changes meaning.

## Pipeline

- **Phase** — one of the **nine** numbered stages (0–9) of the ADE SDLC:
  0 Intent, 1 Research, 2 Plan, 3 Design-check, 4 Implement, 5 Quality-gate, 6 Review,
  7 Docs, 8 Ship, 9 Retro. (Formerly ten — live verification was removed in G5; the test
  suite, via the acceptance-coverage gate, is now the acceptance mechanism.)
- **Orchestrator** — the main-session Claude (Opus) that owns context and the write path
  and dispatches subagents. It never writes application code itself.

## Authoring units

- **Agent Skill** — ADE's portable unit of behavior: a folder containing a `SKILL.md`
  (with `name` + `description` frontmatter and instructions), following the open
  [Agent Skills](https://agentskills.io) standard so the same skill runs across Claude Code,
  Codex, Gemini CLI, and Copilot. Loaded on demand (progressive disclosure); either
  auto-activated by description match or invoked explicitly.
  _Avoid_: command, slash command (Claude Code merged custom commands into skills),
  "composite/phase skill" (legacy ADE term).
- **Driver skill** — the single, explicitly user-invoked Agent Skill that sequences
  Phases 0→9 in order (the former `ade-full`). Its frontmatter marks it user-invoked so the
  pipeline's ordering never depends on probabilistic auto-activation. Distinct from a
  **phase skill** — the auto-activatable Agent Skill realizing one phase's behavior.
- **Worker subagent** — an isolation-critical role (scout, test-writer, implementer,
  spec-verifier, code/security-reviewer, compounder) emitted as a per-harness subagent
  definition carrying a model tier and tool allowlist, so its **context isolation is
  guaranteed, not merely requested**. Distinct from an **Agent Skill**, which carries
  portable behavior but cannot itself guarantee isolation. Phase skills *dispatch* worker
  subagents; on a harness without autonomous dispatch (Codex) they degrade to sequential
  in-context steps, with the deterministic hooks still enforcing the hard guarantees.

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

## Research provenance

ADE grades research evidence on **two orthogonal axes** (the doctrine-standard separation;
cf. NATO Admiralty Code). See `docs/research/provenance-and-evidence-grading-frameworks-2026-06.md`.

- **Trust** — the **source** axis: how reliable the *origin* of a finding is, independent of
  any particular claim. Carried on web sources as `high | medium | low` (also the
  prompt-injection signal). ≈ Admiralty source-reliability A–F. _Avoid_: using "trust" for
  the claim axis — that is **provenance**.
- **Provenance grade** — the **claim** axis: how ADE knows a particular claim is true,
  independent of how trustworthy its source is. One of three values below. ≈ Admiralty
  information-credibility 1–6. _Avoid_: conflating with **trust** (source axis) or with R5
  **Verify** (the Chain-of-Verification phase — a claim's provenance grade is assigned at
  research/synthesis time and says nothing about whether R5 has checked it).
  - **CONFIRMED** — first-hand observed (a scout read the actual code) **or** corroborated by
    ≥2 independent sources. ≈ Admiralty credibility-1 "confirmed by other sources".
    Deliberately **not** named "verified" — that word belongs to R5. _Avoid_: verified.
  - **CITED** — exactly one attributed source that *actually supports* the claim (a citation
    that does not support it is **not** CITED). Not cross-confirmed.
  - **ASSUMED** — inference or untraceable; the **monotonic default** — a claim that cannot be
    traced to first-hand evidence or a supporting source is ASSUMED, never silently a fact.
    Material ASSUMED claims route into the R3 interview before the spec locks.
    _Avoid_: unverified (legacy ad-hoc marker this replaces).

## Security & privacy risk

ADE runs a conditional, design-time risk analysis in Phase 1 (the **R3.3 threat pass**). See
`docs/research/threat-modeling-frameworks-2026-06.md` and `docs/adr/0005-design-time-threat-modeling.md`.

- **Trust boundary** — a point in a change's data flow where the level of trust changes (e.g.
  untrusted input crossing into a privileged process, data leaving a service). It is the **unit
  of the threat pass**: ADE analyses the ~1–3 boundaries a change introduces or crosses, not the
  whole system. Controls (authN, authZ, validation, encryption) belong *at* boundaries.
- **Threat pass** — the **activity**: the conditional R3.3 sub-step that, for each trust boundary
  in the change, classifies the data, elicits STRIDE-lite + abuse-case + (for PII) privacy threats,
  and assigns each a mitigation or an accepted residual risk. Single-shot, static, read-only.
  _Avoid_: "threat model" for the activity — that is the artifact (mirrors **Codify**/Learning,
  **Route**/routing.md).
- **Threat model** — the **artifact** the threat pass produces, at `.ade/tasks/<id>/threat-model.md`:
  the recorded boundaries, classifications, threats, and mitigations/residual risks. Distinct from
  the Phase-6 code-level **security review** (the threat pass is design-time and upstream).
- **Data classification** — the sensitivity label on data crossing a boundary, on **two orthogonal
  axes**: a four-level **tier** (`public` · `internal` · `confidential` · `restricted`) **plus** an
  independent **`regulated/PII` flag**. Orthogonal because regulated data isn't always most
  sensitive (an email is `internal` + PII; a signing key is `restricted`, not PII). The tier drives
  security controls; the PII flag gates the privacy prompt. _Avoid_: treating PII as a top tier.
- **Abuse case** — a way to use a feature that its implementer did not intend, letting an attacker
  influence its outcome via their action or input. The per-feature "how could this be misused?"
  prompt; selected abuse cases become acceptance criteria. _Avoid_: misuse case (used as a synonym).
- **Mitigation** — an **actionable, testable** control that answers a threat ("can success/failure
  be measured?"). Material mitigations become Phase-4 acceptance criteria; vague or hypothetical
  controls do not count. Distinct from a **Residual risk** (a threat consciously *not* mitigated).
- **Residual risk** — a threat the team consciously **accepts** rather than mitigates, recorded in a
  lightweight four-field form (threat, boundary, why accepted, compensating control) and surfaced at
  the ready-for-development gate (never silently dropped). _Avoid_: silently omitting it.
