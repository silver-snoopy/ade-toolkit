# Design — Design-time threat modeling (trust-boundary STRIDE-lite + data classification)

**Date:** 2026-06-24
**Status:** Approved (grilled 2026-06-26; pre-implementation)
**Scope:** ADE toolkit (`src/ade/`) — addresses highest-priority fix #5 of `docs/ade-sdlc-adversarial-review-suggestions-2026-06.md` ("Add design-time threat modeling and data classification … Feed mitigations back into acceptance criteria and tests"). Targets the field-study tail where ADE can leapfrog: **0/17** systems do design-time privacy/PII analysis and only **3/17** do design-time STRIDE threat modeling.
**Depends on:** the Phase-1 research pipeline (R2 scouts, R3 synthesize/interview, R4 grill, R5 CoVe) and the routing classifier (`.ade/ade-routing.json`, the G4 deterministic-rules-plus-judgment pattern) — all shipped.
**Companion docs:** `docs/adr/0005-design-time-threat-modeling.md` (the methodology decision + its external grounding); new glossary terms in the repo `CONTEXT.md`.
**Evidence base:** `docs/research/threat-modeling-frameworks-2026-06.md` — a 2026-06-24 deep-research pass (5 angles, 23 sources, **25/25 verified claims confirmed**, 0 killed) over Shostack's Four-Question Framework, STRIDE, OWASP threat modeling, LINDDUN GO, abuse cases, and OWASP SAMM. The ADR cites its primary sources.

## 1. Context & motivation

ADE's only security analysis today is **code-level and late**: a Phase-6 `security-reviewer` checks the implemented diff against OWASP Top 10 (SQLi, auth bypass, XSS, hardcoded secrets). Nothing examines the **design** for the trust boundaries a change introduces or crosses, the classification of the data flowing across them, or the abuse cases a feature enables — before code exists, while mitigations are still cheap to fold into the spec. Privacy/PII is not analysed at all.

The deep-research pass confirms this is the right gap to close and that a **defensible minimal method already exists**: OWASP's own primary guidance is Shostack's Four-Question spine + a minimal-viable DFD with **trust boundaries** + STRIDE used "for illustration," with mitigations required to be "actionable not hypothetical" and testable. The discipline that keeps it lightweight — and out of security-theater — is **per-change scope**: "threat model every story," analyse only "what we're working on right now," never the whole system (the whole-system variant is called "dangerous").

This design adds one conditional Phase-1 sub-step — **R3.3 — the threat pass** — that runs a fresh-context, adversarial `threat-modeler` worker over the spec's delta, turns each accepted threat into an acceptance criterion or an explicitly-accepted residual risk, and routes trust-boundary decisions to ADRs. It deliberately reuses the proven ADE patterns: the **blind reviewer** structure (`spec-verifier` / `stub-reviewer`), the **deterministic-trigger-plus-judgment** classifier (G4), the **mitigate-or-explicitly-accept** monotonic discipline (provenance's Assumptions section), and the **single-writer orchestrator** owning the spec.

## 2. Goals / non-goals

**Goals**
- Add a conditional **R3.3 — threat pass** sub-step to Phase 1 `ade-research`, between the R3.2 interview and R4 grill — so mitigations become acceptance criteria *before* R4 can challenge them and R5 CoVe verifies them.
- Add a dedicated **`threat-modeler`** worker (sonnet, read-only `[Read, Grep, Glob]`, fresh adversarial context) that sees the **spec draft + affected code but NOT the orchestrator's design reasoning** — the established blind-reviewer guarantee.
- Method: **trust-boundary-anchored STRIDE-lite + data classification**, with the pass **wrapped in Shostack's four questions** as its outer loop (research refinement), scoped strictly to the change's delta (~1–3 boundaries).
- A hard **no-boilerplate guardrail**: every threat must name the real boundary/flow in *this* change and a concrete mitigation, or it is dropped.
- One **unified security + privacy** pass (not two steps). Privacy handled by data classification of cross-boundary data **plus a few LINDDUN-GO-style prompts for the assessable privacy categories** (esp. **Unawareness**, the documented checklist blind spot).
- A **hybrid trigger** mirroring G4, expressed in the existing routing vocabulary: run R3.3 when tier is `architecture`, OR **any forced-escalation floor fired** (the existing security category **or** a new `data_classification` category, both `standard`-floor), OR the orchestrator judges a new/crossed trust boundary or classified-data surface. A change that is `standard` merely *by size* (no escalation) does **not** get a threat pass — no security theater on a rename. `trivial` always skips.
- **Output contract** (what makes this more than another review lens):
  - material **mitigations → acceptance criteria** (existing `ade-intent` format; automatable in-loop, `(manual)` otherwise) → `test-writer` authors **abuse-case tests** in Phase 4; the Phase-6 security lens confirms — **no new verification phase**;
  - **trust-boundary decisions → ADRs**;
  - **accepted residual risks → surfaced at the ready-for-development gate** (the provenance "Assumptions" precedent — mitigate-or-explicitly-accept, never silently dropped);
  - a discovered **new trust boundary may feed routing** (escalate tier).
- Record the working pass to `.ade/tasks/<task-id>/threat-model.md` (ephemeral).
- **Keep it fast: a single-shot, static, read-only pass** — one dispatch, no iteration cycles, no execution. "Fast static analysis" is a hard invariant (§3.1), not a tuning goal.
- New glossary entries in `CONTEXT.md`; degrade to an in-context convention on Codex (no autonomous subagent dispatch).
- All affected tests updated; `ade eval` and the stale-reference guard stay green.

**Non-goals (deferred / out of scope)**
- **No full DFD / per-element STRIDE enumeration** — the unit is the trust boundary the change crosses, not every element.
- **No full LINDDUN GO workshop** — a 2–3 hour group method; ADE borrows the assessable-category prompts only. Detectability (needs runtime detail) and the generic Non-compliance category are not DFD-assessable at spec time; Non-compliance is covered by the classification/regulatory checklist, Detectability is explicitly out of scope at design time.
- **No attack trees, no tool-driven model** (pytm / Threat Dragon / Threagile YAML). The artifact is structured Markdown. (Research produced no surviving claims either way — this is a deliberate weight choice, an open question, not a refuted option.)
- **No new verification phase or runtime gate** — mitigations ride the existing Phase-4 TDD and Phase-6 security lens.
- **No `detect.py` / `cli.py` logic changes** — this is worker + skill template content + routing JSON + glossary + ADR + tests. (`threat-modeler.md.j2` auto-emits to all four harnesses via the existing agent loop; only doc worker-counts change.)
- **No second `security-reviewer` change** — Phase 6 stays code-level; R3.3 is design-level and upstream.

## 3. Design

### 3.1 The `threat-modeler` worker (`agents/threat-modeler.md.j2`)

Mirrors `spec-verifier` / `stub-reviewer`:

```
---
model: sonnet
tools: [Read, Grep, Glob]
---
```

- **Fresh, adversarial context.** Runs the threat pass over the **spec draft + the affected code paths**, NOT the orchestrator's design reasoning (the blind-reviewer guarantee — its value is catching what the author's own reasoning rationalises away). Read-only: never edits files. If its dispatch prompt accidentally includes the orchestrator's design rationale, it flags that rather than absorbing it.
- **Outer loop = Shostack's four questions**, applied to the change only: *(1) What are we working on (this change's delta)? (2) What can go wrong? (3) What are we going to do about it? (4) Did we cover it?*
- For each trust boundary the change **introduces or crosses** (target ~1–3; if zero genuine boundaries, say so and stop — an empty, honest result beats invented threats):
  - **(a) Data classification** — classify what flows across the boundary (see §3.4).
  - **(b) Threats** — applicable **STRIDE-lite** categories via the fixed threat→property mapping (Spoofing→Authentication, Tampering→Integrity, Repudiation→Non-repudiation, Information Disclosure→Confidentiality, Denial of Service→Availability, Elevation of Privilege→Authorization) **+ abuse cases** (per-feature "how could this be misused") **+**, only when the boundary's data carries the **PII flag** (§3.4), a short **privacy prompt** over the four DFD-assessable LINDDUN-GO categories — **Linking, Identifying, Data Disclosure, Unawareness**. Non-compliance is covered by the compliance line of the data-classification check, not a card; Detectability is out of scope at design time (not DFD-assessable).
  - **(c) Each threat → a concrete mitigation OR an explicit accepted residual risk** — never left dangling.
- **No-boilerplate guardrail (hard rule):** every reported threat must name the **specific boundary/flow in this change** and a **concrete, actionable mitigation**. Generic, change-agnostic threats ("validate all inputs") are dropped. A mitigation must be testable ("can success/failure be measured?").
- **Performance invariant — fast static analysis.** The pass is **single-shot, static, and read-only**: one subagent dispatch, one sweep over the bounded delta, **no iteration cycles** (contrast R2.1's ≤3 scout cycles and R5's N verifiers) and **no execution** (no Bash/build/test/web). Its whole cost is reading the spec draft + the affected paths once. This is a hard design property, not a tuning goal — the pass must never grow a retry loop, a second opinion panel, or a runtime check.
- **Output:** a structured Markdown verdict the orchestrator consumes — per boundary: classification, threats (category + the named flow), and for each a mitigation or a marked residual risk; ending with proposed acceptance criteria, any ADR-worthy boundary decision, and any routing-escalation signal. Written by the orchestrator to `.ade/tasks/<task-id>/threat-model.md`.

### 3.2 The trigger (hybrid; `skills/ade-research/SKILL.md.j2` + `ade-routing.json.j2`)

The trigger is expressed entirely in the existing routing vocabulary (**Forced-escalation**, **Floor**) — no parallel "trigger" concept. `data_classification` becomes a **new forced-escalation category** in `.ade/ade-routing.json` with a **`standard` floor**, exactly like the existing security category: a PII/payment/GDPR change is *at least* `standard`, never `trivial`. Keywords (e.g. `pii`, `gdpr`, `ccpa`, `phi`, `personal data`, `payment`, `card number`, `ssn`, `email address`, `health record`, `biometric`) are consumed by the **Phase-0 routing skill** — note the `check-escalation-paths` commit hook reads only `escalation_globs`, not `keywords`, so this is a routing-skill floor, not a new hook-enforced gate (a deliberate scope match to how the existing `keywords` already behave).

R3.3 then runs when **any** of:
1. tier == `architecture` (always), OR
2. **any forced-escalation floor fired** during Phase-0 routing — the existing security category (auth, secret, crypto, credential, data-loss) **or** the new `data_classification` category. The pass is told *which* category fired, so the privacy/Unawareness prompt (§3.1b) fires specifically on `data_classification` hits, OR
3. the **orchestrator judges** the change introduces/crosses a new trust boundary or a classified-data surface that the deterministic rules missed (the G4 judgment leg). This leg is **conservative by default** — it fires only on a concrete, nameable new boundary, never "run it to be safe"; the cheap, deterministic legs (1–2) carry the common case.

A change that is `standard` merely **by size** (no escalation) does **not** get a threat pass. `trivial` **always skips**. The decision (which trigger fired, or why skipped) is recorded in the phase status file, like the R2.2 web-research decision.

### 3.3 Placement in `ade-research` (R3.3)

New `### R3.3 — Threat pass (conditional)` section in `skills/ade-research/SKILL.md.j2`, inserted **after R3.2** (interview) and **before R4** (grill):

- Gated by §3.2. If it runs: dispatch the `threat-modeler` (passing spec draft + affected paths, withholding design reasoning); the orchestrator folds the verdict into the spec (§3.5) and writes `threat-model.md`.
- Sits before R4 so `grill-with-docs` can challenge the new mitigations/terms, and before R5 so CoVe verifies the threat-derived acceptance criteria like any other claim.
- A canonical short **"Threat-pass method"** block defines the four questions, the STRIDE→property mapping, the classification tiers, and the no-boilerplate rule once, referenced by the rest.

### 3.4 Data classification scheme

**Two orthogonal axes** (grill 2026-06-26): a four-level **sensitivity** tier — **public · internal · confidential · restricted** — plus an independent **`regulated/PII` flag**. They are orthogonal because regulated data is not always the most sensitive: a user's email is `internal` **+ PII**, a signing key is `restricted` but **not** PII. A boundary is labelled with the most-sensitive tier crossing it and the flag if any PII/regulated data crosses.

- The **tier** drives which security controls are mandatory (e.g. `restricted` ⇒ confidentiality at-rest/in-transit + non-repudiation logging; `confidential` ⇒ access control + no plaintext logging).
- The **PII flag** is the precise gate for the privacy prompt (§3.1b) and the compliance/minimisation controls — only PII-flagged boundaries pay that cost.

> **Design choice, not a cited fact (grill 2026-06-26).** The deep-research pass found **no verifiable primary-source taxonomy** for data classification (NIST/ISO/4-tier were asked about; **no claim survived verification**). The 4-tier-plus-flag model is a deliberate design decision, chosen over the original 5-tier (which conflated sensitivity with the regulatory marker) and over aligning to a named external standard (heavier, and unverifiable here). It is recorded in **ADR-0005** and defined in `CONTEXT.md` so it stays revisable.

### 3.5 Output contract — orchestrator write path

The orchestrator (single writer) folds the verdict into the permanent spec:
- **Material mitigations → acceptance criteria** in the existing `ade-intent` format (`- [ ] … `; `(manual)` when not automatable). These flow downstream unchanged: Phase-4 `test-writer` authors abuse-case/negative tests for them (RED→GREEN, author-separated), Phase-6 security lens confirms. No new phase.
- **Trust-boundary decisions → ADRs** (`docs/adr/NNNN-*.md`) when they meet the existing 3-criteria ADR gate (hard-to-reverse, surprising, real trade-off) — e.g. "all PII crosses the service boundary already pseudonymised."
- **Accepted residual risks → a dedicated spec section** surfaced at the ready-for-development gate (the provenance "Assumptions" precedent): a non-empty "Accepted residual risks" section is itself a signal that the change carries known, consciously-accepted exposure — never silently dropped. Each record is **lightweight — four fields only: the threat, the named boundary, why it is accepted, and any compensating control.** No `owner`/`expiry` ceremony (grill 2026-06-26): the human at the ready-for-development gate is the implicit owner, and expiry dates rot in a per-task artifact.
- **Routing feedback:** a newly-discovered trust boundary the routing classifier missed may **escalate the tier** (e.g. standard → architecture), recorded as a routing note.

### 3.6 Tiers

`architecture` → R3.3 always runs. `standard` → runs on trigger (§3.2). `trivial` → skipped. Matches the blast-radius right-sizing of the rest of the pipeline.

### 3.7 Glossary (`CONTEXT.md`)

Add a "Security & privacy risk" group: **Trust boundary** (where the level of trust changes as data flows — the unit of the pass), **Threat pass** (the R3.3 *activity*), **Threat model** (the *artifact* at `.ade/tasks/<id>/threat-model.md`), **Data classification** (the four sensitivity tiers + the orthogonal PII flag), **Abuse case** (per-feature misuse), **Mitigation** (an actionable, testable control answering a threat), **Residual risk** (a threat consciously accepted rather than mitigated, surfaced at the gate). Cross-references: _Avoid_ conflating the design-time **threat pass/model** with the Phase-6 code-level **security review**; _Avoid_ using "threat model" for the activity (that is the **threat pass**, mirroring Codify/Compounder and Route/routing.md).

### 3.8 Codex degradation

Codex cannot yet autonomously dispatch subagents (openai/codex#18513). As with the other blind reviewers, on Codex R3.3 runs as an **in-context convention**: the orchestrator runs the four-question threat pass itself against the spec+code, foregoing the fresh-context guarantee. The deterministic trigger (routing keywords/globs) still fires identically — Codex's native hooks are unaffected.

## 4. Files changed

**New**
- `src/ade/templates/agents/threat-modeler.md.j2` — the worker (auto-emits to all four harnesses).
- `docs/adr/0005-design-time-threat-modeling.md` — methodology decision + grounding.

**Modified**
- `src/ade/templates/ade-routing.json.j2` — add the `data_classification` keyword set.
- `src/ade/templates/skills/ade-intent/SKILL.md.j2` — Phase-0 routing: a `data_classification` keyword imposes a **`standard` floor** (like the existing security category), and the routing decision records **which escalation category fired** (security | data_classification) so R3.3 can read it.
- `src/ade/templates/skills/ade-research/SKILL.md.j2` — R3.3 sub-step + trigger (reads the routing decision) + canonical method block + status-file states.
- `src/ade/templates/AGENTS.md.j2` — one R3.3 line under Phase 1.
- `docs/ade-architecture-design.md` — agent table (+`threat-modeler` row), R3.3 in the Phase-1 detail, worker count 13→14.
- `CLAUDE.md` — Phase-1 "at a glance" (R3.3) + worker count.

**Already written during the grill (commit with the docs task):**
- `CONTEXT.md` — the "Security & privacy risk" glossary group.
- `docs/adr/0005-design-time-threat-modeling.md` — the methodology ADR.
- `docs/research/threat-modeling-frameworks-2026-06.md` — the evidence base.

**Tests**
- `tests/test_cli.py` — assertions on the generated tree (see §6).

## 5. Design questions — resolved at grill (2026-06-26)

1. **Trigger vocabulary** — *resolved:* `data_classification` is a **forced-escalation category** (`standard` floor), not a parallel "trigger" concept; R3.3 fires on architecture / any forced-escalation / conservative judgment (§3.2). Reuses the existing Forced-escalation + Floor terms.
2. **Term split** — *resolved:* **Threat pass** = the R3.3 activity; **Threat model** = the artifact; `threat-modeler` = the worker (§3.7, mirrors Codify/Compounder).
3. **Classification taxonomy (§3.4)** — *resolved:* **4 sensitivity tiers + orthogonal PII flag**, chosen over the original 5-tier and over a named external standard. Research-unsupported → recorded in **ADR-0005**.
4. **Privacy weight** — *resolved:* **hybrid** — four DFD-assessable LINDDUN-GO prompts (Linking, Identifying, Data Disclosure, Unawareness), gated by the PII flag; Non-compliance via the compliance line; Detectability out of scope.
5. **Residual-risk record** — *resolved:* **lightweight four-field record** (threat, boundary, why accepted, compensating control); no owner/expiry.
6. **Performance invariant** — *resolved:* the pass is **single-shot, static, read-only, no-loop, no-execution** (§3.1); "fast static analysis" is a hard property.

**Still deferred (not blocking):**
- **Artifact form** — structured Markdown (chosen) vs a machine-checkable model (Threagile/pytm) later. Research produced no surviving claims on tool-driven modeling.
- **Naming guard** — if implementation renames a tier/term, add a test asserting the rejected token never appears in the generated tree (the provenance `VERIFIED` precedent).

## 6. Test plan (TDD, asserts on the generated tree)

Each via `runner.invoke(app, ["init", ...])` against the `python_project` fixture, then read the generated files and assert substrings:
- `threat-modeler` worker emitted to each harness's workers dir (Claude `.md`, Gemini/Copilot, Codex `.toml`), with `model: sonnet` and read-only tools.
- `ade-routing.json` contains the `data_classification` key and representative keywords (e.g. `pii`, `gdpr`).
- `ade-research` SKILL contains an `R3.3` threat-model section, the trigger, and the no-boilerplate rule.
- `AGENTS.md` Phase-1 references the threat pass.
- Worker-count assertions (if any count is asserted) updated 13→14.
- `ade eval` stays `PASS`; the stale-reference guard (`Playwright`, `docker compose`, `localhost`, `NO EXEMPTIONS`, `/10`, `qa-verify`) stays green — keep all threat examples free of those tokens (use neutral placeholders).
