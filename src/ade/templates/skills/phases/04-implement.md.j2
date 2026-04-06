# Phase 4 — Implement

## Purpose

Write the actual implementation code in the worktree, replacing stubs with working logic.
This phase may involve multiple subagents working in parallel on independent tasks.

## Worktree

All implementation happens in the worktree created during Design Check:
`.ade/worktrees/<task-id>`

If the worktree doesn't exist yet (e.g., Design Check was skipped for small tasks):
```bash
git worktree add .ade/worktrees/<task-id> -b ade/<task-id>
```

## Build Order Enforcement

**Always build in this order:**
1. `packages/shared` — types and constants
2. `packages/backend` — server, routes, services
3. `packages/frontend` — UI components, pages

After completing work in each package, run:
```bash
npm run build -w @vitals/shared    # after shared changes
npm run build -w @vitals/backend   # after backend changes
npm run build -w @vitals/frontend  # after frontend changes
```

Do not move to the next package until the current one builds cleanly.

## Subagent File Ownership Rules

When splitting work across subagents:

- **No two agents may edit the same file.** This is a hard rule — no exceptions.
- If two tasks need to modify the same file, they must be serialized (one completes before
  the other starts).
- Shared type files (`packages/shared/src/types/`) are especially prone to conflicts —
  assign all shared type work to a single agent.

### Splitting Strategy

| Pattern | When to use |
|---------|------------|
| **By package** | Backend agent + frontend agent (most common) |
| **By feature slice** | Each agent owns a vertical slice (type + route + UI) |
| **By layer** | One agent does all queries, another does all routes |

The "by package" split is safest because packages have clear boundaries.

## Convention Reference

Before writing code, read these project conventions:

- **CLAUDE.md** — coding style, indentation, import patterns
- **Existing files in the same directory** — match naming, export style, error handling
- **Test files nearby** — understand the testing pattern used

Key conventions to enforce:
- 4-space indentation for Java, 2-space for everything else
- `import type` for type-only imports (enforced by ESLint)
- Explicit types over `var` in Java; `interface` over `type` for object shapes in TS
- Single quotes, semicolons, 100-char line width (Prettier)
- Unused variables prefixed with `_`

## Implementation Checklist

For each task in the plan:

- [ ] Replace stub with working implementation
- [ ] Follow existing patterns in the codebase
- [ ] Add error handling (don't just throw generic errors)
- [ ] Add input validation where applicable
- [ ] Write unit tests alongside the implementation
- [ ] Verify the build passes after changes

## Running Builds After Significant Changes

"Significant" means:
- New file created
- Interface or type changed
- Import structure modified
- Package dependency added

Run the appropriate build command and fix any errors before continuing. Do not accumulate
build errors across multiple tasks.

## When Implementation Diverges from Plan

If you discover during implementation that the plan needs adjustment:

1. **Minor adjustment** (different function name, extra helper file) — proceed and note
   the deviation.
2. **Moderate adjustment** (new file not in plan, different data flow) — proceed but flag
   for review phase.
3. **Major adjustment** (scope increase, architectural change) — STOP. This triggers scope
   drift detection. Present to the user before continuing.

Scope drift threshold: if actual file changes exceed the plan's file table by more than 2x,
pause for re-scoping.
