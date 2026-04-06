Run the complete ADE SDLC cycle for: $ARGUMENTS

You are executing a structured development pipeline. Follow each phase sequentially.
Do NOT skip phases. Each phase has explicit exit criteria that must be met before proceeding.

**Input:** `$ARGUMENTS` — either a path to a spec file, or a text description of the feature/bugfix.

## Execution Policy

For every phase, distinguish between:
- **Hard requirement** — the outcome that must be achieved before proceeding
- **Preferred mechanism** — the default tool or workflow to achieve it
- **Allowed fallback** — the substitute if the preferred mechanism is unavailable

Fallbacks may change HOW work is done, but must not lower the quality bar.
Non-degradable quality gates: live verification with evidence, build/lint/test validation, documentation updates.

## Pipeline Overview

```
Phase 0: Intent → [BUG? → QA Verify] → Phase 1: Research
   → ◆ USER GATE → Phase 2: Plan → ◆ PLAN GATE
   → Phase 3: Design Check → Phase 4: Implement → Phase 5: Quality Gate
   → Phase 6: Review → Phase 7: Verify → Phase 8: Docs
   → Phase 9: Ship → ◆ MERGE GATE → Phase 10: Retro
```

---

## Phase 0 — INTENT

Extract structured requirements from the input.

**If `$ARGUMENTS` is a file path:** Read it directly.
**If `$ARGUMENTS` is a description:** Parse it for requirements.

Extract and present:
- **Type:** feature | bugfix | refactor
- **Goal:** One-sentence summary
- **Acceptance criteria:** Bullet list of what "done" looks like
- **Affected areas:** Which packages/features are likely impacted
- **Estimated scope:** S (< 3 files) | M (3-10 files) | L (> 10 files)

Save to `.ade/tasks/<task-id>/intent.md`.
Update `.ade/tasks/<task-id>/status.md`: `Phase 0/10 — Intent captured`

**Hard requirement:** Goal and acceptance criteria are clearly stated.
**Preferred mechanism:** Read spec file directly.
**Allowed fallback:** Parse text description; ask clarifying questions if ambiguous.

For detailed instructions, see [phases/00-intent.md](phases/00-intent.md).

**Exit criteria:** Goal and acceptance criteria clearly stated. Intent file saved.

---

## QA VERIFY (bugs only — skip for features and refactors)

Reproduce the bug on the live local environment before fixing it.

**Hard requirement:** For bugfixes, reproduce the bug against the live local system and capture screenshot evidence before implementing a fix.
**Preferred mechanism:** Start full local stack (docker compose + dev servers), use Playwright against real frontend and backend, capture screenshots.
**Allowed fallback:** For backend-only bugs with no UI component, live API reproduction is acceptable. Mocked tests are NEVER a substitute.

For detailed instructions, see [phases/qa-verify-bug.md](phases/qa-verify-bug.md).

**Exit criteria:** Bug reproduced on live system with screenshot evidence, OR explicitly marked as not reproducible with explanation.

---

## Phase 1 — RESEARCH

Investigate the codebase before planning.

**Hard requirement:** Research the existing implementation, similar patterns, and reusable utilities well enough to propose an implementation approach.
**Preferred mechanism:** Launch up to 3 Explore agents in parallel:
1. **Existing implementation** — files, functions, execution paths involved
2. **Related patterns** — how similar features work elsewhere in the codebase
3. **Reusable utilities** — shared helpers, hooks, components that can be reused
**Allowed fallback:** Manual investigation covering the same three scopes with detailed file paths.

For detailed instructions, see [phases/01-research.md](phases/01-research.md).

**Exit criteria:** Present findings to user with proposed implementation approach.

---

## ◆ USER GATE ◆

**STOP HERE.** Present research findings and proposed approach to the user.
Get explicit approval before proceeding.

Include:
- Summary of research findings
- Proposed approach (files to create/modify)
- Design decisions that need user input
- Estimated scope (S/M/L)

**Do NOT proceed to Phase 2 until the user explicitly approves.**

---

## Phase 2 — PLAN

Write a detailed implementation plan.

**Hard requirement:** Produce a concrete written plan specific enough to execute without ambiguity.
**Preferred mechanism:** Launch a Plan agent with all research context and user feedback.
**Allowed fallback:** Write the plan directly.

Plan file: `.ade/tasks/<task-id>/plan.md`

Required sections:
1. **Context** — why this change is being made
2. **Ordered task list** — dependency-aware (shared types → backend → frontend)
3. **Files to create/modify** — table with paths and descriptions
4. **Dependencies** — new packages, environment variables
5. **Test strategy** — unit tests, integration tests, E2E tests
6. **Risk areas** — what could break, performance concerns

Update `.ade/tasks/<task-id>/status.md`: `Phase 2/10 — Plan written`

For detailed instructions, see [phases/02-plan.md](phases/02-plan.md).

**Exit criteria:** Plan file written with all 6 sections. Each task specific enough to execute.

---

## ◆ PLAN GATE ◆

Verify the plan file exists and contains all 6 required sections.
**Do NOT proceed if incomplete. Return to Phase 2.**

---

## Phase 3 — DESIGN CHECK

Generate file stubs before full implementation to catch architectural drift early.

**Hard requirement:** Stub files exist in a worktree with correct module structure and interfaces.
**Preferred mechanism:** Dispatch a Sonnet subagent in a worktree:
`Agent(model="sonnet", isolation="worktree", prompt="Create stubs based on plan...")`
**Allowed fallback:** Create stubs directly in worktree.

Review stubs for plan alignment. Re-dispatch if needed (max 2 iterations).

Update `.ade/tasks/<task-id>/status.md`: `Phase 3/10 — Stubs generated`

For detailed instructions, see [phases/03-design-check.md](phases/03-design-check.md).

**Exit criteria:** Stub files created in worktree. Module structure matches plan.

---

## Phase 4 — IMPLEMENT

Write the code following the plan and project conventions from CLAUDE.md.

**Hard requirement:** Implement the approved plan. Code compiles successfully.
**Preferred mechanism:** Dispatch 1-3 Sonnet subagents in the worktree. Each agent owns specific files — no two agents edit the same file.
Enforce build order: shared types → backend → frontend.
**Allowed fallback:** Implement directly if subagent dispatch fails. Build order and file ownership rules still apply.

After each significant change, run the build command to verify compilation.

Update `.ade/tasks/<task-id>/status.md`: `Phase 4/10 — Implementing`

For detailed instructions, see [phases/04-implement.md](phases/04-implement.md).

**Exit criteria:** All code changes compile. Build passes.

---

## Phase 5 — QUALITY GATE

Run automated validation: lint, format, build, tests.

**Hard requirement:** All automated checks pass. Zero lint errors in changed files.
**Preferred mechanism:** Dispatch a Haiku subagent to run checks quickly and cheaply.
**Allowed fallback:** Run checks directly.

Steps:
1. Run lint — must pass with 0 errors in changed files
2. Run format check — changed files must pass
3. Run build — must compile
4. Run unit tests — all must pass
5. Run E2E tests — all must pass

If failures: dispatch a Sonnet fixer subagent (max 3 attempts).

Update `.ade/tasks/<task-id>/status.md`: `Phase 5/10 — QA gate [PASS|FAIL]`

For detailed instructions, see [phases/05-quality-gate.md](phases/05-quality-gate.md).

**Exit criteria:** All automated checks pass. No unresolved failures.

---

## Phase 6 — REVIEW

Multi-lens code review to catch issues before verification.

**Hard requirement:** Review the change across logic, conventions, and security. Resolve all HIGH and MEDIUM findings.
**Preferred mechanism:** Launch 3 parallel Sonnet review subagents:
1. **Logic** — errors, edge cases, null handling, race conditions
2. **Conventions** — project patterns from CLAUDE.md, naming, structure
3. **Security** — OWASP top 10, injection, auth bypass, secrets
**Allowed fallback:** Perform structured self-review using the same three lenses.

Classify findings: HIGH (blocking) | MEDIUM (fix before merge) | LOW (advisory).
Fix all HIGH and MEDIUM before proceeding. Skip LOW unless trivial.

After fixes: re-run build to confirm no regressions.

Update `.ade/tasks/<task-id>/status.md`: `Phase 6/10 — Review [APPROVED|FIXING]`

For detailed instructions, see [phases/06-review.md](phases/06-review.md).

**Exit criteria:** No unresolved HIGH/MEDIUM findings. Build still passes.

---

## Phase 7 — VERIFY

**MANDATORY live verification with evidence — no exemptions.**

This applies to ALL changes: frontend, backend, API-only, refactors, type changes, anything.

**Hard requirement:** Every change verified against the live local environment with screenshot or test evidence. Each acceptance criterion from Phase 0 verified.
**Preferred mechanism:** Start local dev environment, write temporary Playwright visual test against live system, capture screenshots at key states, present to user.
**Allowed fallback:** If Playwright unavailable, use another method that exercises the live system and preserves evidence. Mocked tests alone are NEVER sufficient.

Steps:
1. Start local environment (docker compose + dev servers)
2. Write temporary visual test against `http://localhost:3000` (or equivalent)
3. Capture screenshots at key states
4. Present screenshots to user
5. Verify each acceptance criterion from Phase 0
6. For bugfixes: verify the bug is fixed (compare with Phase 0 reproduction evidence)
7. Clean up temporary test file

Save evidence to `.ade/tasks/<task-id>/verification/`
Update `.ade/tasks/<task-id>/status.md`: `Phase 7/10 — Verified with evidence`

For detailed instructions, see [phases/07-verify.md](phases/07-verify.md).

**Exit criteria:** All acceptance criteria verified. Evidence captured and presented to user.

---

## Phase 8 — DOCUMENTATION

Update project documentation to reflect changes.

**Hard requirement:** Keep all affected documentation in sync with the change.
**Preferred mechanism:** Dispatch a Sonnet subagent to update docs.
**Allowed fallback:** Update docs directly.

Required updates (conditional on change type):
- **Product capabilities** — new use cases with UC IDs, user stories, behavior specs
- **Architecture docs** — new routes, DB tables, data flows
- **CLAUDE.md** — new conventions, patterns, structure changes
- **API docs** — new/changed endpoints

Update `.ade/tasks/<task-id>/status.md`: `Phase 8/10 — Docs updated`

For detailed instructions, see [phases/08-docs.md](phases/08-docs.md).

**Exit criteria:** All affected documentation updated. New features have UC entries.

---

## Phase 9 — SHIP

Create clean commit and open pull request.

**Hard requirement:** Clean commit and PR with proper evidence. PR URL returned to user.
**Preferred mechanism:** Standard git workflow + `gh pr create`.
**Allowed fallback:** Prepare commit and PR content; stop if tooling prevents completion.

Steps:
1. Stage relevant files (NOT .env, credentials, or unrelated changes)
2. Commit with conventional message (imperative mood, max 72 chars, reference UC IDs)
3. Push to feature branch
4. Open PR with summary, acceptance criteria, test plan
5. For UI changes: upload verification screenshots as PR comment
6. For bugfixes: include before/after evidence section

Update `.ade/tasks/<task-id>/status.md`: `Phase 9/10 — PR created`

For detailed instructions, see [phases/09-ship.md](phases/09-ship.md).

**Exit criteria:** PR created. URL returned to user.

---

## ◆ MERGE GATE ◆

**Present PR to user for review and merge decision.**
The agent creates the PR. The human merges it. This is non-negotiable.

---

## Phase 10 — RETROSPECTIVE

Record metrics and learnings.

Save to `.ade/tasks/<task-id>/retro.json`:
- Cycle time per phase
- Iteration counts (design check, code-review, QA fix, verify-reject)
- Circuit breaker triggers (if any)
- What worked, what didn't
- Follow-up items identified

Clean up worktree after merge: `git worktree remove .ade/worktrees/<task-id>`

Update `.ade/tasks/<task-id>/status.md`: `Phase 10/10 — Complete`

**Exit criteria:** Retro saved. Worktree cleaned up.

---

## Circuit Breakers

- Design check: max 2 iterations
- Code→review loop: max 3 cycles
- QA fix: max 3 iterations
- Verify→review reject: max 2 cycles
After any limit, escalate to user with summary. Do NOT retry silently.

## Orchestrator Rules

- The orchestrator NEVER writes application code — only dispatches subagents
- All code changes flow through subagents (Sonnet for coding/review, Haiku for tests)
- Verify subagent output independently — don't trust self-reports
- Update `.ade/tasks/<task-id>/status.md` at each phase transition
- Project conventions come from CLAUDE.md — never hardcode them in skills
