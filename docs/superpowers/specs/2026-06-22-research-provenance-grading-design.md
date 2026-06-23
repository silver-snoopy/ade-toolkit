# Design — Research provenance grading (two-axis claim credibility)

**Date:** 2026-06-22
**Status:** Approved (pre-implementation)
**Scope:** ADE toolkit (`src/ade/`) — addresses small-cleanup #4 of `docs/ade-sdlc-adversarial-review-suggestions-2026-06.md` ("Grade research provenance … `ASSUMED` claims routed into the R3 user interview before becoming locked spec facts").
**Depends on:** the Phase-1 research pipeline (R2 scouts, R2.3 web research, R3 synthesize/interview, R5 CoVe) — all shipped.
**Companion docs:** `docs/adr/0004-two-axis-research-provenance.md` (the methodology decision + its external grounding); new glossary terms in the repo `CONTEXT.md`.
**Evidence base:** `docs/research/provenance-and-evidence-grading-frameworks-2026-06.md` — a 2026-06-22 deep-research pass (5 angles, 25 sources, 24/25 claims confirmed by 3-vote adversarial verification) over NATO Admiralty Code / STANAG 2511, GRADE, OCEBM, W3C PROV, CiTO, nanopublications, in-toto/SLSA, and RAG attribution (Trust-Score). The ADR cites its primary sources.

## 1. Context & motivation

ADE's research phase already carries *two* of the three pieces this needs, but unnamed and uneven:

- **Web findings** (`web-researcher`) attach a source-level `trust: high | medium | low` and require `[n]` citations with verbatim `cited_text`.
- **Scout findings** (internal code) carry `relevance` but **no** provenance signal at all.
- **The synthesizer** preserves citation chains and already has a lone `[unverified]` marker (synthesizer.md.j2:65) for claims it cannot trace — an ad-hoc, single-point version of what this design generalizes.

The gap: a spec fact derived from an unconfirmed blog, a first-hand code read, and a pure inference all *look identical* once they land in the draft spec. The adversarial review flagged that `ASSUMED` claims can silently lock as spec facts. This design makes "how we know each claim" a first-class, graded property and routes the weakest claims to the user before they lock.

**Why two axes.** The deep-research pass found the source-vs-claim separation is not a novel idea but a doctrine-level standard: NATO STANAG 2511 (Admiralty Code) *requires* source reliability (A–F) and information credibility (1–6) to "be considered independently of each other," and GRADE structurally mirrors it (evidence certainty vs. recommendation strength). W3C PROV confirms the architecture from the other side: a provenance/attribution model carries **no grading of its own** — grading is a separate, complementary layer. So ADE keeps source-level `trust` (≈ Admiralty A–F) and adds an orthogonal claim-level `provenance` (≈ Admiralty 1–6).

**The one caveat we design against.** Irwin & Mandel (2019) found rigid all-purpose scales create a false impression of objectivity, and analysts collapse the two "independent" axes onto a diagonal (~87% of ratings at A1/B2/C3, Baker et al. 1968). Mitigations are baked in: **exactly three** crisply-defined levels, grades explicitly **revisable** as evidence accrues, and no over-claimed precision.

## 2. Goals / non-goals

**Goals**
- Add a claim-level `provenance` grade — `VERIFIED | CITED | ASSUMED` — to scout and web-research findings, layered on (not replacing) the existing source-level `trust`.
- Define the three grades crisply and canonically (in the repo glossary + each producing agent).
- Carry per-claim grades through synthesis into the draft spec, co-located with each claim and its citation.
- Enforce a **monotonic default**: any claim that cannot be traced to first-hand observation or a supporting source is `ASSUMED` — absent evidence never defaults to fact.
- Route **material `ASSUMED` claims (and source conflicts) into the R3.2 interview**, prioritized within the existing 5-question cap; a user-confirmed claim becomes `VERIFIED`. Unresolved `ASSUMED` claims remain **labeled** in the spec, never silently promoted.
- Have R5 CoVe target `CITED`/`ASSUMED` claims first.
- Keep grades revisable (synthesizer may promote `CITED`→`VERIFIED` on a second independent corroborating source; CoVe may downgrade).
- All affected tests updated; `ade eval` and the stale-reference guard stay green.

**Non-goals (deferred / out of scope)**
- No RDF / PROV-O / nanopublication serialization — ADE specs are human-readable Markdown; grades are inline tags (`[VERIFIED]` / `[CITED]` / `[ASSUMED]`).
- No fourth grade for refuting/conflicting evidence — conflicts route to R3 as Open Questions (keeps the minimal 3-level ladder; Irwin-Mandel).
- No automated numeric credibility scoring or promotion thresholds — promotion/demotion is synthesizer/CoVe judgment, not a computed metric.
- No change to the source-level `trust` vocabulary or the prompt-injection handling that rides on it.
- No `detect.py` / `cli.py` code changes — this is agent + skill template content + glossary + tests.

## 3. Design

### 3.1 The grade vocabulary (canonical)

A claim's `provenance` answers "how do *we* know this?", independent of how trustworthy the source is:

- **VERIFIED** — first-hand observed **or** corroborated by ≥2 independent sources. For a scout: the agent read the actual file and the code says it. For web: a claim confirmed by two independent sources, or a verbatim quote from a `trust: high` primary source. (≈ Admiralty credibility-1 "confirmed by other sources"; GRADE high; RAG grounded-and-corroborated.)
- **CITED** — exactly one attributed source that **actually supports** the claim, not cross-confirmed. The citation must genuinely back the statement (citation-recall); a citation that does not support it is **not** CITED — it is ASSUMED. (≈ PROV `wasDerivedFrom` + CiTO `citesAsEvidence`; RAG citation-recall.)
- **ASSUMED** — inference, gap-filling, or any claim with no traceable first-hand evidence or supporting source. Generalizes today's `[unverified]`. (≈ Admiralty credibility-6 "truth cannot be judged"; OCEBM bottom; RAG should-refuse.)

**Monotonic rule (in-toto):** when in doubt, a claim is `ASSUMED`. Missing or unconfirmed evidence never upgrades a grade. This is enforced in prose by the synthesizer (§3.4); it is a discipline, not a computed gate.

### 3.2 Scout findings (`agents/scout.md.j2`)

Add a `provenance:` field to each finding in the output schema. A scout reads real files, so its findings are normally `VERIFIED` (the code is the first-hand evidence). When a scout *infers* behavior it did not directly read, or records terminology/externals it does not understand (its Open Questions), those are `ASSUMED`. Scouts effectively never produce `CITED` (they cite the repo itself = first-hand = VERIFIED). The grade definition block is added near the existing relevance-scoring block.

### 3.3 Web-research findings (`agents/web-researcher.md.j2`)

Add a claim-level `provenance:` to each finding, **alongside** the existing per-source `trust:`. Guidance:
- corroborated by ≥2 independent sources, or a verbatim quote from a `trust: high` primary source → `VERIFIED`
- a single source that actually supports the claim → `CITED`
- no fetchable/supporting source, or the agent's own inference → `ASSUMED`
The `trust` axis and prompt-injection handling are unchanged; `provenance` is the second, orthogonal axis.

### 3.4 Synthesis (`agents/synthesizer.md.j2`, Role A / R3.1)

- Carry each claim's `provenance` into the draft, **co-located** with the claim and its citation (not in a separate table). The existing `[unverified]` instruction is replaced by the three-grade tag; `[unverified]` becomes `[ASSUMED]`.
- Apply the **monotonic default**: any claim that cannot be traced to first-hand evidence or a supporting source is tagged `[ASSUMED]`, never stated as a bare fact.
- **Route material `[ASSUMED]` claims into "Open Questions for User"** (the section R3.2 consumes). "Material" = the claim, if wrong, changes architecture, data modeling, testing, UX, operations, or compliance (same materiality bar R3.2 already uses).
- **Conflicting sources** (two sources disagree) also become Open Questions — no new grade.
- May **promote** `CITED`→`VERIFIED` when a second independent source corroborates (revisability).

### 3.5 Interview, verification, spec (`skills/ade-research/SKILL.md.j2`)

- **R2 / R2.3:** note that scouts and web-research tag `provenance`.
- **R3.1:** synthesizer carries grades + routes material ASSUMED/conflicts to Open Questions.
- **R3.2 interview:** material `ASSUMED` claims and source conflicts are **prioritized candidates** within the existing **5-question cap** (they compete with, and generally outrank, ambiguity-taxonomy gaps because an un-grounded fact is higher-risk than an open choice). A claim the user confirms becomes `VERIFIED` and is recorded as a fact; the spec drops the tag. Any `ASSUMED` claim **not** resolved within the cap **stays labeled `[ASSUMED]`** in the spec (an explicit assumption the planner/dev sees), never silently promoted.
- **R5 CoVe:** `spec-verifier` claim extraction **prioritizes `CITED` and `ASSUMED` claims** (the lowest-grounded, highest-payoff), still blind to the spec text. A user-confirmed `VERIFIED` claim is a reusable "verifier assertion" (SLSA VSA analogue) — CoVe need not re-litigate it.
- Add a short canonical **"Provenance grading"** subsection defining the two axes + three grades once, referenced by the rest.

### 3.6 Glossary (`CONTEXT.md`)

Add a "Research provenance" group: **Provenance grade** (the claim-level axis), **VERIFIED / CITED / ASSUMED** (the three values, with the Admiralty mapping noted), and a cross-reference clarifying **trust** (source axis) vs **provenance** (claim axis) — the two-axis model. `_Avoid_`: using "trust" and "provenance" interchangeably.

## 4. Files changed

**Agent templates**
- `agents/scout.md.j2` — `provenance:` field + grade block (VERIFIED/ASSUMED for code reads/inferences).
- `agents/web-researcher.md.j2` — claim-level `provenance:` alongside source `trust:`.
- `agents/synthesizer.md.j2` — carry grades, monotonic default, `[unverified]`→`[ASSUMED]`, route material ASSUMED/conflicts to Open Questions, allow CITED→VERIFIED promotion.

**Skill**
- `skills/ade-research/SKILL.md.j2` — canonical "Provenance grading" subsection; R2/R3.1/R3.2/R5 wiring (prioritize ASSUMED in the 5-question cap; CoVe targets CITED/ASSUMED first).

**Docs**
- `docs/adr/0004-two-axis-research-provenance.md` (NEW) — decision + external grounding (Admiralty/GRADE/PROV/in-toto/RAG), the Irwin-Mandel caveat + mitigations, and the rejected alternative (trust-only single axis). Cites the deep-research primary sources.
- `CONTEXT.md` — Research-provenance glossary group.

## 5. Testing

- `scout` template contains `provenance` + the grade names. (skill/agent content)
- `web-researcher` template contains a claim-level `provenance` distinct from source `trust`. (content)
- `synthesizer` template no longer says `[unverified]`; contains `[ASSUMED]`, the monotonic rule, and the route-to-Open-Questions instruction. (content)
- `ade-research` skill defines the three grades and the ASSUMED→R3 routing + the 5-question prioritization. (content)
- `docs/adr/0004-…` exists and names the two axes.
- `CONTEXT.md` defines Provenance grade + the three values.
- `ade eval` green; the G5 stale-reference grep guard green; full suite green.

## 6. ADR-0004 (summary; full text in `docs/adr/`)

**Decision:** ADE grades research on two orthogonal axes — source-level `trust` (existing) and claim-level `provenance: VERIFIED | CITED | ASSUMED` (new) — and routes material `ASSUMED` claims to the user before they lock as spec facts.

**Context / grounding:** the two-axis separation is doctrine (Admiralty/STANAG 2511) and mirrored by GRADE; provenance models (PROV) deliberately exclude grading, confirming the two are separate layers; the monotonic default (missing evidence ⇒ lowest grade) is in-toto's safety principle; abstain-when-unsupported is RAG best practice (Trust-Score).

**Trade-off / caveat:** rigid scales can mask subjectivity and collapse to a diagonal (Irwin & Mandel 2019). Mitigated by three crisp levels, revisable grades, and no over-claimed precision.

**Rejected alternative:** trust-only single axis (simpler, but cannot distinguish a first-hand code read from an inference attributed to a high-trust source).

## 7. Risks

- **Diagonal-collapse / grade theater** → 3 crisp levels, revisability, ADR records the caveat.
- **Interview-budget pressure** (many ASSUMED claims vs the 5-question cap) → prioritize by materiality; unresolved ASSUMED stays *labeled*, so nothing is silently promoted even when the cap binds.
- **Grade drift across agents** → one canonical definition in `ade-research` + glossary; agents reference it rather than re-defining.

## 8. Migration

Pure ADE-owned regeneration: re-running `ade init` re-emits the updated agents/skill; no user-owned files change. The repo glossary (`CONTEXT.md`) and ADR are repo docs, not seeded artifacts.
