# Phase 5 — Quality Gate

## Purpose

Run automated checks to catch issues before human review. The quality gate is a strict
sequence — each step must pass before proceeding to the next.

## Ordered Check Sequence

Run these in order, in the worktree:

```bash
cd .ade/worktrees/<task-id>
```

### Step 1: Lint
```bash
npm run lint
```
All ESLint errors must be resolved. Warnings are acceptable only if they are pre-existing
(not introduced by this task).

### Step 2: Format Check
```bash
npm run format:check
```
If formatting issues exist, auto-fix:
```bash
npm run format
```
Then re-check to confirm.

### Step 3: Build
```bash
npm run build -w @vitals/shared
npm run build -w @vitals/backend
npm run build -w @vitals/frontend
```
All packages must build with zero TypeScript errors.

### Step 4: Unit Tests
```bash
npm run test
```
All tests must pass. Zero failures allowed for merge.

### Step 5: E2E Tests (if applicable)
```bash
npm run test:e2e
```
Run only if the task includes frontend changes or new E2E tests. E2E tests require the
frontend dev server (auto-started by Playwright config).

## Pre-existing Warnings vs New Errors

| Type | Pre-existing | Newly introduced |
|------|-------------|-----------------|
| ESLint error | Must still fix (was already broken) | Must fix |
| ESLint warning | OK to leave | Should fix, not blocking |
| TS error | Must still fix | Must fix |
| Test failure | Flag as pre-existing, not blocking | Must fix |

To determine if an issue is pre-existing, check if it exists on the base branch:
```bash
git stash && npm run lint && git stash pop
```

## Fixer Subagent Dispatch

When the quality gate fails, dispatch a fixer agent:

1. **Collect failures** — capture the full error output from the failing step.
2. **Dispatch fixer** — provide the error output and the relevant source files.
3. **Re-run the full sequence** — not just the failing step, because fixes can introduce
   new issues.
4. **Maximum 3 fixer attempts.** After 3 failures, escalate to the user.

### Fixer Dispatch Format

Provide the fixer with:
- The exact error messages
- The file(s) that need fixing
- The test file (if test failure)
- The convention rules that apply (from CLAUDE.md)

### Common Fix Patterns

| Failure | Typical fix |
|---------|------------|
| `consistent-type-imports` | Change `import { X }` to `import type { X }` |
| `no-unused-vars` | Remove unused import or prefix with `_` |
| Prettier formatting | Run `npm run format` |
| Type error: property missing | Add property to interface or fix typo |
| Test: expected vs received | Fix assertion or fix implementation |
| Test: mock not called | Fix mock setup or fix call site |

## What to Do When QA Fix Limit Reached

After 3 failed fixer attempts:

1. Summarize all three failure rounds
2. Identify the root cause pattern (e.g., "the mock setup is fundamentally wrong" vs
   "each fix introduces a new issue")
3. Present to the user with:
   - What's failing
   - What was tried
   - Recommended next step (manual fix, plan revision, or scope reduction)

Do NOT silently retry beyond the limit. The circuit breaker exists to prevent infinite loops.

## Quality Gate Pass Criteria

All of the following must be true:
- [ ] `npm run lint` — zero errors
- [ ] `npm run format:check` — zero issues
- [ ] All packages build successfully
- [ ] `npm run test` — all tests pass
- [ ] `npm run test:e2e` — all E2E tests pass (if applicable)

Only after all checks pass does the task proceed to Phase 6 (Review).
