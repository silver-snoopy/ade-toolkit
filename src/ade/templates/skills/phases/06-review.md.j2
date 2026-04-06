# Phase 6 — Review

## Purpose

Perform a structured 3-lens code review of all changes in the task branch. The review
catches issues that automated checks cannot: logic errors, convention violations, and
security vulnerabilities.

## Review Scope

Review the full diff from base branch to task branch:
```bash
git diff main...ade/<task-id>
```

Review every changed file. Do not skip files because they "look fine" or are "just tests."

## Three Review Lenses

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

## Finding Severity Levels

### HIGH (blocking — must fix before merge)
- SQL injection vulnerability
- Authentication/authorization bypass
- Data loss or corruption possibility
- Unhandled error that crashes the server
- Secret or credential exposed in code

### MEDIUM (fix before merge — not emergency)
- Missing input validation on user-facing endpoint
- Incorrect error message misleading users
- Convention violation that makes code hard to maintain
- Missing test for a critical code path
- Race condition that could cause incorrect data display

### LOW (advisory — fix if convenient)
- Minor naming inconsistency
- Missing JSDoc on internal function
- Slightly verbose code that could be simplified
- Test that works but doesn't follow best practices

## Handling Findings

1. **HIGH findings** — Fix immediately. Do not proceed to verify phase.
2. **MEDIUM findings** — Fix before merge. Can batch multiple MEDIUM fixes together.
3. **LOW findings** — Note in review output. Fix if the file is already being changed.
   Otherwise, leave for a future cleanup task.

After fixing HIGH or MEDIUM findings:
- Re-run the full quality gate (Phase 5)
- Re-review the fixes (abbreviated — focus on the changed areas)

## Review Output Format

```markdown
## Code Review: <task-id>

### Lens 1: Logic
| # | Severity | File | Line | Finding | Recommendation |
|---|----------|------|------|---------|----------------|
| 1 | HIGH | routes/export.ts | 42 | No null check on query result | Add null guard |
| 2 | MEDIUM | hooks/useExport.ts | 18 | Missing error state reset | Reset error on retry |

### Lens 2: Conventions
| # | Severity | File | Line | Finding | Recommendation |
|---|----------|------|------|---------|----------------|
| 3 | MEDIUM | types/export.ts | 5 | Uses `type` instead of `interface` | Change to interface |

### Lens 3: Security
| # | Severity | File | Line | Finding | Recommendation |
|---|----------|------|------|---------|----------------|
| 4 | LOW | routes/export.ts | 30 | Rate limiting not configured | Add to backlog |

### Summary
- HIGH: 1 (must fix)
- MEDIUM: 2 (fix before merge)
- LOW: 1 (advisory)

**Verdict:** NEEDS FIXES — resolve #1, #2, #3 before proceeding.
```

## Iteration Limit

- **Maximum 3 code-to-review cycles.**
- If findings keep appearing after 3 rounds, escalate to the user.
- Each cycle should reduce findings, not introduce new ones. If new HIGH findings appear
  in cycle 3 that weren't in cycle 1, something is fundamentally wrong — escalate.
