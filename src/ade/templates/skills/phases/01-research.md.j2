# Phase 1 — Research

## Purpose

Investigate the codebase before writing any plan or code. Research prevents wasted effort
by surfacing existing patterns, reusable utilities, and hidden constraints. Launch up to 3
parallel research scopes for speed.

## Three Research Scopes

### Scope 1: Existing Implementation
What already exists that this task touches or extends?

- Trace the full execution path for affected features
- Identify files that will need modification
- Note any technical debt or TODOs in the affected area
- Check for existing tests that cover the area

### Scope 2: Related Patterns
How do similar features work elsewhere in the codebase?

- Find analogous routes, components, or services
- Note the pattern they follow (naming, structure, error handling)
- Identify deviations — places where the pattern was NOT followed (and why)
- Look for shared abstractions that this feature should plug into

### Scope 3: Reusable Utilities
What existing code can be reused rather than rebuilt?

- Shared types and constants in `@vitals/shared`
- Utility functions (date validation, formatting, error helpers)
- UI components (shadcn/ui components already installed)
- Hooks (TanStack Query hooks, Zustand stores)
- Test utilities (mock factories, test helpers)

## Key Locations to Check by Layer

### Backend
| Area | Location | What to look for |
|------|----------|-----------------|
| Routes | `packages/backend/src/routes/` | Route registration pattern, middleware |
| Query layer | `packages/backend/src/db/queries/` | SQL patterns, parameterization |
| Services | `packages/backend/src/services/` | Business logic, provider pattern |
| Normalizers | `packages/backend/src/services/collectors/*/normalizer.ts` | Input → Row transforms |
| Config | `packages/backend/src/config/env.ts` | EnvConfig interface, env vars |
| Plugins | `packages/backend/src/plugins/` | Fastify decorators, lifecycle hooks |
| Tests | `packages/backend/src/routes/__tests__/` | Test patterns, mock setup |

### Frontend
| Area | Location | What to look for |
|------|----------|-----------------|
| Pages | `packages/frontend/src/pages/` | Page components, layout patterns |
| Components | `packages/frontend/src/components/` | Reusable UI, shadcn/ui usage |
| Hooks | `packages/frontend/src/hooks/` | TanStack Query hooks, custom hooks |
| Store | `packages/frontend/src/store/` | Zustand stores, state shape |
| API client | `packages/frontend/src/api/` | apiFetch wrapper, endpoint patterns |
| Tests | `packages/frontend/src/__tests__/` | Component test patterns |

### Shared
| Area | Location | What to look for |
|------|----------|-----------------|
| Types | `packages/shared/src/types/` | Shared interfaces, enums |
| Constants | `packages/shared/src/constants/` | Magic values, config defaults |
| Index | `packages/shared/src/index.ts` | Public API surface |

### Infrastructure
| Area | Location | What to look for |
|------|----------|-----------------|
| DB migrations | `packages/backend/migrations/` | Schema, constraints, indexes |
| CI/CD | `.github/workflows/` | Build steps, test commands |
| Docker | `Dockerfile`, `docker-compose.yml` | Service configuration |

## How to Trace Execution Paths

For a given feature, trace from entry point to data store:

```
Route (e.g., GET /api/nutrition/daily)
  → Route handler (routes/nutrition.ts)
    → Query function (db/queries/measurements.ts)
      → SQL query (parameterized)
        → DB table (measurements / workout_sets / reports)
```

For frontend, trace from user action to API call:

```
User action (click, navigate)
  → Page component (pages/Nutrition.tsx)
    → TanStack Query hook (hooks/useNutritionDaily.ts)
      → API client (api/client.ts → apiFetch)
        → Backend route
```

Document the full chain so the plan phase knows exactly what to modify.

## Output Format

Present research findings to the user as:

```markdown
## Research Findings

### Existing Implementation
- [file paths and descriptions of what exists]
- [execution path trace]

### Related Patterns
- [similar features and the patterns they follow]
- [pattern name, e.g., "Fastify plugin route pattern"]

### Reusable Utilities
- [utilities, hooks, components that can be reused]
- [what needs to be created vs. what already exists]

### Proposed Approach
- [high-level description of implementation strategy]
- [files to create vs. modify]
- [key design decisions that need user input]

### Risks and Open Questions
- [potential issues discovered during research]
- [questions that need user clarification]
```

## After Research: USER GATE

**STOP after presenting findings.** Do not proceed to planning until the user explicitly
approves the proposed approach. The user may:
- Approve as-is
- Request changes to the approach
- Add constraints or requirements not in the original spec
- Decide to abandon the task

All of these are valid outcomes. Respect the gate.
