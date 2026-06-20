# ADR 0001 — Hybrid blast-radius routing classifier with an un-removable hook baseline

**Status:** Accepted
**Date:** 2026-06-20
**Context tier:** system-wide (ADE pipeline)

## Context

G4 adds blast-radius routing: a task is classified into a tier (`trivial` / `standard` /
`architecture`) that masks which pipeline phases run. We had to decide *how* the
classification is made and *how* the security-sensitive part of it is guaranteed.

Three reference points:
- **LeRisque** uses a fully **deterministic** Stage-0 router (file-glob + diff-size), no
  LLM judgment, no user override, and handles security only via a later post-PR pass.
- **Field research** (2026-06-20 study, 25/25 claims verified) found: a **hybrid** is best —
  deterministic path rules for routing/forced-escalation (auditable, non-evadable) layered
  with a size/severity signal; LLM-only classification is "non-deterministic and evadable"
  and must not be the sole basis for security; forced-escalation should be category-based,
  deterministic, applied at classification time and overriding size, with **defense in
  depth** (also enforced by a deterministic gate later).
- **ADE specifics:** the router runs at **Phase 0, before any code exists**, so it can only
  classify from the intent's *declared* affected areas — there is no diff to scan. And the
  enforcement hook lives in a *user's* repo where humans also commit by hand.

## Decision

1. **Hybrid classifier.** The orchestrator (an LLM) judges `trivial` vs `standard` *within
   the non-forced band* from the intent; **deterministic rules** decide forced-escalation.
   We do **not** adopt a pure-deterministic router (LeRisque) — ADE has no diff at routing
   time, and the orchestrator already produces the intent signals. We do **not** adopt a
   pure-LLM classifier — security routing must not depend on LLM judgment.

2. **Two-layer forced-escalation (defense in depth).** Phase-0 applies escalation rules
   from `.claude/ade-routing.json` against the *declared* affected areas (best-effort, no
   diff). A new deterministic hook (`check-escalation-paths`) enforces the floor against the
   *actual* diff at Ship time — the load-bearing guarantee.

3. **Un-removable security baseline, scoped to ADE-routed tasks.** The hook ships a
   **hardcoded baseline** of escalation paths (security/auth/secrets/crypto, schema/
   migrations, public-API); `ade-routing.json` may only **extend** it, never shrink it, and
   a missing/malformed config falls back to baseline-only (not fail-open). The hook's
   authority is the **routing contract** — "a task ADE *routed* must not commit
   escalation-path changes below its floor" — keyed off the `ade/<task-id>` branch. Off an
   `ade/*` branch or with no routing record, the hook is a **no-op**: policing a user's own
   hand commits is the user's CI/branch-protection job, not ADE's.

## Consequences

- The security floor is non-evadable **for ADE-routed work** even if the JSON config is
  deleted or corrupted — because the baseline is compiled into the hook.
- ADE never hijacks a user's non-ADE commits, preserving it as a well-behaved scaffolded
  tool in a shared repo.
- The guarantee is honestly *scoped*: ADE is not a repo-wide security gate. A user who
  wants that still needs CI/branch protection.
- Phase-0 routing can mis-classify (LLM judgment, no diff); this is acceptable because the
  Ship-time hook is the deterministic backstop, and the user confirms the tier for
  `architecture`/forced-escalation.

## Alternatives considered

- **Pure-deterministic router (LeRisque):** rejected — no diff exists at ADE's Phase-0
  routing point, so size classification would be guesswork without the orchestrator.
- **Pure-LLM classifier, no hook:** rejected — security routing would be evadable and
  non-deterministic.
- **Repo-wide security hook (block all migration/auth commits):** rejected — it would break
  the user's normal hand commits, violating ADE's "don't touch non-ADE commits" constraint.
