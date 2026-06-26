# ADE — what we still lack, and where to improve (state: 2026-06-26)

Companion to `docs/ade-sdlc-gap-analysis-2026-06.html` (the 17-system field re-benchmark, 2026-06-21). This doc re-states ADE's competitive standing after the post-06-21 ships and lays out a prioritised gap/improvement roadmap. It is a planning artifact — each item is its own brainstorm→spec→plan→SDD cycle.

## 1. What changed since the field study (ground truth on `origin/main`)

The 2026-06-21 re-benchmark listed nine recommended moves. **Five shipped**, plus three more from the companion dev-pipeline study:

| Shipped | What | Merge |
|---|---|---|
| Design-time **threat modeling** (rec #2) | R3.3 threat pass — blind `threat-modeler`, trust-boundary STRIDE-lite + data classification + PII-gated privacy prompts; mitigations → acceptance criteria; ADR-0005; deep-research-grounded (25/25 verified) | `eb26379` (06-26) |
| **Privacy-by-design** (design-time half of rec #4) | 4-tier data classification + orthogonal PII flag + LINDDUN-GO prompts, gated by the PII flag | `eb26379` |
| **NFR forcing** (rec #5) | R3 category 4 forces a number or explicit "not constrained"; `spec-verifier` rejects non-falsifiable NFRs | `a04c0d9` (06-22) |
| **Standard-tier plan soundness** | blind `plan-reviewer` now runs a standard-tier coverage matrix (was architecture-only) | `a04c0d9` |
| Blind **stub-reviewer** | independent reviewer of Phase-3 stubs (wrong-but-compiling contracts) | `51de9c9` (06-22) |
| **Provenance grading** (rec #6) | two-axis CONFIRMED/CITED/ASSUMED on research claims; monotonic default; trust floor | `d424b7f` (06-23) |
| G1 doc defect (rec #8) | the `ade-implement` checklist contradiction | `a04c0d9` |

**Net competitive effect.** The report's "largest standards-rooting gap" (design-time security/privacy/NFR) is **closed**. ADE moves from tied-last on that axis to the field's **most integrated** design-time security+privacy treatment (mitigations become author-separated tests + ADRs + a routing signal — not an optional side-gate like gsd's), and is plausibly the **first system to scaffold privacy-by-design** (data classification) as a pipeline step — privacy was 0/17. The report's own "leapfrog thesis" has been *half-executed*; the frontier moves on.

## 2. Where ADE stands now (re-scored)

**Leader-class and protected:** intent/blast-radius routing · research rigor (now with two-axis provenance) · spec-blind CoVe verification · executable design-contract gate (now with a blind stub-reviewer) · hook-enforced author-separated TDD · compound learning loop · stack-agnosticism · **and now design-time security+privacy+NFR.** That is leadership on ~9 of the 12 dev-core dimensions.

**Still below the field — the honest gaps** (the rest of this doc): live runtime evidence · cross-model review diversity · repair-loop stall detection · the entire operational/compliance tail (incident loop, observability, release-safety, supply-chain, accessibility, runtime privacy) · and a set of strategic gaps the benchmark does not even score.

## 3. What ADE lacks — three tiers

### Tier A — Catch-up: dimensions competitors already beat ADE on

These are *not* leapfrogs; multiple systems do them and ADE is measurably behind. Highest credibility-risk if left open (the field can point at them).

**A1 — Live / runtime verification (the #1 gap).**
*State:* ADE has **zero runtime evidence** — Phase 6 verifies test-coverage only (the G6 regression, a deliberate casualty of the G5 stack-agnosticism win). *Field:* `case` hard-gates the PR on a runtime marker; `gstack` does real-browser QA with a fix loop; `oh-my-cc` has live verification + fix loops. ADE is "alone among strong systems with zero runtime evidence." *Idea:* un-park the **functional/acceptance-test tier** spec (`docs/superpowers/specs/2026-06-22-live-verification-design.md`) — author-separated tests that boot the assembled artifact via stack-agnostic `run`/`serve`/`verify` slots in `.ade/ade-stack.md`, executed Phase 5, persisted as durable automation. Scope to where value is high (CLI/lib/service) and keep visual UI as `(manual)`. *Effort:* Medium. *Leverage:* **Highest** — it is the single most-cited ADE weakness and the one a skeptic notices first.

**A2 — Cross-model / cross-family review.**
*State:* every reviewer is `model: sonnet` — a single-model fan with correlated blind spots; **and the new `threat-modeler` is also sonnet.** *Field:* `gstack` and `compound-engineering` fan across model *families* for decorrelated findings. *Idea:* route the **security lens + the new threat pass + architecture-tier plan refutation** to a different model family (the adversarial memo's "selective cross-model" — not everywhere, just where correlated misses are most expensive). *Effort:* Medium. *Leverage:* High, and now higher because the security-design surface just grew — a single model grading its own threat model is the exact failure mode author-separation exists to prevent.

**A3 — Repair-loop stall / no-progress detection.**
*State:* the Phase-5 fixer loop is a bare `max-3` counter. *Field:* `case` fingerprints each failure and aborts when two cycles match; `gsd` requires the issue count to strictly decrease and bails on a non-decreasing round. *Idea:* record a failure fingerprint + finding-count delta each iteration; stop early when the failure set stops shrinking (don't burn all three attempts on an identical error). *Effort:* Low. *Leverage:* Medium — cheap, and it directly improves the agent's cost/latency profile.

### Tier B — Leapfrog: the operational/compliance tail the whole field skips

Field-wide gaps (0–4 of 17). ADE just proved it can take one of these (security-design). The strategic thesis still holds: leading here beats matching peers on A.

**B1 — Incident → learning loop (still 0/17 — now THE remaining leapfrog).**
*State:* ADE's retro/compound loop reads `docs/learnings/` back, but has **no production-incident intake** — its mental model ends at ship. *Field:* **0 of 17.** Google SRE's blameless-postmortem-with-tracked-action-items is the canonical standard nobody scaffolds. *Idea:* a new **Phase-0′ Incident Intake** entry point parallel to intent — ingest a structured postmortem (SEV/timeline/root-cause) → emit mitigative tasks + preventative ADRs/spec-deltas; a "learnings-closure" check fails the next retro if a prior preventative action item is still open. This is the *closing* half of the cycle the threat pass opened: design-time threats → (if one escapes) an incident → a preventative learning that re-grounds the next threat pass. *Effort:* Medium-High. *Leverage:* **Highest leapfrog** — 0/17, maps onto ADE's single strongest differentiator (the compound loop), and composes with the threat pass into a story no competitor has.

**B2 — Observability as a build deliverable (1/17).**
*State:* no step requires emitting instrumentation/SLOs/runbooks. *Field:* only `agent-skills`. *Idea:* an `observability-engineer` that, given a feature, prescribes golden-signal instrumentation (structured logs, RED/USE metrics, trace spans), drafts SLI/SLO targets, and generates a runbook stub; a Phase-5 check verifies new code paths carry instrumentation. *Natural pairing:* the **NFR targets ADE now forces** are exactly the SLOs observability should assert — close the loop NFR(spec) → SLO(observability) → live-verify(A1). *Effort:* Medium-High. *Leverage:* High (only 1/17, and it reuses the freshly-shipped NFR forcing).

**B3 — Release safety + supply-chain (4/17 each).**
*State:* ADE stops at PR. *Idea (release):* `run/serve/verify/smoke/rollback` slots (overlaps A1) + a deployable-change checklist (rollout risk + rollback command + post-deploy verification). *Idea (supply-chain):* a Phase-5/8 `supply-chain-auditor` — ecosystem vuln scan + license-allowlist + CycloneDX/SPDX SBOM scaffolding; a ship hook fails on Critical CVEs, disallowed licenses, unpinned direct deps, or a missing SBOM. *Effort:* Medium. *Leverage:* Medium — real standards (NIST SSDF, SLSA) but less differentiated than B1.

**B4 — Accessibility hard gate (1/17) + runtime privacy (the slice the design-time pass doesn't reach).**
*Accessibility:* a conditional a11y gate on UI-touching changes (file-glob detector → axe-core/contrast/keyboard checks as acceptance criteria). *Runtime privacy:* the design-time pass classifies data and prompts privacy threats, but does **not** verify the *implementation* — a `pii-auditor` that data-flow-greps new code for classified data reaching logs/analytics/third parties without redaction, gated by the same PII flag the threat pass already sets. This is the natural Phase-6 extension of the privacy work just shipped. *Effort:* Medium. *Leverage:* Medium (accessibility is niche unless UI-heavy; runtime privacy compounds the new design-time privacy).

### Tier C — Strategic & novel (beyond the benchmark)

The field study scores ADE against peers; these are gaps the benchmark cannot see because they concern ADE's *own* nature as an agentic SDLC. The two starred items are, in my assessment, the most interesting improvement ideas available right now.

**C1 ★ — Turn the threat-modeler on ADE itself (secure the agentic supply chain).**
ADE just shipped a threat pass for the *user's* code — but **ADE's own pipeline is an unmodelled attack surface.** Three injection paths feed locked artifacts: web-research findings (partly guarded by the new provenance trust-floor), scout-read code, and — most dangerously — the **compound loop**: a poisoned `docs/learnings/` entry or `CONTEXT.md` glossary term propagates to *every future task*, and the loop is designed to read it back uncritically. ADE is one of the few systems with a real compound loop, so this risk is almost unique to it. *Idea:* (1) run the new `threat-modeler` against ADE's own pipeline as a one-off design exercise; (2) add an **integrity gate on compound-loop ingestion** — provenance/trust on what a learning asserts before it can re-ground a future spec (reuse the CONFIRMED/CITED/ASSUMED machinery already shipped); (3) treat `docs/learnings/` and `CONTEXT.md` as trust boundaries in their own right. *Why it matters:* it is the highest-leverage *novel* idea — it composes the two things ADE just shipped (threat modeling + provenance) and closes a real, ADE-specific vulnerability the whole benchmark is blind to. *Effort:* Low (the exercise) → Medium (the ingestion gate).

**C2 ★ — Outcome metrics: does the ceremony actually work?**
ADE has a great deal of process and **no measurement of whether it reduces defect-escape or rework.** Retro records per-task metrics (`retro.json`) but nothing links pipeline rigor → outcome. *Idea:* an efficacy signal — post-merge bot-comment count, and (once B1 exists) incident-linkage — fed back so tiers can be tuned by *evidence* rather than intuition (today `trivial`-vs-`standard` is pure LLM size-judgment). This is what makes the whole pipeline self-improving rather than self-asserting, and it is the data substrate B1 needs. *Effort:* Medium. *Leverage:* High strategically (it is how ADE learns whether any of the above is worth it).

**C3 — Codex-tier parity.** Author-separation and blind verification — now including the threat pass — are *conventions*, not structural guarantees, on Codex (no autonomous subagent dispatch; openai/codex#18513). As harnesses gain dispatch, close this; track upstream. *Effort:* External-dependent. *Leverage:* Medium.

**C4 — Pipeline cost / latency budgeting.** For a "fast agentic SDLC" there is no cost model. The threat pass was deliberately made *fast static analysis*; generalise that discipline — a per-tier token/time budget surfaced at routing, so ceremony is justified by blast radius. `ECC` already has pipeline FinOps (cost-report command, cost-tracker hook) — a competitor lead worth adopting. *Effort:* Medium. *Leverage:* Medium.

**C5 — Reproducible evidence pack + trace manifest.** ADE's competitive claims (this report included) rest partly on un-re-verified competitor data. An **evidence pack** (source snapshots, raw agent outputs, score rationales, dates) makes future studies reproducible. A **trace manifest** (requirement→ADR→task→test→review→PR→runtime, exported before temp cleanup) is table-stakes traceability (9/17 cover some of it) and is the spine C2/B1 read from. *Effort:* Medium. *Leverage:* Medium (meta, but it underwrites everything else).

## 4. Prioritised roadmap

| Rank | Move | Tier | Why now | Effort |
|---|---|---|---|---|
| 1 | **Live runtime verification** (un-park the functional-test tier) | A1 | The #1 cited weakness; the only dim where strong peers clearly beat ADE | Medium |
| 2 | **Incident→learning loop** (Phase-0′ Incident Intake) | B1 | The last 0/17 leapfrog; maps onto ADE's strongest differentiator; closes the cycle the threat pass opened | Med-High |
| 3 | **Turn the threat-modeler on ADE itself** + compound-loop integrity gate | C1 ★ | Novel, ADE-specific, composes the two newest capabilities, closes a real injection risk | Low→Med |
| 4 | **Cross-model review** for the security/threat lens + architecture plans | A2 | The new security-design surface needs decorrelated review; single-model self-grading is the failure mode author-separation exists to prevent | Medium |
| 5 | **Outcome metrics** (efficacy signal → tier tuning) | C2 ★ | Makes the pipeline self-improving; the data substrate B1 needs | Medium |
| 6 | **Observability-as-deliverable** (reuses the new NFR forcing → SLOs) | B2 | Only 1/17; composes with shipped NFR work | Med-High |
| 7 | **Stall / no-progress detection** in the fixer loop | A3 | Cheap; improves cost/latency | Low |
| 8 | **Runtime privacy auditor** + accessibility gate | B4 | Extends the just-shipped design-time privacy into implementation | Medium |
| 9 | **Supply-chain SBOM/license gate**; **cost budgeting**; **evidence pack/trace manifest** | B3/C4/C5 | Standards-rooted breadth; lower differentiation | Medium |

## 5. The three highest-leverage moves (if you do nothing else)

1. **Live runtime verification (A1)** — closes the one gap a skeptic notices first; ADE is alone among strong systems without it.
2. **Incident→learning loop (B1)** — the remaining 0/17 leapfrog, on ADE's home turf; with the threat pass it becomes a design→incident→learning cycle no competitor has.
3. **Threat-model ADE itself + compound-loop integrity (C1)** — the most interesting *novel* idea: point the capability you just built at your own pipeline, where a poisoned learning silently propagates to every future task.

---

*Method note:* This update re-scores ADE from ground-truth commits on `origin/main`; competitor scores are carried forward from the 2026-06-21 adversarial pass (the field is unchanged at a 5-day horizon, so a full 56-agent re-run was judged unnecessary). If primary-source competitor confidence is wanted on the dimensions where ADE now claims leadership (design-time security/privacy) or on the remaining gaps (live verify, cross-model), a targeted re-verification of those specific cells — not a full re-run — is the right next step.*
