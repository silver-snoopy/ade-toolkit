# Phase 2 — Plan

## Purpose

Write a detailed, actionable implementation plan that any developer (or agent) could
execute without needing to re-research. The plan is the contract between research and
implementation.

## Plan File Location

Save to: `.ade/tasks/<task-id>/plan.md`

## Required Sections (All 6 Mandatory)

### Section 1: Context

Why this change is being made. Link to the intent document. Summarize the user-approved
approach from Phase 1.

```markdown
## 1. Context

This task implements [goal from intent]. The user approved [approach] during research
review. See `.ade/tasks/<task-id>/intent.md` for acceptance criteria.

Key decisions:
- [Decision 1 and rationale]
- [Decision 2 and rationale]
```

### Section 2: Ordered Task List

Dependency-aware, numbered task list. Each task must be specific enough that an agent can
execute it without ambiguity.

**Build order rule:** shared types → backend → frontend. Always.

```markdown
## 2. Task List

### Shared Types (build first)
1. Add `ExportFormat` type to `packages/shared/src/types/export.ts`
2. Export from `packages/shared/src/index.ts`

### Backend
3. Add `queryNutritionCsv()` to `packages/backend/src/db/queries/measurements.ts`
4. Add GET `/api/nutrition/export` route in `packages/backend/src/routes/nutrition.ts`
5. Add unit tests for query function
6. Add route tests with app.inject()

### Frontend
7. Add `useNutritionExport` hook in `packages/frontend/src/hooks/`
8. Add Export button to Nutrition page
9. Add component tests
10. Add E2E test for export flow
```

**What makes a task "specific enough to execute":**
- Names the exact file to create or modify
- Describes the function/component/type to add
- References the pattern to follow (e.g., "follow the same pattern as `useNutritionDaily`")
- Has a clear done state

**Bad task:** "Implement the backend logic"
**Good task:** "Add `queryNutritionCsv(pool, startDate, endDate)` function to
`db/queries/measurements.ts` that returns CSV-formatted string using the same date
filtering as `queryDailyNutritionSummary`"

### Section 3: Files to Create/Modify

Table format for quick reference:

```markdown
## 3. Files

| Action | Path | Description |
|--------|------|-------------|
| CREATE | `packages/shared/src/types/export.ts` | ExportFormat type |
| MODIFY | `packages/shared/src/index.ts` | Re-export new type |
| MODIFY | `packages/backend/src/db/queries/measurements.ts` | Add CSV query |
| MODIFY | `packages/backend/src/routes/nutrition.ts` | Add export route |
| CREATE | `packages/backend/src/routes/__tests__/nutrition-export.test.ts` | Route tests |
| MODIFY | `packages/frontend/src/pages/Nutrition.tsx` | Add export button |
| CREATE | `packages/frontend/src/hooks/useNutritionExport.ts` | Export hook |
| CREATE | `e2e/nutrition-export.spec.ts` | E2E test |
```

### Section 4: Dependencies

New packages, environment variables, database migrations, or external services.

```markdown
## 4. Dependencies

- **New packages:** none
- **New env vars:** none
- **DB migrations:** none
- **External services:** none
```

If there are dependencies, be explicit about installation commands and configuration steps.

### Section 5: Test Strategy

What tests to write at each level:

```markdown
## 5. Test Strategy

### Unit Tests
- `queryNutritionCsv` — verify CSV format, date filtering, empty result handling
- Export button component — render, click handler

### Integration Tests
- None needed (no new external dependencies)

### E2E Tests
- Navigate to Nutrition → click Export → verify file download
- Export with empty date range → verify error message
```

### Section 6: Risk Areas

What could break, performance concerns, edge cases:

```markdown
## 6. Risk Areas

- **Large date ranges** could produce very large CSV files — consider pagination or limit
- **Unicode in food names** — ensure CSV encoding handles special characters
- **Empty data** — export with no data in range should show user-friendly message, not empty file
```

## Decomposing Large Features (Scope L)

For tasks affecting > 10 files, decompose into a task DAG (directed acyclic graph):

```
          ┌─ Task A (shared types) ─┐
          │                          │
Start ────┼─ Task B (DB migration) ──┼──── Task E (frontend) ──── Done
          │                          │
          └─ Task C (backend route) ─┘
                    │
                    └── Task D (backend tests)
```

Rules:
- Tasks with no dependency arrows between them can run in parallel
- Tasks that share files CANNOT run in parallel
- Each task in the DAG maps to a subagent assignment in Phase 4

## Plan Gate

Before proceeding to Phase 3, verify:
- [ ] Plan file exists at `.ade/tasks/<task-id>/plan.md`
- [ ] All 6 sections are present and non-empty
- [ ] Task list follows build order (shared → backend → frontend)
- [ ] Every acceptance criterion from intent is covered by at least one task
- [ ] Test strategy covers all new behavior

Do NOT proceed if the plan is incomplete.
