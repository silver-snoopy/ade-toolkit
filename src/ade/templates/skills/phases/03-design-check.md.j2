# Phase 3 — Design Check

## Purpose

Create implementation stubs (interfaces, type signatures, function signatures, module
structure) in a worktree before writing real code. Stubs serve as a lightweight
architecture validation — they catch structural problems early without the cost of full
implementation.

## Worktree Setup

Create a dedicated worktree for the task:

```bash
git worktree add .ade/worktrees/<task-id> -b ade/<task-id>
```

All stub work happens in the worktree, not the main working tree.

## What Stubs Should Contain

Stubs define the **shape** of the code, not the logic:

### Type Definitions (full)
```typescript
// packages/shared/src/types/export.ts
export interface ExportOptions {
  format: 'csv' | 'json';
  startDate: string;
  endDate: string;
  metrics?: string[];
}

export interface ExportResult {
  data: string;
  filename: string;
  contentType: string;
}
```

### Function Signatures (signature + throw)
```typescript
// packages/backend/src/db/queries/measurements.ts
export async function queryNutritionExport(
  pool: Pool,
  startDate: string,
  endDate: string,
  format: ExportFormat
): Promise<ExportResult> {
  throw new Error('Not implemented');
}
```

### Route Stubs (registration + handler shell)
```typescript
// packages/backend/src/routes/nutrition.ts
app.get('/api/nutrition/export', {
  preHandler: apiKeyMiddleware(opts.env.xApiKey),
}, async (request, reply) => {
  // TODO: Implement in Phase 4
  throw new Error('Not implemented');
});
```

### Component Stubs (props interface + empty render)
```typescript
// packages/frontend/src/components/ExportButton.tsx
interface ExportButtonProps {
  onExport: (format: ExportFormat) => void;
  isLoading: boolean;
}

export function ExportButton({ onExport, isLoading }: ExportButtonProps) {
  // TODO: Implement in Phase 4
  return null;
}
```

### Hook Stubs (signature + return shape)
```typescript
// packages/frontend/src/hooks/useNutritionExport.ts
export function useNutritionExport() {
  // TODO: Implement in Phase 4
  return {
    exportData: async (_options: ExportOptions) => {},
    isExporting: false,
    error: null as string | null,
  };
}
```

## What Stubs Should NOT Contain

- Business logic or algorithms
- SQL queries
- API calls
- Complex JSX rendering
- Test implementations (test files are not stubbed)

## Validating Stubs Against Plan

After creating stubs, verify:

1. **Coverage** — Every file in the plan's file table (Section 3) that is marked CREATE
   has a corresponding stub.
2. **Type consistency** — Types flow correctly across package boundaries
   (shared → backend, shared → frontend).
3. **Build check** — Run `npm run build -w @vitals/shared` to verify shared types compile.
   Other packages may not build yet (stubs throw), but there should be no type errors.
4. **Import check** — All imports resolve. No circular dependencies introduced.

## Iteration Limit

- **Maximum 2 iterations** of stub creation and validation.
- If stubs still don't pass validation after 2 rounds, escalate to the user with:
  - What's failing
  - Why the plan may need adjustment
  - Proposed resolution

## Output

Stubs committed to the worktree branch (`ade/<task-id>`) with message:
`chore: add implementation stubs for <task-id>`

This commit will be squashed or amended during the implementation phase.
