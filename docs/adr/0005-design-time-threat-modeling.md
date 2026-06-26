# 5. Design-time threat modeling (trust-boundary STRIDE-lite + data classification)

Date: 2026-06-26

## Status

Accepted

## Context

ADE's only security analysis was **code-level and late**: a Phase-6 `security-reviewer` checks the implemented diff against the OWASP Top 10. Nothing examined the *design* — the trust boundaries a change introduces or crosses, the classification of data flowing across them, or the abuse cases a feature enables — while mitigations are still cheap to fold into the spec. Privacy/PII was not analysed at all. A 17-system field study put this in relief: **0/17** systems do design-time privacy/PII analysis and only **3/17** do design-time STRIDE — the strongest available leapfrog.

A deep-research survey (`docs/research/threat-modeling-frameworks-2026-06.md`, **25/25 verified claims confirmed, 0 killed**) found a defensible minimal method already exists and is endorsed by primary sources: **OWASP's own guidance is Shostack's Four-Question spine + a minimal-viable DFD with trust boundaries + STRIDE "for illustration,"** with mitigations required to be "actionable not hypothetical" and testable, and abuse cases mapping to "User Story acceptance criteria." The discipline that keeps it lightweight is **per-change scope** ("threat model every story"; the whole-system variant is explicitly called "dangerous").

## Decision

Add a **conditional Phase-1 sub-step — R3.3, the "threat pass"** — between the R3.2 interview and the R4 grill, so mitigations become acceptance criteria before R4 challenges them and R5 verifies them.

- **Method:** trust-boundary-anchored **STRIDE-lite**, wrapped in **Shostack's four questions** as the outer loop, scoped to the change's delta (~1–3 boundaries). STRIDE's fixed threat→control-property mapping keeps it productive, not open-ended. A hard **no-boilerplate guardrail**: every threat names the real boundary/flow in *this* change and a concrete, testable mitigation, or it is dropped.
- **Worker:** a dedicated **`threat-modeler`** (sonnet, read-only `[Read, Grep, Glob]`) running in a **fresh, adversarial context** that sees the spec draft + affected code but **not** the orchestrator's design reasoning — the established blind-reviewer guarantee (`spec-verifier`/`stub-reviewer`). The orchestrator owns the write path. Degrades to an in-context convention on Codex.
- **Performance invariant:** the pass is **single-shot, static, read-only** — one dispatch, no iteration cycles, no execution. "Fast static analysis" is a hard property, not a tuning goal.
- **Data classification:** two orthogonal axes — a four-level sensitivity tier (`public | internal | confidential | restricted`) **plus** an orthogonal **`regulated/PII` flag**. The tier drives security controls; the PII flag gates the privacy prompt.
- **Privacy:** a **hybrid** — for PII-flagged boundaries, a short prompt over the four DFD-assessable LINDDUN-GO categories (Linking, Identifying, Data Disclosure, **Unawareness**); Non-compliance via the compliance check; Detectability out of scope at design time.
- **Trigger (reusing the existing routing vocabulary):** `data_classification` becomes a **forced-escalation category** with a `standard` floor. R3.3 runs when tier is `architecture`, **or** any forced-escalation floor fired (security or data_classification), **or** the orchestrator conservatively judges a new/crossed trust boundary. `standard`-by-size and `trivial` skip it.
- **Output contract:** material mitigations → **acceptance criteria** (existing `ade-intent` format) → Phase-4 abuse-case tests → Phase-6 lens confirms (no new phase); trust-boundary decisions → **ADRs**; **accepted residual risks** (lightweight four-field record) → surfaced at the ready-for-development gate, never silently dropped; a newly-discovered boundary may **escalate routing**.

## Consequences

- ADE gains a design-time security **and** privacy analysis the field almost universally lacks, feeding mitigations into the same author-separated TDD and review machinery rather than a new gate — the "mitigate-or-explicitly-accept" discipline mirrors the provenance Assumptions section.
- The pass is **lightweight by construction**: conditional (most tasks pay zero), single static read-only dispatch, bounded to ~1–3 boundaries, no loops, no execution.
- **Caveat — classification taxonomy is a design choice, not research-grounded.** The deep-research pass could not verify any primary-source data-classification taxonomy (NIST/ISO/4-tier all failed verification). The 4-tier-plus-flag scheme is chosen deliberately and kept revisable in `CONTEXT.md`.
- **Caveat — single-case privacy evidence.** LINDDUN GO's design-phase efficacy (completeness/Unawareness gain; Detectability/Non-compliance not DFD-assessable) rests on one peer-reviewed case study — directionally strong, not multi-case generalised.
- **Rejected alternatives:** a full per-element DFD/STRIDE enumeration (too heavy for per-change); a 5-tier scheme that conflated sensitivity with the regulatory marker (replaced by 4-tier + orthogonal flag); aligning to a named external standard (heavier, unverifiable here); the full 33-card LINDDUN GO workshop (multi-hour, group method); a machine-checkable tool-driven model — pytm/Threat Dragon/Threagile (deferred; no surviving research either way); and extending the Phase-6 `security-reviewer` instead (it stays code-level and downstream — the gap is design-time).
- The method and its terms are recorded in `CONTEXT.md`; the framework grounding is in `docs/research/threat-modeling-frameworks-2026-06.md`.
