# Research — Provenance & evidence-grading frameworks

**Date:** 2026-06-22
**Purpose:** Survey well-established frameworks for (a) tracing claims back to their evidence (provenance/traceability) and (b) grading the credibility of evidence and reliability of sources — to ground ADE's research-provenance design (see `docs/superpowers/specs/2026-06-22-research-provenance-grading-design.md` and `docs/adr/0004-two-axis-research-provenance.md`).
**How produced:** ADE deep-research harness — 5 search angles → 25 sources fetched → 115 falsifiable claims extracted → top 25 claims put through 3-vote adversarial verification (a claim survives only if it is *not* refuted 2-of-3). **24 of 25 claims confirmed; 1 refuted.** Confidence labels below are the harness's, carried with their primary sources. This document is itself, by ADE's own scheme, a `VERIFIED` artifact (corroborated, primary-sourced).

---

## Executive summary

Separating **source reliability** from **claim credibility** into two orthogonal axes is a proven, decades-old pattern — it is the explicit core of NATO's Admiralty Code (STANAG 2511), which *mandates* the two be judged independently, and it is structurally echoed by GRADE. Provenance data models (W3C PROV) confirm the architecture from the other side: they record lineage but carry **no grading of their own**, so attribution and grading are deliberately separate, complementary layers. The supply-chain world (in-toto/SLSA) contributes two transferable safety rules: a **monotonic default** (missing/ignored evidence never upgrades a decision) and the **verifier-assertion** pattern (a confirmed judgment is reusable downstream without re-deriving). RAG attribution research (Trust-Score) restates the same principle in LLM terms: **abstain when evidence is insufficient**, and measure whether a citation actually supports its statement. The main warning (Irwin & Mandel 2019): rigid all-purpose scales create false objectivity and collapse onto a diagonal in practice — so keep the vocabulary minimal, well-defined, and revisable.

**Direct answers to the design questions:**

1. **Two axes (source vs claim) — proven?** Yes, at doctrine level (Admiralty/STANAG 2511; mirrored by GRADE; confirmed by PROV's grading-free design).
2. **Minimal proven grade vocabularies?** Admiralty credibility 1–6, GRADE certainty (high/moderate/low/very-low). ADE's 3-level `VERIFIED/CITED/ASSUMED` is a defensible minimal analogue.
3. **Handling "unverified/assumed"?** Default to the lowest grade (in-toto monotonicity); structurally separate the assertion from its provenance so it can't read as fact (nanopublications); abstain (RAG).
4. **Routing low-credibility claims to a human?** Standard practice — intelligence "collector–analyst collaboration + periodic revaluation"; GRADE's human evidence→recommendation judgment; RAG grounded-refusal.

---

## Frameworks surveyed

### Intelligence analysis — NATO Admiralty Code (STANAG 2511 / AJP-2.1)
- **What it grades:** every piece of intelligence on **two independent axes**.
- **Axes/levels:** source **reliability** `A`–`F` (A = completely reliable/tried-and-trusted … E = unreliable, F = cannot be judged); information **credibility** `1`–`6` (1 = confirmed by other sources … 4 = doubtful, 5 = improbable, 6 = truth cannot be judged).
- **Key rule:** "Reliability and credibility, the two aspects of evaluation, must be considered independently of each other."
- **Maps to ADE:** `trust:high/medium/low` ≈ the A–F source axis; `VERIFIED/CITED/ASSUMED` ≈ the 1–6 credibility axis (VERIFIED ≈ 1 "confirmed by other sources"; ASSUMED ≈ 6 "truth cannot be judged").
- **Confidence:** high. Sources: STANAG 2511 reproduced at ETURWG/GMU; Irwin & Mandel 2019; Wikipedia (Admiralty code).

### Evidence-based medicine — GRADE
- **What it grades:** two decoupled elements — **certainty of evidence** and **strength of recommendation**.
- **Levels:** certainty is a 4-level ordinal — `high / moderate / low / very low`. A strong recommendation can issue from low-certainty evidence (explicit decoupling).
- **Claim→evidence link:** **evidence profiles** and **Summary-of-Findings tables** co-locate each finding with its certainty rating and the underlying study data — "claim + grade + evidence in one container."
- **Maps to ADE:** validates a minimal ordinal credibility vocabulary, and the **co-location** pattern (put each spec claim next to its grade and citation).
- **Confidence:** high. Sources: GRADE Working Group; Guyatt et al. BMJ 2008 (PMC2335261); Cochrane Handbook ch.14.

### Evidence-based medicine — Oxford CEBM Levels of Evidence (OCEBM)
- **What it grades:** evidence by **study design only** (systematic reviews/RCTs > cohort > case-control/case reports > mechanism/expert reasoning), per *type* of clinical question.
- **Note:** **single-axis** (source/design rank), no separate claim-credibility axis — a useful counter-example showing ADE's two-axis choice is the deliberate, richer option over trust-only grading.
- **Confidence:** high. Source: CEBM "2011 OCEBM Levels of Evidence."

### Provenance data model — W3C PROV (PROV-DM / PROV-O)
- **What it does:** records **lineage**, not quality. Properties: `wasDerivedFrom`, `wasGeneratedBy`, `wasAttributedTo`, `wasInformedBy`, all under `wasInfluencedBy`.
- **Key finding:** PROV contains **no grading/reliability scoring of its own** — it frames provenance as *input to* a downstream trust judgment. Separate extensions (e.g. PROV-K) exist precisely to add trust.
- **Maps to ADE:** the attribution backbone (claim→source link) is a *separate layer* from the trust×credibility grading — exactly ADE's split.
- **Confidence:** high. Sources: W3C PROV-O, PROV-DM (Recommendations).

### Typed citations — CiTO (Citation Typing Ontology)
- **What it does:** makes claim→evidence links **first-class and typed by reason** — evidentiary (`citesAsEvidence`, `citesAsDataSource`, `citesAsAuthority`) vs rhetorical/stance (`agreesWith`, `disagreesWith`, `supports`, `refutes`, `disputes`), via directional property pairs and a reified `cito:Citation`.
- **Maps to ADE:** a CITED claim could carry a citation *reason*; CiTO's `refutes/disagreesWith` is the formal home for the **conflicting-evidence** case ADE routes to R3 (ADE chose not to add a 4th grade, but this is where one would live if ever needed).
- **Confidence:** high. Sources: SPAR/CiTO spec; Shotton 2010, J. Biomed. Semantics.

### Granular provenance — Nanopublications
- **What it does:** each nanopub separates **assertion** (the claim) from **provenance** (where it came from, via `wasDerivedFrom` + citation) into distinct named RDF graphs, attaching provenance at the **atomic claim level** rather than the document level. ~98.95% use W3C PROV in the provenance position.
- **Maps to ADE:** the principle (not the RDF) — structurally separate an `ASSUMED`/inference claim from a `VERIFIED`/cited one so it cannot be mistaken for fact; bind each claim to its own evidence, not a bibliography blob.
- **Confidence:** high. Source: Kuhn et al., IEEE eScience 2018 (arXiv 1809.06532).

### Software supply chain — in-toto / SLSA
- **What it does:** cryptographic **claim→artifact binding** (in-toto `Statement` subject matched by digest) plus two safety rules:
  - **Monotonic principle:** "ignoring an attestation, or a field within an attestation, will never turn a DENY decision into an ALLOW" — absent/unverified evidence is never silently treated as fact.
  - **Verification Summary Attestation (VSA):** separates a verifier's **assertion** ("artifact meets level N") from the underlying **evidence**, so consumers trust the summary without re-evaluating all provenance.
- **Maps to ADE:** (1) default an unverified/absent claim to its lowest grade (`ASSUMED`) — the monotonic rule; (2) a human-confirmed `VERIFIED` claim is a reusable verifier-assertion downstream phases trust without re-deriving (R5 need not re-litigate it).
- **Caveat:** monotonicity is a **SHOULD-level** policy property, not auto-enforced — ADE must enforce "missing evidence ⇒ lowest grade" itself.
- **Confidence:** high. Sources: in-toto attestation spec v1; SLSA v1.0 Verification Summary.
- **Refuted (do NOT borrow):** SLSA build levels `L1..L3` are **not** a general-purpose claim-credibility vocabulary (1-of-3 vote; killed). Do not use SLSA levels as ADE grade names.

### LLM/RAG attribution — Trust-Score and groundedness
- **What it does:** decomposes RAG trustworthiness into separate measures — **Grounded Refusals** (abstain when evidence is insufficient), **Answer Correctness**, **Citation Recall** (statements supported by their citations) and **Citation Precision** (citation relevance) — i.e. attribution quality is measured, not assumed.
- **Maps to ADE:** a claim with insufficient evidence → `ASSUMED` (or refuse); a `CITED` claim must pass citation-recall — **the cited source must actually support the statement** (this directly drove ADE's "CITED requires real support" decision).
- **Confidence:** high. Source: Song et al., Trust-Score, ICLR 2025 (arXiv 2409.11242). *(Fast-moving area; FActScore (arXiv 2305.14251) and RAGAS were also surveyed — treat specific metric choices as time-sensitive.)*

---

## Caveats carried from the research

1. **GRADE's two elements are a derivation chain** (evidence-certainty → recommendation-strength), whereas ADE's axes are **two attributes of the same claim** — the Admiralty Code is the cleaner precedent for "two attributes of one item."
2. **Rigid grades can mislead.** Irwin & Mandel (2019): all-purpose scales "mask rather than effectively guide subjectivity"; ~87% of ratings collapse onto the A1/B2/C3 diagonal (Baker et al. 1968). **Mitigation:** 3 well-defined levels, grades revisable as evidence accrues, no over-claimed precision.
3. **Monotonicity is a policy, not a mechanism** — ADE enforces "missing evidence ⇒ ASSUMED" in prose, not via a framework.
4. Two Irwin & Mandel copies were verified via abstract/secondary corroboration (publisher returned HTTP 403); abstract confirmed by two search engines.
5. **Grade names are a design choice**, not dictated by any framework. `VERIFIED/CITED/ASSUMED` is defensible; the deliberate refinement is that `CITED` encodes citation *quality* (does the source actually support the claim), not mere presence.

## Open questions (not blocking the current design)

- Should a confirmed `VERIFIED` grade be a reusable verifier-assertion that downstream phases never re-check, and how is it invalidated when the underlying code/source changes (digest-binding analogue)?
- Exact promotion/demotion automation thresholds (e.g. does a 2nd independent source auto-promote `CITED`→`VERIFIED`, or require human confirm?). Intelligence literature recommends "periodic revaluation" but prescribes no automation threshold. ADE currently leaves promotion to synthesizer/CoVe judgment.
- Representation of refuting/conflicting evidence beyond routing to R3 (CiTO `refutes` is the formal home if a 4th grade is ever warranted).

## Sources (primary unless noted)

| # | Source | Quality | Framework |
|---|---|---|---|
| 1 | STANAG 2511 / Admiralty Code — eturwg.c4i.gmu.edu/?q=node/128 | primary | Admiralty |
| 2 | Irwin & Mandel 2019, *Improving Information Evaluation for Intelligence Production* (ResearchGate 328858953) | primary | Admiralty critique |
| 3 | Admiralty code — en.wikipedia.org/wiki/Admiralty_code | secondary | Admiralty |
| 4 | GRADE Working Group — gradeworkinggroup.org | primary | GRADE |
| 5 | Guyatt et al. 2008, BMJ — pmc.ncbi.nlm.nih.gov/articles/PMC2335261 | primary | GRADE |
| 6 | Cochrane Handbook ch.14 — training.cochrane.org/handbook/current/chapter-14 | primary | GRADE |
| 7 | OCEBM 2011 Levels — cebm.ox.ac.uk/resources/levels-of-evidence/ocebm-levels-of-evidence | primary | OCEBM |
| 8 | W3C PROV-O — w3.org/TR/prov-o | primary | PROV |
| 9 | W3C PROV-DM — w3.org/TR/prov-dm | primary | PROV |
| 10 | CiTO spec — sparontologies.github.io/cito/current/cito.html | primary | CiTO |
| 11 | Shotton 2010 — jbiomedsem.biomedcentral.com/articles/10.1186/2041-1480-1-S1-S6 | primary | CiTO |
| 12 | Kuhn et al. 2018, nanopublications — arxiv.org/pdf/1809.06532 | primary | Nanopub |
| 13 | in-toto attestation spec v1 — github.com/in-toto/attestation/tree/main/spec/v1 | primary | in-toto |
| 14 | SLSA v1.0 Verification Summary — slsa.dev/spec/v1.0/verification_summary | primary | SLSA |
| 15 | C2PA 2.4 explainer — spec.c2pa.org/.../2.4/explainer/Explainer.html | primary | C2PA |
| 16 | Trust-Score / Song et al. ICLR 2025 — arxiv.org/pdf/2409.11242 | primary | RAG |
| 17 | FActScore — arxiv.org/abs/2305.14251 | primary | RAG |
| 18 | Self-RAG — arxiv.org/abs/2310.11511 | primary | RAG |
| 19 | Cambridge JDM, source-reliability × info-credibility study | primary | Two-axis |
| 20 | SANS — Admiralty system for CTI | secondary | Two-axis (applied) |

*Full harness output (all 24 confirmed claims with verbatim evidence) was produced 2026-06-22; this document is the curated synthesis.*
