# Research — Threat-modeling & privacy-analysis frameworks (lightweight, per-change)

**Date:** 2026-06-24
**Method:** Deep-research pass — 5 search angles, 23 sources fetched, 109 claims extracted, **top 25 adversarially verified (3-vote), 25/25 confirmed, 0 killed**. Grounds the design-time threat-modeling feature (R3.3) and ADR-0005.
**Question:** What established, *lightweight* threat-modeling and privacy frameworks should a fast agentic SDLC borrow for a per-change, design-time "threat pass"? For each: what it analyzes, its unit, its output, its weight — then four ADE design answers.

## Executive summary

The strongest evidence-backed minimal method is **Shostack's Four-Question Framework** (*What are we working on? / What can go wrong? / What are we going to do about it? / Did we do a good enough job?*) as the process spine, anchored on a **minimal-viable Data Flow Diagram with trust boundaries**, with **STRIDE used as the lightweight "what can go wrong" prompt** mapped deterministically to six security-control properties. OWASP's own primary threat-modeling guidance is *structurally identical* (Four-Question spine + STRIDE-for-illustration + simple-symbol DFDs that whiteboarding can satisfy), so **"trust-boundary-anchored STRIDE-lite + data classification" is defensible and primary-source-aligned** — STRIDE is explicitly one of several interchangeable methods, not mandatory. The single refinement worth making over the approved design is to **wrap the STRIDE-lite pass in the four questions** and **scope it strictly per-change**.

For privacy, **LINDDUN GO** is a proven, bounded lite/card form (33 cards over 7 categories; no mapping table or threat-tree catalog) with peer-reviewed evidence it adds **completeness** a control checklist misses — notably **Unawareness** threats. But two of its seven categories (**Detectability, Non-compliance**) are not assessable from a design-phase DFD alone, so a **hybrid** (LINDDUN-GO prompts for the assessable categories + a data-classification/compliance checklist for Non-compliance) is the right weight; full LINDDUN GO (a 2–3 hour group workshop) is too heavy for a per-change pass.

The anti-boilerplate discipline is **per-story incremental scope** ("threat model every story," analyse only the change in front of you). The proven way to turn threats into requirements is OWASP's mandate that **mitigations be actionable and testable**, with abuse cases becoming **User-Story acceptance criteria**; explicitly-accepted residual risk is recorded as a **first-class decision** (an ADR in ADE).

## Frameworks surveyed

### Shostack's Four-Question Framework — the process spine

- **What it analyses / unit / output / weight:** the *work in front of you*; unit = the current change; output = a shared answer to four questions; weight = minimal (can be done with no diagram and no STRIDE knowledge).
- The framework "is made up of these four specific questions" and "organizes most modern work in threat modeling"; rephrasings "often lose nuance, flexibility, or both." It is deliberately accessible — phrasing risk as "*What can go wrong?*" "expand[s] the space of answers, increase[s] participation, and reduce[s] debates over terminology." Minimal form is explicitly sanctioned: "threat modeling can be as simple as asking the Four Questions, and that's way better than no threat modeling at all." [1]
- **Per-change scope is load-bearing.** "*What are we working on?* can easily be extended to *What are we working on right now?* This aligns well with agile development and … Izar Tarandach, *Threat model every story*. When we innocently vary the question to *What are we building?* we move towards a waterfall view and the **dangerous implication that we have to analyze the whole of what we're building, rather than the part that we're working on right now**." [1]

### STRIDE (Microsoft) — the "what can go wrong" prompt

- **What / unit / output / weight:** elicits threats by category against DFD elements/boundaries; unit = an element or boundary; output = candidate threats tagged by category; weight = light when used as a checklist prompt (heavier as full per-element/per-interaction enumeration).
- **Deterministic threat→control mapping** is what makes it productive rather than open-ended brainstorming: Spoofing→Authentication(Authenticity), Tampering→Integrity, Repudiation→Non-repudiation, Information Disclosure→Confidentiality, Denial of Service→Availability, Elevation/Expansion of Authority→Authorization. [1][2] The property is a **control objective**, not a single prescribed implementation.

### Trust boundaries & minimal-viable DFD

- The minimal DFD vocabulary is a small fixed symbol set — external entity, process, multiple process, data store, data flow, and **trust/privilege boundary**. "Technical tools are not strictly necessary; whiteboarding may be sufficient." [3]
- The **trust boundary is the highest-yield structuring device**: "The privilege boundary (or trust boundary) shape is used to represent the change of trust levels as the data flows through the application"; "Boundaries show any location where the level of trust changes" [2] — which is exactly where controls (authN, authZ, input validation) belong. Anchoring a per-change pass on the trust boundaries the change crosses is the lowest-effort, highest-signal move.

### OWASP threat modeling — independent validation of the approved shape

- OWASP's primary guidance anchors on the Manifesto's four questions and decomposes into four steps mirroring them: **(1) Scope your work, (2) Determine Threats, (3) Determine Countermeasures and Mitigation, (4) Assess your work.** [2] "For illustration purposes, this cheatsheet will leverage STRIDE; however, in practice, other approaches may be used alongside or instead of STRIDE" (lists LINDDUN/PASTA/OCTAVE/VAST) and "There is no universally accepted industry standard." [3] → a STRIDE-lite anchor is OWASP-consistent but not the only sanctioned method.

### LINDDUN GO — lightweight privacy threat modeling

- **What / unit / output / weight:** privacy threats by category against a DFD; unit = a DFD element/hotspot × a threat card; output = elicited privacy threats + countermeasures; weight = medium — a card game, but a **2–3 hour group workshop** in full form.
- A fixed deck of **33 threat cards** (35 in the original 2020 paper) over **7 categories** (Linking, Identifying, Non-repudiation, Detecting, Data Disclosure, Unawareness, Non-compliance) plus system "hotspots." It deliberately removes full-LINDDUN's heavyweight steps: "there's no need to consult a mapping table or threat tree catalog," lowering the privacy expertise needed to start. [4][5][6]
- **Demonstrated value over a bare checklist = completeness.** A peer-reviewed design-phase case study found GO "able to identify not only a built-in privacy deficiency but also unforeseen privacy threats … especially in the **Unawareness** category" — threats a data-classification/control checklist would not prompt. [5]
- **But partial at design weight.** "Detectability was not assessable since it required detailed information that was not contained in our data flow graph in the design phase. … non-compliance was treated too generically; its intention is more to complete the list of important topics." [5] → use GO prompts for the assessable categories; cover Non-compliance via a classification/regulatory checklist; accept Detectability is not answerable at spec time.

### Abuse cases & misuse cases — per-feature "how could this be misused"

- **Unit = the feature/business function.** An abuse case is "a way to use a feature that was not expected by the implementer, allowing an attacker to influence the feature or outcome … based on the attacker action (or input)," defined "for a feature (that can be mapped to a user story in agile projects)." [7]
- OWASP candidly flags the *full* abuse-case framework as heavyweight: "in practice the abuse case framework seems heavyweight and there are few published examples or success stories," and offers only "a pragmatic approach" getting-started subset. [7] → borrow the framing (per-feature misuse prompt), not the full methodology.

### Mitigations → testable requirements; staged via SAMM

- "Mitigation strategies must be actionable not hypothetical"; testability is itself validated: "Can the agreed upon mitigations be tested? Can success or failure … be measured?" [3] Selected abuse cases "must become security requirements … or **User Story acceptance criteria** (agile)." [7]
- A graduated model is available via **OWASP SAMM** Misuse/Abuse Testing maturity: L1 fuzzing → L2 misuse/abuse cases → L3 DoS/stress — useful to *stage* which threats become tests first. [8]

## Design answers for ADE

1. **Is "trust-boundary-anchored STRIDE-lite + data classification" defensible, or is there a more-proven lite shape?** Defensible — it is structurally identical to OWASP's own guidance (Four-Question spine + minimal DFD/trust boundaries + STRIDE-for-illustration), and **no more-proven lighter shape exists**. The only refinement worth making is to wrap it in **Shostack's four questions** and scope it **per-change**. [1][2][3]
2. **Privacy: is LINDDUN GO worth it, or does data-classification + a control checklist suffice?** A **hybrid** is correct. LINDDUN GO earns its place for the *assessable* categories — peer-reviewed completeness gain, especially **Unawareness**, which a checklist misses — but it does **not** fully replace a data-classification/compliance checklist, because Detectability and Non-compliance aren't DFD-assessable at design time. Use a handful of GO-style privacy prompts inside the unified pass; keep the classification tiers for Non-compliance. [4][5]
3. **How to keep a per-change pass from degenerating into boilerplate?** Per-story scope — "threat model every story," analyse only the current change, **never the whole system** — anchored on the specific trust boundaries the change crosses. Every threat must name a real boundary/flow in *this* change. [1][2]
4. **Turning threats into testable requirements + accepted residual risk?** Each accepted threat becomes an **actionable, testable acceptance criterion** (mitigation must be measurable), optionally staged via SAMM maturity; abuse cases map to **User-Story acceptance criteria**. Explicitly-accepted residual risk is recorded as a **first-class decision** — in ADE, an **ADR** (and surfaced at the ready-for-development gate). [3][7][8]

## Caveats carried from the research

- **Data-classification *taxonomies* are unsupported here.** The question asked about NIST / ISO 27001 / common 4-tier (public/internal/confidential/restricted; PII/regulated) schemes and their tier→control mapping, but **no claim on classification taxonomies survived verification**. ADE's tier scheme is therefore a **defensible design choice, not research-grounded** — treat the specific tier names and their control mapping as a design/grill decision, not a cited fact. (See open questions.)
- **Tool-assisted / code-driven modeling is unsupported here.** Attack trees, OWASP pytm / Threat Dragon, and Threagile were named in the question but produced **no surviving claims** — this report cannot say when attack trees are worth it or whether a YAML/code artifact beats prose. ADE's choice of a structured-Markdown threat-pass artifact is thus a deliberate weight decision, not a refuted alternative.
- **Single-case privacy evidence.** The design-phase efficacy findings (completeness, Unawareness, Detectability/Non-compliance gaps) rest on **one** peer-reviewed case study (intelligent EV-charging) — directionally strong, not multi-case generalised.
- **Minor:** LINDDUN GO's card count is 35 (2020 paper) vs 33 (current deck); the OWASP Threat Modeling Process page is now tagged "(Historical)" but remains the authoritative source for the DFD symbol set and four-step decomposition; the "several-hours/group-workshop" framing of GO carried the only non-unanimous verifier split (2-1), so its time/headcount specifics are weaker than the rest; STRIDE's threat→control "mapping" is a control objective, not a prescribed implementation; Shostack's "don't rephrase the questions" is a strong preference, not an absolute.

## Open questions (not blocking the current design)

- **Data-classification scheme:** which concrete taxonomy should ADE seed (NIST SP 800-60 / FIPS 199 impact levels, ISO 27001, or the common 4-tier), and what is the primary-sourced tier→control mapping (esp. PII/regulated)? No surviving claim covered this — resolve at grill/ADR time.
- **Attack trees:** at what change complexity do they become worth their cost versus STRIDE-lite? Unanswered.
- **Artifact form:** should the `threat-modeler` emit a machine-checkable YAML/code model (Threagile/pytm style) or is structured Markdown sufficient at this weight? No claims survived on the tool-driven options.
- **Residual-risk record fields:** is an ADR the best vehicle for accepted residual risk, and is there a primary source (ISO 27005 / NIST RMF risk-acceptance) prescribing required fields (owner, expiry, compensating control)? No source mandated the ADR mechanism specifically.

## Sources (primary unless noted)

| # | Source | Quality | Anchors |
|---|---|---|---|
| 1 | Shostack, *The Four-Question Framework* (white paper) — shostack.org/files/papers/The_Four_Question_Framework.pdf; shostack.org/resources/threat-modeling | primary | Four questions; per-change scope; STRIDE→property mapping |
| 2 | OWASP *Threat Modeling Process* (community) — owasp.org/www-community/Threat_Modeling_Process | primary (historical) | 4-step decomposition; DFD symbols; trust-boundary definition; STRIDE control list |
| 3 | OWASP *Threat Modeling Cheat Sheet* — cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html | primary | Four-question spine; STRIDE-for-illustration; minimal DFD; testable mitigations |
| 4 | Wuyts et al., *LINDDUN GO: A Lightweight Approach to Privacy Threat Modeling*, IEEE EuroS&PW 2020 — ieeexplore.ieee.org/document/9229757 | primary | 33/35 cards; 7 categories; no mapping table/threat tree |
| 5 | SciTePress 2025 design-phase LINDDUN GO case study — scitepress.org/Papers/2025/131630/131630.pdf | primary | Completeness/Unawareness gain; Detectability/Non-compliance not DFD-assessable |
| 6 | LINDDUN GO — linddun.org/go | primary | Deck composition; getting-started/scheduling |
| 7 | OWASP *Abuse Case Cheat Sheet* — cheatsheetseries.owasp.org/cheatsheets/Abuse_Case_Cheat_Sheet.html | primary | Abuse-case definition; → user-story acceptance criteria; heavyweight caveat |
| 8 | OWASP SAMM, Requirements-Driven Testing Stream B — owaspsamm.org/model/verification/requirements-driven-testing/stream-b | primary | Misuse/abuse testing maturity L1→L3 |

_Verification: 25/25 verified claims confirmed by 3-vote adversarial check (one privacy time/headcount claim 2-1). Full raw bundle was produced by the `deep-research` workflow on 2026-06-24 (105 agents, ~2.6M tokens)._
