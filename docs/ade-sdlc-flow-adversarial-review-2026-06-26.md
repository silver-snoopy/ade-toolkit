# ADE SDLC Flow - Adversarial Review (2026-06-26)

## Scope

This review stress-tests ADE's intended SDLC flow against the current repository docs and
primary external references. It treats the existing market study,
`docs/ade-dev-pipeline-market-best-practices-2026-06.md`, as an important historical
snapshot, but not as the final source of truth: since that study, ADE has added R3.3
design-time threat modeling, data classification, privacy prompts, a blind stub reviewer,
and broader plan validation.

Local files reviewed:

- `README.md`
- `CONTEXT.md`
- `docs/ade-architecture-design.md`
- `docs/ade-gaps-and-roadmap-2026-06.md`
- `docs/ade-dev-pipeline-market-best-practices-2026-06.md`
- `docs/research/threat-modeling-frameworks-2026-06.md`
- `docs/adr/0005-design-time-threat-modeling.md`

External sources checked are listed in the source appendix.

## Executive Verdict

ADE is credible as a high-rigor, agentic development inner loop from intent through PR.
Its strongest defensible claim is:

> ADE scaffolds a specification-first, author-separated, hook-backed, review-heavy
> development flow with durable cross-task learning.

The claim that should be avoided is:

> ADE is a complete SDLC.

That stronger claim is not yet defensible. Standards and mature field practice include
release, operational verification, incident learning, supply-chain controls, accessibility,
privacy implementation checks, maintenance, and retirement. ADE currently stops at PR plus
retro. Its roadmap recognizes several of these gaps, which is good, but marketing and
architecture language should distinguish "inner development SDLC" from "full software
life cycle."

Most material adversarial finding: the old "Codex is degraded because it lacks subagents"
claim is stale. Current Codex documentation describes explicit subagent workflows and
project-scoped custom agents. ADE's Codex risk is now integration proof, not upstream
platform absence.

## What I Would Keep

1. **Phase-masked 9-phase flow.** The trivial/standard/architecture routing model is a
good answer to the usual SDLC ceremony problem. The system should not force architecture
ceremony onto a copy edit.

2. **Author-separated TDD plus VCS hooks.** Splitting `test-writer` from `implementer`,
then backing that split with a mixed-commit hook, is one of ADE's best structural ideas.
It turns a prompt convention into a checkable boundary.

3. **R5 blind Chain-of-Verification.** Passing a verifier only a claim, not the whole
spec, is an unusually strong guard against self-confirming specification review.

4. **R3.3 threat pass.** The added design-time threat pass materially changes the earlier
market-study score. The old "largest standards-rooting gap" finding is no longer accurate
as written for design-time security and privacy.

5. **Compound loop.** Durable learnings and review calibration are a genuine differentiator.
The idea is risky, but worth keeping with integrity controls.

6. **Harness-native scaffolding rather than an ADE runtime.** Keeping ADE as a generator
reduces lock-in and avoids another runtime layer. The cost is that parity must be tested
per harness rather than assumed.

## Findings

### F1 - "Full SDLC" Is An Overclaim

**Severity:** High

ADE currently covers intent, research, specification, plan, design check, implementation,
quality gate, review, docs, ship/PR, and retro. That is a strong development pipeline, but
it does not cover the full life-cycle surface described by standards such as
ISO/IEC/IEEE 12207 or maturity models such as OWASP SAMM. Those include operation,
maintenance, incident handling, and end-of-life concerns.

**Why it matters:** A buyer or maintainer hearing "SDLC" may expect release governance,
runtime monitoring, incident response, vulnerability management, and retirement workflows.
ADE's current evidence supports "development inner loop through PR," not those broader
claims.

**Recommendation:** Use narrower language:

- "agentic development pipeline"
- "inner development SDLC"
- "intent-to-PR SDLC scaffold"

Only use "full SDLC" after B1/B3-style operational and release controls exist and are
exercised by tests or example transcripts.

### F2 - Removing Live Verification Leaves The Weakest Practical Gap

**Severity:** High

ADE's current glossary says live verification was removed and that the test suite, via the
acceptance-coverage gate, is now the primary automated acceptance mechanism. That is a
safer phrasing, but tests are still not equivalent to runtime evidence. They do not prove
that a web app actually starts, that a migration applies in a real database, that a UI path
is usable, or that a third-party integration works with real credentials or stubs.

Anthropic's Claude Code best-practices material explicitly emphasizes giving agents a way
to verify their work through tests, build, screenshots, and other concrete checks. Case is
also stronger here: its closer path can require manual-tested evidence before PR creation.

**Recommendation:** Restore live evidence as conditional evidence, not as a mandatory full
phase for every task. Add stack slots to `.ade/ade-stack.md`:

- `run`
- `serve`
- `verify`
- `smoke`
- `screenshot`
- `rollback`

For non-runnable libraries, the slot can be empty. For UI/service/database changes, Phase 5
or Phase 8 should require a short evidence record: command, result, artifact path, and
reason if skipped.

### F3 - Codex Degradation Is Stale; Codex Parity Is Now An Integration Risk

**Severity:** High

The repo previously said Codex could not autonomously dispatch subagents and therefore
author-separation and blind verification degraded to convention. Current official Codex
documentation describes explicit subagent workflows, project-scoped custom agents, custom
agent configuration, hook events, `AGENTS.md`, and skills.

**Why it matters:** The stale claim makes ADE look weaker than it needs to, while also
hiding the real risk. The real risk is not "Codex cannot do this"; it is "ADE has not yet
proved its Codex templates, prompts, hooks, and transcripts actually preserve the same
isolation guarantees."

**Recommendation:**

- Add a Codex parity fixture that renders `.codex/agents/*.toml` and validates the expected
  14 worker definitions.
- Add a transcript-level or prompt-level test that phase instructions explicitly spawn
  Codex subagents for `test-writer`, `implementer`, `spec-verifier`, `threat-modeler`, and
  `stub-reviewer`.
- Keep the caveat until ADE has evidence from at least one real Codex run.

### F4 - Security/Privacy Improved At Design Time, But Runtime Controls Are Still Thin

**Severity:** High

R3.3 closes the earlier design-time threat-modeling gap. It does not close implementation
privacy, supply-chain, or runtime security verification. A data boundary can be classified
correctly in a spec and still leak through logs, analytics, traces, exported CSVs, or
third-party SDKs.

**Recommendation:**

- Add a PII-triggered `pii-auditor` in Phase 6 that traces newly classified data into logs,
  analytics, observability, storage, and external calls.
- Add a conditional ASVS-inspired security control checklist for web-facing changes.
- Add supply-chain checks in Phase 5 or Phase 8: vulnerable direct dependencies, disallowed
  licenses, unpinned direct dependencies, and SBOM generation.
- Add an accessibility gate for UI-touching changes using automated checks plus an explicit
  keyboard/focus evidence slot where practical.

### F5 - Single-Model Adversarial Review Creates Correlated Blind Spots

**Severity:** Medium-High

ADE separates roles, but many adversarial roles still use the same model family: the
`threat-modeler`, `plan-reviewer`, `spec-verifier`, and fallback security/code reviewers
are Sonnet. This reduces context contamination, but not model-family correlation. The
roadmap already identifies cross-model review as a gap; external peer systems such as
gstack and compound-style flows show that cross-model review is a real field pattern.

**Recommendation:** Do not make every role cross-model. Use selective cross-model review
where correlated misses are most expensive:

- architecture-tier plan refutation
- R3.3 threat pass
- Phase 6 security lens
- large public API or data migration changes

### F6 - Repair Loops Have Caps But Not No-Progress Detection

**Severity:** Medium-High

ADE has hard loop caps, which is good. But a cap alone waits until failure is expensive.
Case's deterministic loop machinery is stronger because it can detect repeated failure
fingerprints and stop earlier.

**Recommendation:** Record a loop fingerprint for each retry:

- failing command or review finding class
- normalized error text hash
- changed file count
- test count delta
- finding count delta

If the same fingerprint repeats twice with no material diff improvement, escalate early
instead of consuming the remaining loop budget.

### F7 - The Compound Loop Is Also A Memory-Poisoning Boundary

**Severity:** Medium-High

The compound loop is one of ADE's best ideas and one of its most ADE-specific risks. A bad
learning, poisoned `CONTEXT.md` term, or injected research note can influence every future
task because Phase 1 reads the material back by design.

**Recommendation:** Treat `docs/learnings/`, `docs/review-calibration.md`, and `CONTEXT.md`
as trust boundaries. Apply the existing provenance concepts to learning ingestion:

- source of the learning
- task that produced it
- evidence link
- whether it is observed, cited, or inferred
- whether it should be allowed to influence future specs automatically

### F8 - Traceability Is Present In Pieces, But Not As An Exported Evidence Pack

**Severity:** Medium

ADE has specs, ADRs, threat models, tests, reviews, retro, and learnings, but there is no
single trace manifest tying requirement -> decision -> task -> test -> review -> PR ->
runtime evidence. Without this, market claims and audit claims are hard to reproduce.

**Recommendation:** Emit `.ade/tasks/<id>/trace.json` and optionally copy a stable summary
to `docs/specs/` or `docs/learnings/` before task cleanup. Minimum fields:

- spec path and acceptance criteria IDs
- ADR IDs
- threat IDs and mitigation IDs
- tests added or changed
- quality-gate commands and results
- review findings and dispositions
- PR link
- runtime evidence artifacts, if any

### F9 - Hook Guarantees Are Session-Scoped, Not Repository-Wide

**Severity:** Medium

The architecture doc correctly states that PreToolUse hooks gate commits made through an
ADE-wired agent session, not every commit that reaches the repository. README language
should preserve that distinction wherever it summarizes deterministic hooks.

**Recommendation:** Keep saying "native PreToolUse hooks enforce ADE-session commits."
Use CI, pre-commit, or server-side checks for repo-wide guarantees.

### F10 - Documentation Drift Was Material

**Severity:** Low-Medium

The docs contained factual drift:

- README said 12 workers while architecture and tests expect 14.
- README also carried a stale hard-coded shared skill-folder count.
- README image alt text said 10-phase while ADE is now 9-phase.
- README omitted R3.3 in the Phase 1 summary.
- README and architecture framed Codex as degraded due to no subagents.
- The roadmap framed Codex parity as externally blocked.

These are not cosmetic. For a scaffolder whose product is generated process and docs,
documentation drift is product drift.

## Claims To Narrow

| Existing or tempting claim | Safer claim |
|---|---|
| ADE is a full SDLC. | ADE is an intent-to-PR agentic development pipeline with retro and learning. |
| R3.3 closes the security/privacy gap. | R3.3 closes the design-time threat/privacy gap; runtime privacy, supply-chain, and operational controls remain open. |
| Tests are the primary automated acceptance mechanism. | Tests are the durable automated acceptance mechanism; runnable changes still need runtime evidence where practical. |
| Codex is degraded because it lacks subagents. | Current Codex supports subagent workflows; ADE must prove Codex parity in its own generated flow. |
| Deterministic hooks enforce the repo. | Deterministic hooks enforce ADE-session commits; repo-wide enforcement needs CI/pre-commit/server-side wiring. |

## Priority Recommendations

1. **Codex parity proof.** Update templates/tests/transcripts to prove Codex isolated-agent
   behavior. This is now actionable and should be quick relative to the risk it removes.

2. **Conditional runtime evidence.** Restore live verification as evidence slots, not as a
   heavy always-on phase.

3. **Trace manifest.** Emit one machine-readable artifact that connects spec, ADR, threat
   model, tests, review, PR, and runtime evidence.

4. **Runtime privacy and supply-chain checks.** Extend R3.3's design-time data
   classification into Phase 6/8 implementation checks.

5. **Selective cross-model review.** Use cross-model review only for threat/security and
   architecture-tier refutation.

6. **Compound-loop integrity.** Treat ADE's own learning corpus as an attack surface.

7. **Early stall detection.** Add loop fingerprints so max-3 loops fail fast when no
   progress is happening.

8. **Incident intake.** Add a Phase-0-prime path for postmortems that turns real escaped
   failures into specs, ADRs, mitigations, and learnings.

## Source Appendix

Primary external sources checked on 2026-06-26:

- Anthropic Claude Code best practices:
  https://code.claude.com/docs/en/best-practices
- Anthropic Claude Code hooks:
  https://code.claude.com/docs/en/hooks
- Anthropic Claude Code subagents:
  https://docs.anthropic.com/en/docs/claude-code/sub-agents
- OpenAI Codex subagents:
  https://developers.openai.com/codex/subagents
- OpenAI Codex hooks:
  https://developers.openai.com/codex/hooks
- OpenAI Codex AGENTS.md:
  https://developers.openai.com/codex/guides/agents-md
- OpenAI Codex skills:
  https://developers.openai.com/codex/skills
- NIST SP 800-218 Secure Software Development Framework:
  https://csrc.nist.gov/pubs/sp/800/218/final
- ISO/IEC/IEEE 12207:2026:
  https://www.iso.org/standard/90219.html
- ISO/IEC 25010:2023:
  https://www.iso.org/standard/78176.html
- OWASP SAMM:
  https://owaspsamm.org/model/
- OWASP ASVS:
  https://owasp.org/www-project-application-security-verification-standard/
- NIST Privacy Framework:
  https://www.nist.gov/privacy-framework
- DORA metrics:
  https://dora.dev/guides/dora-metrics/
- Google SRE postmortem culture:
  https://sre.google/sre-book/postmortem-culture/
- SLSA v1.2:
  https://slsa.dev/spec/v1.2/
- CycloneDX:
  https://cyclonedx.org/
- W3C WCAG 2.2:
  https://www.w3.org/TR/WCAG22/
- WorkOS Case:
  https://github.com/workos/case
- GSD core:
  https://github.com/open-gsd/gsd-core
- gstack:
  https://github.com/garrytan/gstack
- Compound Engineering plugin:
  https://github.com/EveryInc/compound-engineering-plugin
