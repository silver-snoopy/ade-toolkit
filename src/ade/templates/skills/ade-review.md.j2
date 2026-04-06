Run ADE review phases (Review + Verify + Documentation) for: $ARGUMENTS

## Phase 6 — REVIEW
Launch 3 parallel Sonnet review subagents:
1. Logic: errors, edge cases, null handling, race conditions
2. Conventions: project patterns from CLAUDE.md
3. Security: OWASP top 10, injection, auth bypass, secrets

Classify: HIGH (blocking) | MEDIUM (fix before merge) | LOW (advisory).
Fix all HIGH and MEDIUM. Re-run build after fixes.

**Hard requirement:** No unresolved HIGH/MEDIUM findings.
**Allowed fallback:** Structured self-review using same three lenses.
**Exit criteria:** No HIGH/MEDIUM findings. Build passes.

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
