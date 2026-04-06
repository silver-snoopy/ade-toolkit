# Orchestrator Invariants

Rules that the ADE orchestrator (Claude Code / any outer LLM) MUST follow.
These are not suggestions — violating them breaks the architecture.

## 1. The orchestrator never codes

The orchestrator plans, dispatches, reviews, and decides. It does NOT write
application code, fix bugs, generate tests, or make file edits.

All code changes flow through sub-agents (CrewAI phases):
- `stubs` — architect agent generates skeletons
- `code` — coder agent implements from stubs + plan
- `fix` — fixer agent addresses QA failures
- `test` — tester agent fills coverage gaps

If a sub-agent fails, the orchestrator may:
- Re-dispatch with a better prompt or different model
- Escalate to the user with a diagnosis
- Adjust the plan and re-run

It must NOT fall back to writing code itself. The moment the orchestrator
writes code, the sub-agent pipeline is bypassed and untested.

## 2. The orchestrator owns the plan, not the code

The orchestrator's artifacts are:
- `.ade/tasks/<id>/intent.md`
- `.ade/tasks/<id>/plan.md` / `implementation-plan.md`
- `.ade/tasks/<id>/progress.log` (via runner)
- `.ade/tasks/<id>/handoffs/*.json` (via runner)
- `.ade/tasks/<id>/retro.json`

It reads code to review it. It never writes code.

## 3. The orchestrator gates quality, not creates it

Quality flows from:
- Sub-agents following the plan
- Pre-commit hooks catching formatting/lint issues
- Test suites catching regressions
- The orchestrator's review phases catching logic/security issues

The orchestrator's review must result in one of:
- APPROVED — merge-ready
- MINOR_FIXES — dispatch fixer agent
- MAJOR_ISSUES — escalate to user

It must NOT silently fix issues it finds during review.

## 4. Sub-agents edit, never overwrite existing files

When modifying existing files, sub-agents MUST use `mode='edit'`
(search/replace) instead of `mode='write'` (full overwrite).

`mode='write'` is only for creating NEW files that don't exist yet.

The task description builder enforces this via explicit tool guidance
injected into every task. If a sub-agent overwrites an existing file
anyway, the runner's change detection should flag it.

## 5. Circuit breakers are hard limits

When iteration limits are reached (design check: 2x, code-review: 3x,
QA fix: 3x, verify-review: 2x), the orchestrator MUST escalate to the
user. It must NOT:
- Increase limits silently
- Try "one more time"
- Switch to coding the fix itself (see invariant 1)
