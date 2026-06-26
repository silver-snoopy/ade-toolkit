# ADE SDLC Flow — Adversarial Review Suggestions

Date: 2026-06-21

This memo captures the concrete suggestions from an adversarial review of
`docs/ade-dev-pipeline-study-2026-06.html`. The study is directionally strong,
but some claims need narrower wording and several controls should be upgraded
before ADE can credibly present the flow as best-practice rooted.

## Highest-priority fixes

1. **Restore live runtime verification as a first-class gate.**
   Phase 6 currently states that acceptance coverage by tests replaces live
   evidence. Add stack-neutral `run` / `serve` / `verify` slots to
   `.ade/ade-stack.md`, and require per-criterion evidence for every
   non-manual acceptance criterion where a runnable check is feasible. Keep the
   Acceptance-Coverage Gate as a durable complement, not a substitute.

2. **Extend independent plan validation to the `standard` tier.**
   Architecture-tier full refutation is appropriate, but the median change
   should still get a lightweight fresh-context coverage matrix:
   acceptance criterion -> implementation task -> test plan. This preserves
   blast-radius right-sizing without dropping independent validation to zero.

3. **Add a blind Design Check reviewer.**
   Stubs currently compile/import and are self-checked against the plan. Add a
   read-only `stub-reviewer` that sees the spec, plan, and stubs, but not the
   stub author's reasoning, and rejects wrong-but-compiling contracts.

4. **Force falsifiable NFR and capacity decisions.**
   The R3 taxonomy includes non-functional attributes, but it does not force a
   number or an explicit "not constrained" decision. Require concrete targets
   such as p95/p99 latency, throughput, concurrency, data volume, availability,
   memory, or startup budget when relevant.

5. **Add design-time threat modeling and data classification.**
   Phase 6 security review is code-level. Add an earlier threat-surface step for
   auth, trust boundaries, secrets, external inputs, data classification, and
   abuse cases. Feed mitigations back into acceptance criteria and tests.

## Small but important cleanups

1. **Fix the Phase 4 checklist contradiction.**
   `ade-implement` tells implementers not to edit tests, but the checklist says
   "Write unit tests alongside the implementation." Replace that checklist item
   with "Make the pre-written failing tests pass; do not author or edit tests."

2. **Document the scope of deterministic hooks.**
   `check-escalation-paths` is scoped to ADE-routed `ade/<task-id>` branches.
   That is a valid boundary, but the docs should make clear that it does not
   protect direct-to-main or non-ADE branch workflows unless wired as a broader
   repository policy.

3. **Add no-progress detection to bounded loops.**
   The fixed retry caps are good, but add failure fingerprints or issue-count
   deltas so repeated identical failures stop early instead of burning all
   attempts.

4. **Grade research provenance.**
   Scout/web findings should be tagged as `VERIFIED`, `CITED`, or `ASSUMED`.
   `ASSUMED` claims should be routed into the R3 user interview before becoming
   locked spec facts.

5. **Use cross-model review selectively.**
   Cross-family review is not necessary everywhere. Start with the security lens
   and high-blast-radius plans, where correlated model blind spots are most
   expensive.

## Claims to narrow in the study

1. **Avoid "all tiers" for Phase 1 blind verification.**
   The driver states that `trivial` tasks use a lightweight scout and skip
   grill/CoVe. Phrase the strength as applying to `standard` and `architecture`
   tiers.

2. **Avoid unqualified "structural guarantee" across all harnesses.**
   Codex is documented as a degraded tier for autonomous subagent dispatch, so
   author separation and blind verification are structural only on harnesses
   with real independent subagent contexts. Hooks still enforce the hard commit
   gates.

3. **Treat field-leader and "only system" claims as confidence-rated.**
   The current study relies on prior internal agent research for many market
   comparisons. Keep the claims when useful, but attach evidence levels:
   primary-source verified, secondary/internal verified, or inference.

4. **Separate "best in ADE" from "best in field."**
   ADE's design is genuinely strong on spec-blind verification, author-separated
   TDD, and deterministic hooks. The study should still avoid turning internal
   strengths into absolute market claims unless the competitor evidence is
   reproducible.

## Suggested next study shape

The next market study should score ADE and competitors against a best-practice
framework, not just against each other. Recommended dimensions:

- Intent capture and blast-radius routing
- Research grounding and provenance
- Independent specification verification
- Plan validation and requirements coverage
- Design-time security, privacy, and NFR forcing
- Executable contract/design validation
- Author-separated TDD and test quality
- Deterministic gates and hook enforcement
- Quality gate repair loops with stall detection
- Runtime/live verification evidence
- Review diversity and calibration
- Documentation, learning, and post-task compounding

The final output should explicitly mark confidence per competitor and cite
primary sources wherever possible.
