# ADE Dev Pipeline Market and Best-Practice Study

Date: 2026-06-21

Scope: ADE's inner development pipeline, from intent capture through review:
Intent -> Research -> Plan -> Design Check -> Implement -> Quality Gate ->
Review. Shipping, release management, and long-term product operations are
covered only where they expose a best-practice gap in the inner loop.

This file complements `docs/ade-dev-pipeline-study-2026-06.html`. It is written
as a conservative market synthesis: score the framework against recognized
software-engineering practices, compare the surveyed competitors against the
same rubric, and separate strong evidence from plausible but lower-confidence
market claims.

## Executive conclusion

ADE is legitimately strong where the modern agentic-SDLC field is converging:
durable artifacts, explicit routing, research/specification grounding,
independent verification, author-separated TDD, deterministic hooks, and a
compounding review memory. This matches the direction identified by the 2026
"From Prompt to Process" taxonomy: frameworks are moving beyond isolated
prompts toward persistent artifacts, roles, traceability, validation, and
human review.

The claim to keep is narrower than "no competitor matches ADE." A defensible
version is:

> In the surveyed corpus, ADE is a high-rigor implementation of the
> specification-to-reviewed-code loop, with particularly strong evidence for
> routing, standard/architecture-tier spec verification, executable design
> checks, author-separated TDD, and hook enforcement. Its weakest best-practice
> gaps are live runtime evidence, standard-tier plan validation, independent
> review of design stubs, design-time security/privacy/NFR forcing, and
> operational-readiness controls.

That framing roots ADE in best practices without relying on absolute market
superlatives. It also makes the roadmap clearer: ADE does not need a new
pipeline shape. It needs to extend its existing verification discipline to the
gaps where standards and mature competitors agree evidence matters.

## Research execution

Inputs used for this synthesis:

- Local ADE source review: `docs/ade-architecture-design.md`,
  `src/ade/templates/skills/*.j2`, hooks, tests, and the existing HTML studies.
- Parallel subagent review:
  - local ADE implementation verifier
  - standards and best-practice anchor reviewer
  - competitor clusters for gstack/gsd/case/compound-engineering,
    Spec Kit/BMAD/OpenSpec/HumanLayer, and ECC/oh-my-cc/LeRisque/octobots
  - evidence-audit reviewer focused on overclaim risk
- External source check:
  - Anthropic Claude Code best practices, hooks, and subagents docs
  - NIST SSDF SP 800-218
  - ISO/IEC/IEEE 12207:2026 and ISO/IEC 25010:2023
  - OWASP SAMM and ASVS
  - DORA metrics, Google SRE postmortem guidance, SLSA, NIST Privacy Framework,
    WCAG 2.2, GitLab incremental rollout examples, and SBOM literature
  - public repos/docs for the higher-confidence competitors

One competitor cluster covering Superpowers, sdlc-skills, agent-skills, and
M.Pocock did not finish before synthesis. Those rows preserve the prior study's
evidence and are explicitly marked medium confidence rather than primary
re-verified.

## Evidence scoring

Use this scale for every cell:

| Score | Meaning |
|---:|---|
| 0 | Absent, marketing-only, or no observable evidence. |
| 1 | Prompt-level or ad hoc practice; depends on user discipline. |
| 2 | Repeatable workflow with documented artifacts, partial automation, or visible logs. |
| 3 | Enforced/defaulted mechanism with objective evidence, independent checks, and traceability. |

Source confidence:

| Mark | Meaning |
|---|---|
| H | Primary public source or local source verified in this session. |
| M | Public evidence exists, but some scoring depends on inference or prior study notes. |
| L | Prior internal/secondary evidence only; needs primary-source revalidation. |

## Best-practice framework

| Practice dimension | Why it belongs in the rubric | Anchor sources |
|---|---|---|
| Lifecycle coverage and traceability | A credible SDLC covers requirements, design, implementation, verification, operation, maintenance, and feedback. | ISO/IEC/IEEE 12207:2026: https://www.iso.org/standard/90219.html |
| Quality and NFR acceptance criteria | Non-functional quality must become measurable acceptance criteria, not adjectives like "fast" or "robust." | ISO/IEC 25010:2023: https://www.iso.org/standard/78176.html |
| Runnable verification evidence | Agentic systems need checks the agent can run and evidence the reviewer can inspect. | Anthropic best practices: https://code.claude.com/docs/en/best-practices |
| Deterministic gates | Hooks and policy checks are stronger than prose instructions because they run at lifecycle/tool events. | Anthropic hooks: https://docs.anthropic.com/en/docs/claude-code/hooks |
| Independent/fresh-context review | The builder should not be the only judge. Fresh-context subagents and factorized verification reduce self-confirmation risk. | Anthropic subagents: https://docs.anthropic.com/en/docs/claude-code/sub-agents; CoVe: https://arxiv.org/abs/2309.11495; self-correction limits: https://arxiv.org/abs/2310.01798 |
| Security requirements and threat modeling | Security requirements, risk modeling, attack-surface review, and secure design review should happen before code review. | NIST SSDF: https://csrc.nist.gov/pubs/sp/800/218/final; OWASP SAMM: https://owaspsamm.org/model/; OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/ |
| Privacy and data governance | Data classification and privacy risk need design-time treatment for systems handling personal or sensitive data. | NIST Privacy Framework: https://www.nist.gov/privacy-framework |
| Operational readiness | Production-facing changes need observability, rollback/recovery, and incident-learning loops. | DORA metrics: https://dora.dev/guides/dora-metrics/; Google SRE postmortems: https://sre.google/sre-book/postmortem-culture/ |
| Rollout and rollback safety | Runtime verification should include smoke checks, rollback paths, and progressive rollout criteria when deployable software changes are involved. | GitLab incremental rollouts as a concrete platform example: https://docs.gitlab.com/ci/environments/incremental_rollouts/ |
| Supply-chain integrity | Dependency, build, provenance, SBOM, and artifact-verification controls are distinct from source-code security review. | SLSA: https://slsa.dev/spec/v1.1/about; SBOM landscape study: https://arxiv.org/abs/2402.11151 |
| Accessibility/usability validation | UI-facing changes need keyboard, contrast, semantics, and assistive-technology checks, not only code tests. | WCAG 2.2: https://www.w3.org/TR/WCAG22/ |
| Process taxonomy | The agentic-framework market is converging on specification, context, roles, execution, validation, and portability, but no framework covers all dimensions strongly. | From Prompt to Process: https://arxiv.org/abs/2606.04967 |

## ADE score against the framework

| Dimension | Score | ADE status | Best-practice interpretation |
|---|---:|---|---|
| Intent/routing | 3 | `trivial`/`standard`/`architecture` routing with escalation floors and branch-scoped hook backstop. | Strong. Make branch scope explicit so users do not mistake ADE-routed protection for repo-wide policy. |
| Research/provenance | 3 | Full research skill uses scouts, synthesis, domain grill, and CoVe; routed `trivial` tasks skip grill/CoVe. | Strong for standard/architecture; docs should reconcile trivial-tier wording. |
| Independent spec verification | 3 | Spec-blind verifier is strong where independent subagent dispatch is available. | Defensible strength, but not "all tiers/all harnesses." Codex/fallback is degraded. |
| Plan validation | 2 | Self-check for all plans; adversarial plan reviewer only for architecture tier. | Add lightweight standard-tier coverage validation. |
| Design contract gate | 3 | Executable stubs, compile/import checks, and leftover-stub hook. | Strong mechanism; add independent stub reviewer. |
| Threat/privacy/NFR forcing | 1 | Security review exists late; R3 taxonomy does not force threat model, data classification, or measurable NFR targets. | Largest standards-rooting gap. |
| Author-separated TDD | 3 | Test writer and implementer roles plus mixed-commit hook. | Strong, with harness caveat: hook enforces commit content, not literal human/agent authorship in degraded fallback. |
| Deterministic gates/hooks | 3 | Mixed-commit, leftover-stub, and escalation-path hooks. | Strong for ADE branches; wider repo policy is optional future work. |
| Repair/stall handling | 2 | Retry caps and review loops exist; no failure-fingerprint/no-progress detector. | Add stall detection before expanding retry depth. |
| Live/runtime evidence | 1 | Acceptance coverage by tests exists; no first-class run/serve/live verification slot. | Restore live proof per non-manual acceptance criterion. |
| Review/calibration | 2 | Calibration corpus and reviewer agents; fallback is mostly same-model. | Good baseline; use cross-model review selectively for security/high-blast-radius changes. |
| Learning/traceability | 3 | Durable specs, ADRs, docs, review calibration, and retrospection. | Strong; distinguish passive influence from hard gating. |

## Competitor matrix

Columns:

- Route: intent/routing and blast-radius sizing
- Rsch: research grounding and provenance
- SpecV: independent spec/claim verification
- Plan: plan validation and requirements coverage
- Design: contracts, scaffolding, architecture checks
- SecNFR: design-time security, privacy, and measurable NFR forcing
- TDD: test authorship and test-quality discipline
- Hooks: deterministic hooks/policy gates
- Repair: bounded repair, stall detection, recovery loops
- Live: runnable/live acceptance evidence
- Review: review diversity, adversarial review, or calibrated judging
- Learn: durable learning/traceability/compounding

| System | Conf. | Route | Rsch | SpecV | Plan | Design | SecNFR | TDD | Hooks | Repair | Live | Review | Learn |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ADE | H | 3 | 3 | 3 | 2 | 3 | 1 | 3 | 3 | 2 | 1 | 2 | 3 |
| LeRisque | M | 3 | 2 | 3 | 3 | 1 | 1 | 3 | 3 | 2 | 2 | 3 | 3 |
| gstack | H | 3 | 2 | 2 | 2 | 3 | 1 | 2 | 2 | 2 | 3 | 3 | 2 |
| compound-engineering | M | 2 | 3 | 2 | 2 | 2 | 1 | 1 | 1 | 2 | 2 | 3 | 3 |
| case | H | 2 | 2 | 2 | 1 | 1 | 1 | 2 | 3 | 2 | 3 | 2 | 3 |
| sdlc-skills | M | 2 | 2 | 1 | 2 | 2 | 1 | 2 | 1 | 2 | 2 | 2 | 2 |
| ECC | M | 3 | 2 | 2 | 2 | 2 | 1 | 2 | 3 | 2 | 2 | 2 | 3 |
| octobots | M | 1 | 2 | 1 | 2 | 1 | 1 | 0 | 0 | 2 | 3 | 2 | 2 |
| gsd | H | 2 | 3 | 3 | 3 | 2 | 1 | 2 | 2 | 3 | 2 | 3 | 3 |
| Superpowers | M | 1 | 2 | 2 | 2 | 1 | 1 | 3 | 1 | 1 | 2 | 2 | 2 |
| HumanLayer | M | 2 | 2 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 2 | 2 | 2 |
| oh-my-cc | H | 3 | 2 | 2 | 2 | 2 | 1 | 2 | 3 | 3 | 3 | 2 | 3 |
| agent-skills | M | 2 | 2 | 1 | 2 | 1 | 1 | 2 | 1 | 2 | 2 | 3 | 2 |
| M.Pocock skills | M | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 2 |
| GitHub Spec Kit | H | 2 | 2 | 2 | 3 | 2 | 1 | 2 | 1 | 1 | 2 | 1 | 2 |
| OpenSpec | H | 2 | 2 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 2 |
| BMAD | M | 3 | 3 | 2 | 3 | 2 | 1 | 2 | 1 | 2 | 2 | 3 | 2 |

Interpretation:

- ADE's profile is high-rigor and front-loaded. Its trough is runtime proof and
  design-time tail controls, not the core spec-to-code loop.
- gsd is the cleanest direct challenge to ADE's plan/research rigor. It
  pressures ADE on all-tier plan checking, provenance tags, stall detection, and
  model-diverse review.
- case and gstack pressure ADE on live verification. case is narrower but
  strong where it insists on verifier evidence; gstack is stronger on
  browser/QA and review fan-out.
- BMAD and Spec Kit pressure ADE on planning/spec artifact discipline and broad
  adoption ergonomics. They are weaker evidence for deterministic enforcement.
- oh-my-cc and ECC pressure ADE on hook surface, persistent state, model routing,
  and live/repair loops.
- LeRisque pressures ADE on calibrated judging and hook-enforced discipline, but
  confidence is capped without fresh public primary-source verification.
- Superpowers, sdlc-skills, agent-skills, and M.Pocock are useful methodology
  comparators, but this synthesis treats them as medium confidence until the
  evidence pack is primary-source revalidated.

## Competitor notes and primary sources

| System | Best observed strength | Limit against ADE framework | Source posture |
|---|---|---|---|
| gstack | Parallel specialist review and browser/QA evidence. | Weaker explicit research provenance and TDD authorship enforcement. | Public repo: https://github.com/garrytan/gstack |
| gsd | Research provenance, plan checker, goal-backward verifier, cross-AI review, stall detection. | Less evidence for hard TDD authorship gates than ADE. | Public repo/docs: https://github.com/open-gsd/gsd-core |
| case | Runtime verification and deterministic PR-loop reliability. | Intentionally narrower on specification/design breadth. | Public repo: https://github.com/workos/case |
| compound-engineering | Durable compounding and broad reviewer/persona fan-out. | Deterministic hooks and live evidence are weaker in public evidence. | Public repo: https://github.com/EveryInc/compound-engineering-plugin |
| Spec Kit | Strong spec/plan/tasks/analyze artifact pipeline and portability. | Validation is mostly artifact analysis, not ADE-style blind verification or hook enforcement. | Public repo: https://github.com/github/spec-kit |
| BMAD | Strong full-lifecycle planning, QA/adversarial review, and human checkpoints. | Enforcement appears more procedural than deterministic. | Public repo/docs: https://github.com/bmad-code-org/BMAD-METHOD |
| OpenSpec | Lightweight persistent spec/change-proposal workflow. | Shallow compared with ADE on verification, test discipline, and gates. | Public site/repo: https://openspec.dev/ and https://github.com/Fission-AI/OpenSpec |
| HumanLayer | Human collaboration, artifact workspace, and review surfaces. | More product/runtime collaboration than enforceable SDLC methodology. | Public site/repo: https://www.humanlayer.dev/ and https://github.com/humanlayer/humanlayer |
| ECC | Broad cross-harness operator system and hook surface. | Some specific scoring still depends on internal secondary notes. | Prior study plus public repo candidate: https://github.com/affaan-m/ECC |
| oh-my-cc | Hook-driven state, team pipeline, live verification and fix loops. | Less clear evidence for blind spec verification and standards-tail controls. | Prior study plus public repo candidate: https://github.com/Yeachan-Heo/oh-my-claudecode |
| octobots | Standing multi-instance dev-team orchestration and worker isolation. | Weak formal gates, TDD authorship, and blind verification. | Prior study plus public repo candidate: https://github.com/arozumenko/octobots |
| sdlc-skills | Multi-IDE skill/persona content and test-automation workflow patterns. | More content-layer than enforcement layer. | Prior study plus public repo candidate: https://github.com/arozumenko/sdlc-skills |
| agent-skills | Phase-organized skills and review personas. | Stronger methodology than hard gates. | Prior study plus public repo candidate: https://github.com/addyosmani/agent-skills |
| M.Pocock skills | Grill-with-docs/domain-modeling style and composable small skills. | Not an integrated enforcement pipeline. | Prior study plus public repo candidate: https://github.com/mattpocock/skills |
| Superpowers | Strong skill methodology, TDD/worktree discipline, and task-review patterns. | Relies heavily on skill compliance rather than deterministic enforcement. | Prior study plus public repo candidate: https://github.com/obra/superpowers |
| LeRisque | Calibrated judge, hook discipline, and adversarial pipeline. | Public primary-source confidence not refreshed in this session. | Prior internal/local evidence; public candidate: https://github.com/PetroczyP/LeRisque |

## Claims to avoid or narrow

| Original-style claim | Safer version |
|---|---|
| "ADE is field-leading and no competitor matches it." | "Under this rubric, ADE scores as leader/near-leader on routing, standard/architecture-tier spec verification, executable design checks, TDD authorship, and hook enforcement; confidence varies by competitor cell." |
| "Phase 1 blind verification exists at all tiers." | "Full R4/R5 blind verification applies to standard/architecture; trivial-tier behavior is intentionally lighter and needs doc reconciliation." |
| "Author-separated TDD is a structural guarantee." | "ADE blocks mixed test+implementation commits and structurally separates authorship where independent subagent dispatch is available; Codex/fallback modes degrade to convention plus hooks." |
| "ADE has partial live verification." | "ADE has test-coverage acceptance validation, but no documented live-runtime acceptance gate." |
| "The field covers zero privacy/incident controls." | "In this corpus, no enforced gate was found for these controls; most surveyed systems under-cover the operational/compliance tail." |
| "ADE's compound loop gates review quality." | "ADE has a passive compound loop: review reads a calibration corpus that influences attention; it is not a hard merge gate." |

## Missing or weak capabilities across the field

| Capability | Best-practice anchor | Field coverage | ADE status | Adoption path |
|---|---|---|---|---|
| Live runtime acceptance evidence | Anthropic best practices; DORA change stability | Present in stronger evidence systems such as case, gstack, and oh-my-cc; absent as a first-class ADE gate. | Test-coverage gate only. | Add `.ade/ade-stack.md` `run`, `serve`, and `verify` slots; require per-criterion evidence for runnable acceptance checks. |
| Standard-tier independent plan validation | CoVe/fresh-context review; "Prompt to Process" validation dimension | gsd, Spec Kit, BMAD, and ECC show stronger common-case plan validation patterns. | Architecture-only adversarial plan review. | Add lightweight coverage matrix for standard tasks: criterion -> task -> test -> evidence. |
| Independent design-stub review | NIST SSDF secure design review; fresh-context review | Rare in the field. | Stubs compile/import but are self-reviewed. | Add read-only `stub-reviewer` with spec+plan+stubs and no stub-author reasoning. |
| Threat modeling and abuse-case design | NIST SSDF PW.1/PW.2; OWASP SAMM/ASVS | Sporadic; usually code-level security review only. | Late security review, no design-time threat model. | Add threat-model gate between Plan and Implement; feed mitigations to acceptance criteria and tests. |
| Privacy/data classification | NIST Privacy Framework | Very weak across surveyed systems. | No explicit data inventory or PII classification. | Add data-classification questions to R3; scaffold `DATA-INVENTORY.md`; block new sensitive sinks without retention/logging/legal-basis notes where applicable. |
| Falsifiable NFR/capacity targets | ISO/IEC 25010 | Usually optional or prose-level. | NFRs can remain vague. | Require target or explicit "not constrained" decision for p95/p99 latency, throughput, availability, memory, data volume, and startup/runtime budget. |
| Observability/runbooks/SLOs | Google SRE; DORA | Rare in pre-merge agent frameworks. | Not a build deliverable. | For production-facing changes, generate SLI/SLO notes, structured log/metric/span expectations, and runbook stubs. |
| Incident-to-learning loop | Google SRE postmortems; NIST SSDF RV root-cause practices | Very weak or absent as enforced pipeline input. | Retro exists, but not production-incident intake. | Add incident intake skill that converts postmortems into spec deltas, tests, runbooks, and review-calibration entries. |
| Rollback/canary/production verification | DORA stability metrics; SRE rollout discipline; GitLab incremental rollouts as a platform example | Mixed: stronger DevOps platforms cover this well; agentic SDLC frameworks usually stop at pre-merge checks. | No deploy-time evidence, rollback command, smoke check, or post-deploy verification slot. | Add stack-neutral `smoke` and `rollback` slots for deployable projects; require rollout risk, rollback command, and post-deploy verification criteria when applicable. |
| Supply-chain/SBOM/provenance | SLSA; SBOM studies; NIST SSDF supply-chain concerns | Vulnerability scans appear more often than SBOM/provenance controls. | No first-class SBOM/provenance gate. | Add dependency delta review, license policy, SBOM generation, and provenance checks for release-bound changes. |
| Accessibility/usability validation | WCAG 2.2; ISO 25010 usability/accessibility-related quality concerns | Rare unless the framework is UI-specific. | No conditional UI/a11y gate. | For UI changes, run axe/contrast/keyboard checks and require manual usability notes where automation is insufficient. |
| Trace manifest and evidence auditability | ISO-style traceability; "From Prompt to Process" risks around benchmarks/reproducibility | Artifact-heavy frameworks do some traceability; most do not emit a single end-to-end manifest. | ADE has specs, ADRs, plan, review, and retro artifacts, but no unified requirement-to-evidence manifest. | Add `trace.md` or `trace.json`: requirement -> design decision/ADR -> task -> test -> review finding -> PR -> runtime/release evidence. Store source URL/date, raw excerpts, agent notes, score rationale, and uncertainty per cell for market studies. |

## ADE adoption backlog

1. Restore live verification as a Phase 6 or Phase 5.5 gate.
   - Add `run`, `serve`, `verify`, `smoke`, and `rollback` slots to
     `.ade/ade-stack.md` where the project can support them.
   - Require per-criterion evidence for every feasible non-manual acceptance
     criterion.
   - For deployable systems, require rollout risk, rollback command, and
     post-deploy verification criteria.
   - Keep acceptance-coverage tests as the durable complement.

2. Extend independent plan validation to `standard`.
   - Use a lightweight fresh-context coverage matrix, not full architecture-tier
     refutation.
   - Fail only for uncovered acceptance criteria, missing tests, fake
     dependencies, or unbounded scope creep.

3. Add blind review to the Design Check.
   - Introduce `stub-reviewer`.
   - Inputs: spec, plan, stubs, and compile/import output.
   - No access to the stub author's reasoning.

4. Add design-time security/privacy/NFR gates.
   - Threat model: trust boundaries, auth, secrets, external inputs, abuse cases.
   - Data classification: personal/sensitive data, logs, third-party sinks,
     retention, redaction.
   - NFR forcing: numeric target or explicit "not constrained."

5. Add no-progress detection to repair loops.
   - Record failure fingerprints and finding counts.
   - Stop early when repeated attempts do not reduce the failure set.

6. Mark source confidence in every market claim.
   - Primary public verified.
   - Local implementation verified.
   - Prior internal/secondary only.
   - Inference from docs.

7. Separate harness guarantees.
   - Claude Code with subagents can enforce fresh-context roles.
   - Codex/fallback modes should be described as degraded for subagent
     isolation, while deterministic hooks still enforce commit/content rules.

8. Build an evidence pack next to future studies.
   - Store source snapshots, raw agent outputs, score rationales, and dates.
   - This is what turns "deep research" into a reproducible benchmark.

9. Add a task trace manifest.
   - Link requirement -> design decision/ADR -> task -> test -> review finding
     -> PR -> runtime/release evidence.
   - Export durable summaries before cleaning temporary task artifacts.

## Bottom line

The best-practice-rooted version of ADE is not "we beat every competitor at
everything." It is:

- ADE already has a rigorous specification-to-code spine.
- Its strongest mechanisms align with current agentic-SDLC best practice:
  artifacts, fresh contexts, runnable checks, deterministic gates, and traceable
  learning.
- The highest-leverage improvements are extensions of existing ADE concepts,
  not a new architecture.
- The market's broad missing layer is the standards tail: threat modeling,
  privacy, NFRs, observability, incident learning, supply-chain provenance, and
  accessibility. ADE can differentiate by making those controls small,
  conditional, and evidence-producing rather than heavyweight ceremony.
