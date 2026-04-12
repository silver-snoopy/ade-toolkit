# Phase 6 — Review

## Purpose

Perform a structured code review of all changes in the task branch. The review catches
issues that automated checks cannot: logic errors, convention violations, security
vulnerabilities, test gaps, type design flaws, and comment accuracy.

## Review Scope

Review the full diff from base branch to task branch:
```bash
git diff main...ade/<task-id>
```

Review every changed file. Do not skip files because they "look fine" or are "just tests."

## Review Mechanism

**Preferred mechanism:** Invoke `pr-review-toolkit:review-pr` with aspects:
code, errors, tests, types, comments (exclude simplify).

This dispatches up to 5 specialized agents based on what changed:
- **code-reviewer** — logic errors, convention violations, CLAUDE.md compliance, security
- **silent-failure-hunter** — catch blocks, error suppression, inadequate logging
- **pr-test-analyzer** — test coverage gaps, missing edge cases, test quality
- **type-design-analyzer** — type encapsulation, invariant expression (only if types changed)
- **comment-analyzer** — comment accuracy vs code, documentation completeness (only if comments changed)

**Allowed fallback:** Launch 3 parallel Sonnet review subagents covering the same ground:

### Lens 1: Logic

Focus on correctness, edge cases, and runtime behavior.

**What to look for:**
- Null/undefined handling — what happens when optional data is missing?
- Off-by-one errors in loops, array indexing, date ranges
- Race conditions in async code — are promises properly awaited?
- Error propagation — do errors bubble up with useful messages?
- State management — can the UI reach an inconsistent state?
- Data transformation — does the output match the expected shape?
- Boundary conditions — empty arrays, zero values, max integers, very long strings
- Database queries — SQL injection via string concatenation (must use parameterized queries)
- Idempotency — can the operation be safely retried?

### Lens 2: Conventions

Focus on consistency with project patterns and standards.

**What to look for:**
- Naming conventions — files, functions, variables, types match existing patterns
- Import style — `import type` for type-only imports, consistent ordering
- Code structure — follows the established pattern for that file type (route, hook, component)
- Error handling — uses project error patterns (not bare `try/catch` with `console.log`)
- Test structure — follows existing test patterns (describe/it nesting, mock setup)
- Formatting — should be clean after Prettier, but check logical formatting (line breaks in
  complex expressions)
- Documentation — JSDoc for public APIs, inline comments for non-obvious logic
- File organization — new files are in the correct directory

### Lens 3: Security

Focus on OWASP Top 10 and application-specific security concerns.

**What to look for:**
- **Injection** — SQL injection, XSS, command injection
- **Authentication bypass** — routes missing `apiKeyMiddleware` that should have it
- **Authorization** — can users access data they shouldn't?
- **Sensitive data exposure** — API keys, passwords, or PII in logs, responses, or error messages
- **Mass assignment** — accepting unvalidated request body properties
- **SSRF** — user-controlled URLs in server-side requests
- **Dependency risks** — new packages with known vulnerabilities
- **Secrets in code** — hardcoded API keys, tokens, or credentials
- **Input validation** — are all user inputs validated before use?

## Severity Classification

Both the preferred mechanism and fallback use the same severity taxonomy:

### Critical (blocks merge — must fix immediately)
- SQL injection vulnerability
- Authentication/authorization bypass
- Data loss or corruption possibility
- Unhandled error that crashes the server
- Secret or credential exposed in code
- Silent failure that masks data corruption

### Important (fix before merge — can batch)
- Missing input validation on user-facing endpoint
- Incorrect error message misleading users
- Convention violation that makes code hard to maintain
- Missing test for a critical code path
- Race condition that could cause incorrect data display
- Catch block that swallows errors without logging
- Type that fails to express its invariants

### Suggestions (fix if file already open)
- Minor naming inconsistency
- Missing JSDoc on internal function
- Slightly verbose code that could be simplified
- Test that works but doesn't follow best practices
- Comment that is accurate but could be clearer

### Positive (informational — no action required)
- Well-designed type with strong invariants
- Thorough test coverage for edge cases
- Clean error handling that preserves context
- Code that follows established patterns effectively

## Handling Findings

1. **Critical findings** — Fix immediately. Do not proceed to verify phase.
2. **Important findings** — Fix before merge. Can batch multiple Important fixes together.
3. **Suggestions** — Note in review output. Fix if the file is already being changed.
   Otherwise, leave for a future cleanup task.
4. **Positive** — Include in review output. No action needed.

## Review-Fix Cycle

After each review pass:

1. If Critical or Important findings exist → fix them
2. Invoke `code-simplifier` on changed files (polish pass)
3. Re-run Phase 5 (Quality Gate) to validate fixes and simplifications
4. Re-review (abbreviated — focus on changed areas)

On review pass (no Critical/Important findings):

1. Invoke `code-simplifier` — final polish pass
2. Re-run Phase 5 (Quality Gate) to validate
3. Proceed to Phase 7

## Review Output Format

```markdown
## Code Review: <task-id>

### Critical Issues
| # | File | Line | Finding | Recommendation |
|---|------|------|---------|----------------|
| 1 | routes/export.ts | 42 | No null check on query result | Add null guard |

### Important Issues
| # | File | Line | Finding | Recommendation |
|---|------|------|---------|----------------|
| 2 | hooks/useExport.ts | 18 | Missing error state reset | Reset error on retry |
| 3 | types/export.ts | 5 | Uses `type` instead of `interface` | Change to interface |

### Suggestions
| # | File | Line | Finding | Recommendation |
|---|------|------|---------|----------------|
| 4 | routes/export.ts | 30 | Rate limiting not configured | Add to backlog |

### Positive Observations
- Clean parameterized query pattern in `queries/measurements.ts`
- Thorough date validation in export hook

### Summary
- Critical: 1 (must fix)
- Important: 2 (fix before merge)
- Suggestions: 1 (advisory)

**Verdict:** NEEDS FIXES — resolve #1, #2, #3 before proceeding.
```

## Iteration Limit

- **Maximum 3 review-fix cycles.**
- If findings keep appearing after 3 rounds, escalate to the user.
- Each cycle should reduce findings, not introduce new ones. If new Critical findings appear
  in cycle 3 that weren't in cycle 1, something is fundamentally wrong — escalate.
