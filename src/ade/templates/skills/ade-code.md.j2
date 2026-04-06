Run ADE coding phases (Design Check + Implement + Quality Gate) for: $ARGUMENTS

If a plan exists in `.ade/tasks/`, use it. Otherwise, run /ade-plan first.

## Phase 3 — DESIGN CHECK
Dispatch Sonnet subagent in worktree to create file stubs.
Review for plan alignment (max 2 iterations).
**Exit criteria:** Stubs created. Module structure matches plan.

## Phase 4 — IMPLEMENT
Dispatch 1-3 Sonnet subagents in the worktree.
Each agent owns specific files — no overlap.
Enforce build order: shared types → backend → frontend.
Follow project conventions from CLAUDE.md.
Run build after significant changes.

**Hard requirement:** Code compiles. Build passes.
**Preferred mechanism:** Parallel Sonnet subagents with file ownership.
**Allowed fallback:** Implement directly. Build order still applies.
**Exit criteria:** All code compiles. Build passes.

## Phase 5 — QUALITY GATE
Run: lint → format → build → unit tests → E2E tests.
If failures: dispatch Sonnet fixer subagent (max 3 attempts).

**Exit criteria:** All automated checks pass.

The orchestrator NEVER writes code — only dispatches subagents.
Update `.ade/tasks/<task-id>/status.md` at each phase transition.
