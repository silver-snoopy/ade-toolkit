Run ADE review phases (Review + Verify + Documentation) for: $ARGUMENTS

## Phase 6 — REVIEW

**Hard requirement:** No unresolved Critical/Important findings.
**Preferred mechanism:** Invoke `pr-review-toolkit:review-pr` with aspects:
code, errors, tests, types, comments (exclude simplify).
  - Scope: `git diff main...ade/<task-id>`
  - ADE iteration limit (max 3 cycles) governs the review-fix loop
**Allowed fallback:** Launch 3 parallel Sonnet review subagents:
1. Logic: errors, edge cases, null handling, race conditions
2. Conventions: project patterns from CLAUDE.md
3. Security: OWASP top 10, injection, auth bypass, secrets

Classify: Critical (blocking) | Important (fix before merge) | Suggestions (advisory) | Positive (informational).
Fix all Critical and Important. Re-run build after fixes.

### Review-Fix Cycle (max 3 iterations)
1. Run review (preferred or fallback mechanism)
2. If Critical/Important findings → fix them
3. Invoke `code-simplifier` on changed files
4. Re-run Phase 5 (Quality Gate) to validate
5. Re-review (abbreviated — focus on changed areas)

On review pass: invoke `code-simplifier` final polish → re-run Phase 5 → proceed.

**Exit criteria:** No Critical/Important findings. Build passes. Simplification pass complete.

## Phase 7 — VERIFY (MANDATORY — NO EXEMPTIONS)
Live verification with evidence for ALL changes (frontend, backend, refactors, anything).

1. Start local dev environment
2. Write temporary Playwright test against live system
3. Capture screenshots at key states
4. Present to user
5. Verify each acceptance criterion from Phase 0
6. For bugfixes: compare with reproduction evidence

**Hard requirement:** Evidence captured against live system.
**Allowed fallback:** Any method exercising live system with evidence. Mocked tests NEVER sufficient.
**Exit criteria:** All acceptance criteria verified with evidence.

## Phase 8 — DOCUMENTATION
Update affected docs: product capabilities, architecture, CLAUDE.md, API docs.
**Exit criteria:** All affected documentation updated.

Update `.ade/tasks/<task-id>/status.md` at each phase transition.
