# 4. Two-axis research provenance grading

Date: 2026-06-23

## Status

Accepted

## Context

ADE's research phase (Phase 1) produces a spec from internal code-scout findings and web-research findings. Previously, a fact from an unconfirmed blog, a first-hand code read, and a pure inference all looked identical once they landed in the draft spec; only an ad-hoc `[unverified]` marker existed. The adversarial review (`docs/ade-sdlc-adversarial-review-suggestions-2026-06.md`, cleanup #4) flagged that `ASSUMED` claims could silently lock as spec facts.

A deep-research survey (`docs/research/provenance-and-evidence-grading-frameworks-2026-06.md`, 24/25 claims adversarially verified) found that separating **source reliability** from **claim credibility** is a doctrine-level standard: NATO's Admiralty Code (STANAG 2511) mandates the two be judged independently, GRADE mirrors it (evidence certainty vs. recommendation strength), and W3C PROV confirms that provenance models deliberately carry no grading of their own.

## Decision

Grade research on two orthogonal axes:

- **`trust`** (existing) — the SOURCE axis: `high | medium | low`. ≈ Admiralty reliability A–F. Also the prompt-injection signal.
- **`provenance`** (new) — the CLAIM axis: `CONFIRMED | CITED | ASSUMED`. ≈ Admiralty credibility 1–6.
  - **CONFIRMED** — first-hand observed or corroborated by ≥2 independent sources (Admiralty credibility-1, "confirmed by other sources"). Named `CONFIRMED`, **not** `VERIFIED`, to avoid colliding with the R5 Verify (Chain-of-Verification) phase.
  - **CITED** — exactly one source that *actually supports* the claim (citation that does not support it ⇒ ASSUMED).
  - **ASSUMED** — inference or untraceable.

Two safety rules:

- **Monotonic default** (from in-toto's attestation model): missing/unsupported evidence is `ASSUMED`, never silently a fact.
- **Trust floor** — ADE's one deliberate departure from Admiralty's strict axis-independence: a `trust: low` source cannot, on its own, lift a claim above `ASSUMED`. This blocks injection-laundering of untrusted web content into locked spec facts. The axes are still recorded independently; only the *promotion* rule treats trust as a floor.

Material `ASSUMED` claims (and source conflicts) route into the R3 interview, prioritized within the existing 5-question cap; unresolved ones stay labeled in the spec's "Assumptions" section. R5 CoVe prioritizes `CITED`/`ASSUMED` claims.

## Consequences

- Research evidence is auditable: each claim shows how it is known, separate from how trustworthy its source is. A locked spec with a non-empty Assumptions section is a visible signal at the ready-for-development gate that research left gaps.
- Caveat (Irwin & Mandel 2019): rigid scales can create a false impression of objectivity, and analysts collapse the two "independent" axes onto a diagonal in practice. Mitigated by exactly three crisply-defined levels, grades revisable as evidence accrues, and no over-claimed precision.
- **Rejected alternative:** a trust-only single axis (simpler, but cannot distinguish a first-hand code read from an inference attributed to a high-trust source).
- The two-axis model and its terms are recorded in `CONTEXT.md`; the framework grounding is in `docs/research/provenance-and-evidence-grading-frameworks-2026-06.md`.
